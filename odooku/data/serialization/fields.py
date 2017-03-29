from .base import BaseFieldSerializer


class FieldSerializer(BaseFieldSerializer):

    def __init__(self, field_name):
        self._field_name = field_name

    def serialize(self, record):
        return record.get(self._field_name)

    @classmethod
    def factory(cls, field_name, field):
        return cls(field_name)
