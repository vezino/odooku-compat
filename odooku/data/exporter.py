from collections import OrderedDict

import json
import logging

from odooku.api import environment
from odooku.data.sort import topological_sort, CyclicDependencyError
from odooku.data.serialization import SerializationContext
from odooku.data.exceptions import (
    NaturalKeyMultipleFound,
    NaturalKeyNotFound,
    NaturalKeyMissing
)

from odooku.data.pk import is_nk, is_link
from odooku.data.match import match, match_any


_logger = logging.getLogger(__name__)


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
            dependencies = set(serializer.resolve_dependencies(dependency_context))

        for dependency in list(dependencies):
            if match_any(dependency, self._config.excludes):
                dependencies.remove(dependency)

        # Make sure there is no dependency to self, this can be handled
        dependencies.discard(model_name)
        return dependencies


    def _serialize_record(self, record, context):
        serializer = context.serializers[context.model_name]
        entry = serializer.serialize(record, context)
        # Extract delayed data
        delayed_entry = {
            field_name: entry.pop(field_name)
            for field_name in context.delayed_fields
        }

        return entry, delayed_entry

    def _serialize_pk(self, record, context):
        serializer = context.serializers[context.model_name]
        try:
            return serializer.serialize_pk(context.pk, context)
        except NaturalKeyMissing:
            return context.pk


    def export(self, fp):
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
                        (model_name, serializers[model_name])
                        for model_name in topological_sort(g)
                    ])
                except CyclicDependencyError as ex:
                    raise ex

                # Begin export
                fp.write('[')
                first_entry = True
                delayed_entries = []

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
                            entry, delayed_entry = self._serialize_record(record, record_context)
                            pk = self._serialize_pk(record, record_context)
                            entries[record_context.pk] = entry
                            g[record_context.pk] = record_context.dependencies
                            entry['__pk__'] = pk
                            entry['__model__'] = model_name
                            if delayed_entry:
                                if not (is_nk(pk) or is_link(pk)):
                                    raise Exception("Delayed entry %s cannot work without a natural key or link %s:%s" % (delayed_entry, model_name, pk))
                                delayed_entry['__pk__'] = pk
                                delayed_entry['__model__'] = model_name
                                delayed_entries.append(delayed_entry)

                    # Sort entries
                    try:
                        entries = [
                            entries[pk]
                            for pk in topological_sort(g)
                        ]
                    except CyclicDependencyError as ex:
                        raise ex

                    for entry in entries:
                        if not first_entry:
                            fp.write(',')
                        first_entry = False
                        fp.write(json.dumps(entry, indent=2, separators=(',', ': ')))

                for entry in delayed_entries:
                    if not first_entry:
                        fp.write(',')
                    first_entry = False
                    fp.write(json.dumps(entry, indent=2, separators=(',', ': ')))

                fp.write(']')
