class BaseFieldSerializer(object):

    def serialize(self, record, context):
        raise NotImplementedError()

    def deserialize(self, record, context):
        raise NotImplementedError()

    def resolve_dependencies(self, context):
        return []

    @classmethod
    def factory(cls, field_name, field, config=None):
        raise NotImplementedError()
