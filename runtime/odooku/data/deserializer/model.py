from collections import OrderedDict

from .fields import FieldDeserializer
from .relations import ManyToOneDeserializer, ManyToManyDeserializer
from .exceptions import NaturalKeyNotFound, NaturalKeyMultipleFound


field_types = {
    'many2one': ManyToOneDeserializer,
    'many2many': ManyToManyDeserializer
}

excluded_field_types = [
    'one2many'
]


class ModelDeserializer(object):

    def __init__(self, model_name):
        self._fields = OrderedDict()
        self._model_name = model_name

    def add_field(self, field_name, deserializer):
        self._fields[field_name] = deserializer

    def deserialize(self, values, context):
        result = {}
        for field_name, value in values.iteritems():
            field = self._fields[field_name]
            result[field_name] = field.deserialize(values, context)
        return result

    def deserialize_pk(self, pk, context):
        if not isinstance(pk, dict):
            return pk
        elif context.resolve_nk(self._model_name, pk):
            return context.resolve_nk(self._model_name, pk)

        nk = {}
        for field_name, value in pk.iteritems():
            field = self._fields[field_name]
            nk[field_name] = field.deserialize(pk, context)

        lookup = [
            (k, '=', v)
            for (k, v) in nk.iteritems()
        ]

        records = context.env[self._model_name].search(lookup)
        if len(records) == 0:
            raise NaturalKeyNotFound("0 records found for model %s with lookup %s" % (self._model_name, lookup))
        elif len(records) > 1:
            raise NaturalKeyNotFound("%s records found for model %s with lookup %s" % (len(records), self._model_name, lookup))

        return records[0]._ids[0]

    @classmethod
    def factory(cls, model_name, model):
        if model._transient:
            raise ValueError(model)

        deserializer = cls(
            model_name
        )

        for field_name, field in model.fields_get().iteritems():
            if field.get('store', False) and not field['type'] in excluded_field_types:
                field_cls = field_types.get(field['type'], FieldDeserializer)
                field_deserializer = field_cls.factory(
                    field_name,
                    field
                )

                deserializer.add_field(field_name, field_deserializer)

        return deserializer
