class BaseFieldSerializer(object):

    def serialize(self, record):
        raise NotImplementedError()

    @property
    def dependencies(self):
        return []

    @classmethod
    def factory(cls, field_name, field, config=None):
        raise NotImplementedError()
