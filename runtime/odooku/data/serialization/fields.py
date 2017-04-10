from odooku.data.serialization.base import BaseFieldSerializer


class FieldSerializer(BaseFieldSerializer):

    def __init__(self, field_name):
        self._field_name = field_name

    def serialize(self, record, context):
        return record.read([self._field_name])[0][self._field_name]

    def deserialize(self, values, context):
        return values[self._field_name]

    @classmethod
    def factory(cls, field_name, field, config):
        return cls(field_name)
