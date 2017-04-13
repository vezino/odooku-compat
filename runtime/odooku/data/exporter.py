import json
import logging

from odooku.api import environment
from odooku.data.serialization.context import SerializationContext
from odooku.data.serialization.dependency import (
    Dependency,
    DependencyGraph,
    DependencyError,
)

from odooku.data.ids import is_nk, is_link
from odooku.data.match import match_any
from odooku.data.exceptions import (
    NaturalKeyMissing
)


_logger = logging.getLogger(__name__)


class Exporter(object):

    def __init__(self, registry, config, strict=False, link=False):
        self._registry = registry
        self._config = config
        self._strict = strict
        self._link = link

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

    def iterator(self, models, context):
        raise NotImplementedError()

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

                # Get models to export
                models = [
                    model_name
                    for model_name in context.serializers.iterkeys()
                    if not (match_any(model_name, self._config.excludes) or
                        (self._config.includes and not
                        match_any(model_name, self._config.includes))
                    )
                ]

                _logger.info("Serializing %s models" % len(models))
                for (model_name, id, values) in self.iterator(models, context):
                    self._write(model_name, id, values)

            self._end_write()


class DefaultExporter(Exporter):

    def iterator(self, models, context):

        g = DependencyGraph.from_models(models, context.serializers)

        delayed = []
        for model_name in [str(x) for x in g.sort()]:
            model = context.env[model_name].with_context(active_test=False)
            serializer = context.serializers[model_name]
            lookup = []

            count = model.search_count(lookup)
            if not count:
                continue

            _logger.info("Serializing %s records for model %s" % (count, model_name))

            g = DependencyGraph()
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
                        yield (model_name, id, values)
                    else:
                        entries[record_context.id] = (model_name, id, values)

                    if record_context.delayed_fields:
                        if not (is_nk(id) or is_link(id)):
                            raise Exception("Delayed entry cannot work without a natural key or link %s:%s" % (model_name, id))
                        delayed.append((model_name, record, record_context.delayed_fields))

            # Sort entries
            entries = [
                entries[id]
                for id in g.sort() if id in entries
            ]

            for (model_name, id, values) in entries:
                yield (model_name, id, values)

        _logger.info("Serializing %s delayed records" % len(delayed))
        for (model_name, record, delayed_fields) in delayed:
            with context.new_record(model_name, record._ids[0], delayed=True) as record_context:
                serializer = context.serializers[record_context.model_name]
                values = serializer.serialize(record, record_context, fields=delayed_fields)
                id = serializer.serialize_id(record_context.id, record_context)
                yield (model_name, id, values)


def factory(strategy=None):
    return DefaultExporter
