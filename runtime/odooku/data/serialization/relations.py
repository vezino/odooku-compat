from odooku.data.serialization.base import BaseFieldSerializer


import logging
_logger = logging.getLogger(__name__)


class RelationSerializer(BaseFieldSerializer):

    def __init__(self, field_name, relation, required=False):
        super(RelationSerializer, self).__init__(field_name, required=required)
        self.relation = relation

    def serialize(self, record, context):
        return self.serialize_relation(record, context)

    def serialize_relation(self, record, context):
        raise NotImplementedError()

    def deserialize(self, values, context):
        return self.deserialize_relation(values, context)

    def deserialize_relation(self, values, context):
        raise NotImplementedError()

    @classmethod
    def parse(cls, field_name, field, config):
        relation = field['relation']
        required = field['required']
        model_config = config.models.get(relation, None)
        if model_config and model_config.nk or not(
                    config.includes and relation not in config.includes
                    or config.excludes and relation in config.excludes
                ):
            return cls(field_name, relation, required=required)


class ManyToOneSerializer(RelationSerializer):

    def serialize_relation(self, record, context):
        value = record.read([self.field_name])[0][self.field_name]
        if value:
            serializer = context.serializers[self.relation]
            context.add_dependency(self.relation, value[0], self)
            return serializer.serialize_id(value[0], context)
        return False

    def deserialize_relation(self, values, context):
        value = values[self.field_name]
        if value:
            serializer = context.serializers[self.relation]
            return serializer.deserialize_id(value, context)
        return False


class ManyToManySerializer(RelationSerializer):

    def serialize_relation(self, record, context):
        result = []
        if context.delayed:
            value = record.read([self.field_name])[0][self.field_name]
            if value:
                serializer = context.serializers[self.relation]
                for id in value:
                    context.add_dependency(self.relation, id, self)
                    result.append(serializer.serialize_id(id, context))
            return result
        else:
            context.delay_field(self.field_name)

    def deserialize_relation(self, values, context):
        result = []
        value = values[self.field_name]
        if value:
            serializer = context.serializers[self.relation]
            for id in value:
                result.append(serializer.deserialize_id(id, context))

        return [(6, 0, result)]
