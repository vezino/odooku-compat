import itertools


class BaseFieldSerializer(object):

    def serialize(self, record, context):
        raise NotImplementedError()

    def deserialize(self, record, context):
        raise NotImplementedError()

    def resolve_dependencies(self, context):
        return []

    @classmethod
    def factory(cls, field_name, field, config):
        raise NotImplementedError()


class Dependency(object):

    def __init__(self, value, *fields):
        self.value = value
        self.fields = fields

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return other == self.value

    def __repr__(self):
        return str(self.value)

    @classmethod
    def merge(cls, dependencies):
        return cls(dependencies[0].value, *list(itertools.chain(*[
            dependency.fields for dependency in dependencies
        ])))
