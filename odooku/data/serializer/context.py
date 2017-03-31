from contextlib import contextmanager


class SerializerContext(object):

    def __init__(self, env, model_serializers):
        self.env = env
        self.model_serializers = model_serializers

    @contextmanager
    def resolve_dependencies(self):
        self.stack = list()
        yield self
        del self.stack

    @contextmanager
    def record(self, model_name, pk):
        self.model_name = model_name
        self.pk = pk
        self.dependencies = set()
        self.delayed_fields = set()
        yield self
        del self.model_name
        del self.pk
        del self.dependencies
        del self.delayed_fields

    def delay_field(self, field_name):
        self.delayed_fields.add(field_name)

    def add_relation(self, relation, pk):
        if relation == self.model_name:
            self.dependencies.add(pk)
