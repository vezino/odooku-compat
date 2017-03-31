from .base import BaseFieldSerializer


import logging
_logger = logging.getLogger(__name__)


class RelationSerializer(BaseFieldSerializer):

    def __init__(self, field_name, relation):
        self._field_name = field_name
        self._relation = relation

    def serialize(self, record, context):
        return self.serialize_relation(record, context)

    def serialize_relation(self, record, context):
        raise NotImplementedError()

    @classmethod
    def factory(cls, field_name, field, config=None):
        return cls(field_name, field['relation'])


class ManyToOneSerializer(RelationSerializer):

    def resolve_dependencies(self, context):
        model_serializer = context.model_serializers[self._relation]
        dependencies = set([self._relation])
        if (context.stack[-1] != self._relation):
            dependencies |= model_serializer.resolve_nk_dependencies(context)
        return dependencies

    def serialize_relation(self, record, context):
        value = record.read([self._field_name])[0][self._field_name]
        if value:
            model_serializer = context.model_serializers[self._relation]
            context.add_relation(self._relation, value[0])
            return model_serializer.serialize_pk(value[0], context)
        return False


class ManyToManySerializer(RelationSerializer):

    def serialize_relation(self, record, context):
        result = []
        context.delay_field(self._field_name)
        value = record.read([self._field_name])[0][self._field_name]
        if value:
            model_serializer = context.model_serializers[self._relation]
            for pk in value:
                context.add_relation(self._relation, pk)
                result.append(model_serializer.serialize_pk(pk, context))
        return result
