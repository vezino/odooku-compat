from .base import BaseFieldDeserializer


class FieldDeserializer(BaseFieldDeserializer):

    def __init__(self, field_name):
        self._field_name = field_name

    def deserialize(self, values, context):
        return values[self._field_name]

    @classmethod
    def factory(cls, field_name, field):
        return cls(field_name)
