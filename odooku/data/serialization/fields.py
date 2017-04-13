from odooku.data.serialization.base import BaseFieldSerializer


class FieldSerializer(BaseFieldSerializer):

    def serialize(self, record, context):
        return record.read([self.field_name])[0][self.field_name]

    def deserialize(self, values, context):
        return values[self.field_name]
