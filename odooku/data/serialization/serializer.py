from collections import OrderedDict

import logging


from odooku.api import environment
from odooku.utils.sort import topological_sort, CyclicDependencyError
from .model import ModelSerializer

_logger = logging.getLogger(__name__)


def match(value, pattern):
    pattern = pattern.split('*')
    if len(pattern) == 2:
        return value.startswith(pattern[0])
    elif len(pattern) == 1:
        return value == pattern[0]
    else:
        raise ValueError(pattern)


def match_any(value, patterns):
    return any([
        match(value, pattern)
        for pattern in patterns
    ])


class Serializer(object):

    def __init__(self, registry, check=False):
        self._registry = registry
        self._check = check
        self._exclude = ['ir.*', 'base.*', 'res.*']

    def resolve_dependencies(self, model_name, model_serializer):
        # Resolve dependencies for the given model serializer
        # accounting for excluded models
        dependencies = set(model_serializer.dependencies)
        dependencies.discard(model_name)
        for dependency in list(dependencies):
            if match_any(dependency, self._exclude):
                dependencies.remove(dependency)

        return dependencies

    def get_model_serializers(self, env):
        model_serializers = OrderedDict()
        for model_name, model in env.iteritems():
            if (model._transient
                    or model._abstract
                    or match_any(model_name, self._exclude)):
                continue

            model_serializer = ModelSerializer.factory(model)
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


    def serialize(self):
        with self._registry.cursor() as cr:
            with environment(cr) as env:
                model_serializers = self.get_model_serializers(env)
                for model_name, model_serializer in model_serializers.iteritems():
                    model = env[model_name]
                    for record in model.search([]):
                        model_serializer.serialize(record)
