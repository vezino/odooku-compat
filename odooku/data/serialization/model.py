from collections import OrderedDict

from .fields import FieldSerializer
from .relations import ManyToOneSerializer


field_types = {
    'many2one': ManyToOneSerializer
}


class ModelSerializer(object):

    def __init__(self):
        self._fields = OrderedDict()

    def add_field(self, field_name, serializer):
        self._fields[field_name] = serializer

    def serialize(self, record):
        pass

    @property
    def dependencies(self):
        dependencies = set()
        for field in self._fields.itervalues():
            dependencies |= set(field.dependencies)
        return dependencies

    @classmethod
    def factory(cls, model):
        if model._abstract or model._transient:
            raise ValueError(model)

        serializer = cls()
        for field_name, field in model.fields_get().iteritems():
            if field.get('store', False):
                field_serializer_cls = field_types.get(field['type'], FieldSerializer)
                field_serializer = field_serializer_cls.factory(field_name, field)
                serializer.add_field(field_name, field_serializer)

        return serializer
