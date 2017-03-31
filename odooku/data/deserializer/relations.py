from .base import BaseFieldDeserializer


import logging
_logger = logging.getLogger(__name__)


class RelationDeserializer(BaseFieldDeserializer):

    def __init__(self, field_name, relation):
        self._field_name = field_name
        self._relation = relation

    def deserialize(self, values, context):
        return self.deserialize_relation(values, context)

    def deserialize_relation(self, values, context):
        raise NotImplementedError()

    @classmethod
    def factory(cls, field_name, field):
        return cls(field_name, field['relation'])


class ManyToOneDeserializer(RelationDeserializer):

    def deserialize_relation(self, values, context):
        value = values[self._field_name]
        if value:
            model_deserializer = context.model_deserializers[self._relation]
            return model_deserializer.deserialize_pk(value, context)
        return False


class ManyToManyDeserializer(RelationDeserializer):

    def deserialize_relation(self, values, context):
        result = []
        value = values[self._field_name]
        if value:
            model_deserializer = context.model_deserializers[self._relation]
            for pk in value:
                result.append(model_deserializer.deserialize_pk(pk, context))
        return result
