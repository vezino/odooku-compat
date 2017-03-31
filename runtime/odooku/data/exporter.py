from collections import OrderedDict

import json
import logging

from odooku.api import environment
from .sort import topological_sort, CyclicDependencyError
from .serializer import ModelSerializer, SerializerContext
from .config import ExportConfig
from .match import match, match_any

_logger = logging.getLogger(__name__)


class Exporter(object):

    def __init__(self, registry, config=None):
        self._registry = registry
        self._config = config or ExportConfig(
            excludes=[
                'res.*',
                'ir.*',
                'base.*',
                'base_import.tests.*'
            ]
        )

    def resolve_dependencies(self, model_name, context):
        # Resolve dependencies for the given model serializer
        # accounting for excluded models
        model_serializer = context.model_serializers[model_name]
        with context.resolve_dependencies():
            dependencies = set(model_serializer.resolve_dependencies(context))
        for dependency in list(dependencies):
            if match_any(dependency, self._config.excludes):
                dependencies.remove(dependency)

        # Make sure there is no dependency to self, this can be handled
        dependencies.discard(model_name)
        return dependencies

    def get_model_serializers(self, env):
        model_serializers = OrderedDict()
        for model_name, model in env.registry.iteritems():
            if model._transient:
                continue

            model_serializer = ModelSerializer.factory(
                model_name,
                model,
                config=self._config.models.get(model_name, None)
            )
            model_serializers[model_name] = model_serializer

        return model_serializers


    def export(self, fp, delayed=False):
        with self._registry.cursor() as cr:
            with environment(cr) as env:
                model_serializers = self.get_model_serializers(env)

                # Filter out includes / excludes
                filtered = OrderedDict([
                    (model_name, model_serializer)
                    for (model_name, model_serializer) in model_serializers.iteritems()
                    if not (match_any(model_name, self._config.excludes) or
                        (self._config.includes and not
                        match_any(model_name, self._config.includes))
                    )
                ])

                context = SerializerContext(env, model_serializers)

                # Build dependency graph
                g = OrderedDict([
                    (model_name, self.resolve_dependencies(model_name, context))
                    for (model_name, model_serializer) in filtered.iteritems()
                ])

                # Sort model serializers
                try:
                    filtered = OrderedDict([
                        (model_name, filtered[model_name])
                        for model_name in topological_sort(g)
                    ])
                except CyclicDependencyError as ex:
                    raise ex

                _logger.info("Serializing %s models" % len(filtered))

                has_delayed = False
                data = OrderedDict()
                for model_name, model_serializer in filtered.iteritems():
                    model = env[model_name]
                    lookup = []
                    count = model.search_count(lookup)
                    if not count:
                        continue
                    _logger.info("Serializing %s records for model %s" % (count, model_name))

                    g = OrderedDict()
                    entries = dict()
                    for record in model.search(lookup):
                        with context.record(model_name, record._ids[0]):
                            entry = model_serializer.serialize(record, context)
                            if not delayed:
                                has_delayed = has_delayed or bool(context.delayed_fields)
                                # Remove delayed fields
                                for delayed_field in context.delayed_fields:
                                    entry.pop(delayed_field)
                            else:
                                # Use only delayed fields
                                entry = {
                                    field_name: entry[field_name]
                                    for field_name in context.delayed_fields
                                }

                            if entry:
                                entry['__pk__'] = model_serializer.serialize_pk(context.pk, context)
                                entries[context.pk] = entry
                                g[context.pk] = context.dependencies

                    # Sort records
                    try:
                        entries = [
                            entries[pk]
                            for pk in topological_sort(g)
                        ]
                    except CyclicDependencyError as ex:
                        raise ex

                    data[model_name] = entries

                if has_delayed and not delayed:
                    _logger.warning("Delayed fields detected, make sure to rerun this command with the --delayed flag")

                json.dump(data, fp, indent=2, separators=(',', ': '))
