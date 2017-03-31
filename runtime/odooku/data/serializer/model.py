from collections import OrderedDict
import logging

from .fields import FieldSerializer
from .relations import ManyToOneSerializer, ManyToManySerializer

from odooku.data.match import match, match_any


field_types = {
    'many2one': ManyToOneSerializer,
    'many2many': ManyToManySerializer
}

excluded_field_types = [
    'one2many'
]


_logger = logging.getLogger(__name__)


class ModelSerializer(object):

    def __init__(self, model_name, nk_fields=None):
        self._fields = OrderedDict()
        self._model_name = model_name
        self._nk_fields = nk_fields or []

    def add_field(self, field_name, serializer):
        self._fields[field_name] = serializer

    def serialize(self, record, context):
        result = {}
        for field_name, field in self._fields.iteritems():
            result[field_name] = field.serialize(record, context)
        return result

    def serialize_pk(self, pk, context):
        if not self._nk_fields:
            _logger.warning("Did not serialize a natural key for %s:%s" % (self._model_name, pk))
            return pk

        nk = {}
        record = context.env[self._model_name].browse([pk])[0]
        for field_name in self._nk_fields:
            field = self._fields[field_name]
            nk[field_name] = field.serialize(record, context)
        return nk

    def resolve_dependencies(self, context):
        context.stack.append(self._model_name)
        dependencies = set()
        for field in self._fields.itervalues():
            dependencies |= set(field.resolve_dependencies(context))
        context.stack.pop()
        return dependencies

    def resolve_nk_dependencies(self, context):
        context.stack.append(self._model_name)
        dependencies = set()
        for field_name in self._nk_fields:
            field = self._fields[field_name]
            dependencies |= set(field.resolve_dependencies(context))
        context.stack.pop()
        return dependencies

    @classmethod
    def factory(cls, model_name, model, config=None):
        if model._transient:
            raise ValueError(model)

        nk_fields = config and config.nk or None
        if not nk_fields:
            # Attempt to find suitable fk_fields from unique constraint
            for constraint in model._sql_constraints:
                constraint = ''.join(constraint[1].split()).lower()
                if constraint.startswith('unique('):
                    nk_fields = constraint[len('unique('):-1].split(',')
                    break

        serializer = cls(
            model_name,
            nk_fields=nk_fields
        )

        for field_name, field in model.fields_get().iteritems():
            if field.get('store', False) and not field['type'] in excluded_field_types:
                if (config and (match_any(field_name, config.excludes)
                        or (config.includes
                            and not match_any(field_name, config.includes)
                        ))):

                    if field.get('required', False):
                        _logger.warning("Field '%s' on model '%s' is marked as required but will not be serialized" % (field_name, model_name))
                    continue

                field_cls = field_types.get(field['type'], FieldSerializer)
                field_serializer = field_cls.factory(
                    field_name,
                    field
                )

                serializer.add_field(field_name, field_serializer)

        return serializer
