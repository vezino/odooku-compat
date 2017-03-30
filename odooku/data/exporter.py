from collections import OrderedDict

import logging


from odooku.api import environment
from odooku.utils.sort import topological_sort, CyclicDependencyError
from .serializer import ModelSerializer
from .config import ExportConfig
from .match import match, match_any

_logger = logging.getLogger(__name__)


class Exporter(object):

    def __init__(self, registry, config=None, check=False):
        self._registry = registry
        self._check = check
        self._config = config or ExportConfig.factory(
            excludes=['res.*', 'ir.*', 'base.*']
        )

    def resolve_dependencies(self, model_name, model_serializer):
        # Resolve dependencies for the given model serializer
        # accounting for excluded models
        dependencies = set(model_serializer.dependencies)
        dependencies.discard(model_name)
        for dependency in list(dependencies):
            if match_any(dependency, self._config.excludes):
                dependencies.remove(dependency)

        return dependencies

    def get_model_serializers(self, env):
        model_serializers = OrderedDict()
        for model_name, model in env.iteritems():
            if (model._transient
                    or model._abstract
                    or match_any(model_name, self._config.excludes)
                    or (self._config.includes
                        and not match_any(model_name, self._config.includes))
                    ):
                continue

            model_serializer = ModelSerializer.factory(
                model,
                config=self._config.models.get(model_name, None)
            )
            model_serializers[model_name] = model_serializer

        # Build dependency graph
        g = OrderedDict([
            (model_name, self.resolve_dependencies(model_name, model_serializer))
            for (model_name, model_serializer) in model_serializers.iteritems()
        ])

        # Sort model serializers
        try:
            model_serializers = OrderedDict([
                (model_name, model_serializers[model_name])
                for model_name in topological_sort(g)
            ])
        except CyclicDependencyError as ex:
            raise ex

        return model_serializers


    def export(self):
        with self._registry.cursor() as cr:
            with environment(cr) as env:
                model_serializers = self.get_model_serializers(env)
                for model_name, model_serializer in model_serializers.iteritems():
                    model = env[model_name]
                    for record in model.search([]):
                        model_serializer.serialize(record)
