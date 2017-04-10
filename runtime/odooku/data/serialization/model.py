from collections import OrderedDict
import uuid
import logging

from odooku.data.serialization.fields import FieldSerializer
from odooku.data.exceptions import (
    NaturalKeyError,
    NaturalKeyMultipleFound,
    NaturalKeyNotFound,
    NaturalKeyMissing,
    NaturalKeyInvalid,
    LinkNotFound,
    ModelMissing
)

from odooku.data.serialization.relations import (
    ManyToOneSerializer,
    ManyToManySerializer
)

from odooku.data.ids import is_pk, is_nk, is_link
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

    def serialize(self, record, context, fields=None):
        result = {}
        for field_name in (fields or self._fields.iterkeys()):
            field = self._fields[field_name]
            result[field_name] = field.serialize(record, context)
        return result

    def serialize_id(self, id, context):
        resolved = context.resolve(self._model_name, id)
        if resolved:
            return resolved

        try:
            new_id = self._serialize_id(id, context)
            if is_pk(new_id) and context.link:
                return self._link_id(new_id, context)
            else:
                context.register_nk(self._model_name, new_id)
            return new_id
        except NaturalKeyMissing as ex:
            if context.link:
                return self._link_id(id, context)
            else:
                raise ex

    def _link_id(self, id, context):
        link = str(uuid.uuid4())
        if context.model_name != self._model_name:
            raise ModelMissing("Can not create a link for relation %s:%s, this model is not serialized" % ( self._model_name, id))
        context.map(self._model_name, link, id)
        context.map(self._model_name, id, link)
        _logger.debug("Link %s created for %s:%s" % (link, self._model_name, id))
        return link

    def _serialize_id(self, id, context):
        if not self._nk_fields:
            if context.strict:
                raise NaturalKeyMissing("Did not serialize a natural key for %s:%s" % (self._model_name, id))
            return id

        nk = {}
        record = context.env[self._model_name].browse([id])[0]
        for field_name in self._nk_fields:
            field = self._fields[field_name]
            nk[field_name] = field.serialize(record, context)

        if context.strict:
            with context.new_entry(self._model_name) as entry_context:
                if id != self.deserialize_id(nk, entry_context):
                    raise NaturalKeyInvalid("Natural key invalid for %s:%s" % (self._model_name, id))

        return nk

    def deserialize(self, values, context):
        result = {}
        for field_name, value in values.iteritems():
            if field_name not in self._fields:
                if context.strict:
                    raise Exception("Missing field %s " % field_name)
                continue
            field = self._fields[field_name]
            result[field_name] = field.deserialize(values, context)
        return result

    def deserialize_id(self, id, context, no_lookup=False):
        resolved = context.resolve(self._model_name, id)
        if resolved:
            return resolved

        if is_pk(id):
            return id
        elif is_link(id):
            raise LinkNotFound("No link resolved for %s %s" % (self._model_name, id))

        nk = {}
        for field_name, value in id.iteritems():
            field = self._fields[field_name]
            nk[field_name] = field.deserialize(id, context)

        if no_lookup:
            return nk

        lookup = [
            (k, '=', v)
            for (k, v) in nk.iteritems()
        ]

        records = context.env[self._model_name].search(lookup)
        if len(records) == 0:
            raise NaturalKeyNotFound("0 records found for model %s with lookup %s" % (self._model_name, lookup))
        elif len(records) > 1:
            raise NaturalKeyMultipleFound("%s records found for model %s with lookup %s" % (len(records), self._model_name, lookup))

        return records[0]._ids[0]

    def resolve_dependencies(self, context):
        context.stack.append(self._model_name)
        dependencies = []
        for field in self._fields.itervalues():
            dependencies += field.resolve_dependencies(context)
        context.stack.pop()
        return dependencies

    def resolve_nk_dependencies(self, context):
        context.stack.append(self._model_name)
        dependencies = []
        for field_name in self._nk_fields:
            field = self._fields[field_name]
            dependencies += field.resolve_dependencies(context)
        context.stack.pop()
        return dependencies

    @classmethod
    def factory(cls, model_name, model, config):
        if any([
            # use getattr for Odoo 9 compatibility
            getattr(model, attr, False)
            for attr in ['_transient', '_abstract']
        ]):
            raise ValueError(model)

        model_config = config.models.get(model_name, None)
        nk_fields = model_config and model_config.nk or None
        if nk_fields is True:
            # Attempt to find suitable fk_fields from unique constraint
            for constraint in model._sql_constraints:
                constraint = ''.join(constraint[1].split()).lower()
                if constraint.startswith('unique('):
                    nk_fields = constraint[len('unique('):-1].split(',')
                    break

            if nk_fields is True:
                raise Exception("Cannot resolve an automatic natural key for model %s" % model_name)

        serializer = cls(
            model_name,
            nk_fields=nk_fields
        )

        def include_field(field_name, field):
            if not field.get('store', False) or field['type'] in excluded_field_types:
                return False

            if (model_config and (match_any(field_name, model_config.excludes)
                    or (model_config.includes
                        and not match_any(field_name, model_config.includes)
                    ))):

                if field.get('required', False):
                    _logger.warning("Field '%s' on model '%s' is marked as required but will not be serialized" % (field_name, model_name))

                return False

            return True

        for field_name, field in model.fields_get().iteritems():
            if include_field(field_name, field):
                field_cls = field_types.get(field['type'], FieldSerializer)
                field_serializer = field_cls.factory(
                    field_name,
                    field,
                    config
                )
                if field_serializer:
                    serializer.add_field(field_name, field_serializer)
                    continue

            if model_config and match_any(field_name, model_config.includes, exact=True):
                _logger.warning("Field '%s' in inclusions is missing from model '%s'" % (field_name, model_name))

        return serializer
