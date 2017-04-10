from collections import OrderedDict

import json
import logging

from odooku.api import environment
from odooku.data.sort import topological_sort, CyclicDependencyError
from odooku.data.serialization import SerializationContext, Dependency

from odooku.data.ids import is_nk, is_link
from odooku.data.match import match_any
from odooku.data.exceptions import (
    NaturalKeyMissing,
    DependencyError
)


_logger = logging.getLogger(__name__)


def _dependency_error(ex):
    path = []
    for node in ex.nodes:
        if isinstance(node, Dependency) and node.fields:
            path.append('(%s : %s)' % ('|'.join([str(field) for field in node.fields]), str(node)))
        else:
            path.append(str(node))

    return DependencyError("Cyclic dependency detected %s" % " -> ".join(path))


class Exporter(object):

    def __init__(self, registry, config, strict=False, link=False):
        self._registry = registry
        self._config = config
        self._strict = strict
        self._link = link

    def _resolve_serializer_dependencies(self, model_name, context):
        # Resolve dependencies for the given model serializer
        # accounting for excluded models
        serializer = context.serializers[model_name]

        with context.resolve_dependencies(model_name) as dependency_context:
            dependencies = serializer.resolve_dependencies(dependency_context)

        # Compact dependencies
        dependencies = set([
            Dependency.merge([y for y in dependencies if x == y])
            for x in dependencies
        ])

        for dependency in list(dependencies):
            if match_any(dependency, self._config.excludes):
                dependencies.remove(dependency)

        # Make sure there is no dependency to self, this can be handled
        dependencies.discard(model_name)

        return dependencies

    def _begin_write(self, fp):
        self._fp = fp
        self._first_entry = True
        self._fp.write('[')

    def _end_write(self):
        self._fp.write(']')

    def _write(self, model_name, id, values):
        if not self._first_entry:
            self._fp.write(',')
        self._first_entry = False
        self._fp.write(json.dumps(dict({
            '__model__': model_name,
            '__id__' : id
        }, **values), indent=2, separators=(',', ': ')))

    def export(self, fp):
        self._begin_write(fp)
        with self._registry.cursor() as cr:
            with environment(cr) as env:

                context = SerializationContext(
                    env,
                    strict=self._strict,
                    link=self._link,
                    config=self._config
                )

                # Resolve "root" serializers
                serializers = OrderedDict([
                    (model_name, serializer)
                    for (model_name, serializer) in context.serializers.iteritems()
                    if not (match_any(model_name, self._config.excludes) or
                        (self._config.includes and not
                        match_any(model_name, self._config.includes))
                    )
                ])

                # Build dependency graph for root serializers
                g = OrderedDict([
                    (model_name, self._resolve_serializer_dependencies(model_name, context))
                    for (model_name, serializer) in serializers.iteritems()
                ])

                # Sort root serializers
                try:
                    serializers = OrderedDict([
                        (str(model_name), serializers[str(model_name)])
                        for model_name in topological_sort(g)
                    ])
                except CyclicDependencyError as ex:
                    raise _dependency_error(ex)


                delayed = []
                _logger.info("Serializing %s models" % len(serializers))
                for model_name, serializer in serializers.iteritems():
                    model = context.env[model_name]
                    lookup = []

                    count = model.search_count(lookup)
                    if not count:
                        continue

                    _logger.info("Serializing %s records for model %s" % (count, model_name))

                    g = OrderedDict()
                    entries = dict()

                    for record in model.search(lookup):
                        with context.new_record(model_name, record._ids[0]) as record_context:
                            serializer = context.serializers[record_context.model_name]
                            values = serializer.serialize(record, record_context)

                            try:
                                id = serializer.serialize_id(record_context.id, record_context)
                            except NaturalKeyMissing:
                                id = record_context.id

                            # Add entry to graph
                            g[record_context.id] = record_context.self_dependencies

                            # Either write directly or write later
                            if not record_context.self_dependencies:
                                self._write(model_name, id, values)
                            else:
                                entries[record_context.id] = (model_name, id, values)

                            if record_context.delayed_fields:
                                if not (is_nk(id) or is_link(id)):
                                    raise Exception("Delayed entry cannot work without a natural key or link %s:%s" % (model_name, id))
                                delayed.append((model_name, record, record_context.delayed_fields))

                    # Sort entries
                    try:
                        entries = [
                            entries[id]
                            for id in topological_sort(g) if id in entries
                        ]
                    except CyclicDependencyError as ex:
                        raise _dependency_error(ex)

                    for (model_name, id, values) in entries:
                        self._write(model_name, id, values)

                _logger.info("Serializing %s delayed records" % len(delayed))
                for (model_name, record, delayed_fields) in delayed:
                    with context.new_record(model_name, record._ids[0], delayed=True) as record_context:
                        serializer = context.serializers[record_context.model_name]
                        values = serializer.serialize(record, record_context, fields=delayed_fields)
                        id = serializer.serialize_id(record_context.id, record_context)
                        self._write(model_name, id, values)

            self._end_write()
