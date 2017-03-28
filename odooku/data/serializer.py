from collections import OrderedDict

from odoo.modules.registry import RegistryManager
from odoo.api import Environment, Environments
from odoo import SUPERUSER_ID


class FakeLocal(object):
    environments = Environments()


class BaseFieldSerializer(object):

    def serialize(self, record):
        raise NotImplementedError()

    def depends_on(self):
        return []


class FieldSerializer(BaseFieldSerializer):

    def __init__(self, field_name):
        self._field_name = field_name

    def serialize(self, record):
        return record.get(self._field_name)


class RelationSerializer(BaseFieldSerializer):

    def __init__(self, fk_fields):
        pass

    def serialize_fk(self, record):
        pass


class ManyToOneSerializer(BaseFieldSerializer):
    pass


class ModelSerializer(object):

    def __init__(self):
        self._fields = OrderedDict()

    def add_field(self, field_name, serializer):
        self._fields[field_name] = serializer

    def serialize(self, record):
        pass

    @classmethod
    def from_model(cls, model):
        serializer = cls()
        for field_name, field in model.fields_get().iteritems():
            serializer.add_field(field_name, None)

        return serializer


class Serializer(object):

    def __init__(self, registry, check=False):
        self._registry = registry
        self._models = {}

    def configure(self):
        Environment._local = FakeLocal()
        with self._registry.cursor() as cr:
            uid = SUPERUSER_ID
            ctx = Environment(cr, uid, {})['res.users'].context_get()
            env = Environment(cr, uid, ctx)
            for model_name, model in env.iteritems():
                serializer = ModelSerializer.from_model(model)
                self._models[model_name] = serializer

    def serialize(self):
        self.configure()
        Environment._local = FakeLocal()
        with self._registry.cursor() as cr:
            uid = SUPERUSER_ID
            ctx = Environment(cr, uid, {})['res.users'].context_get()
            env = Environment(cr, uid, ctx)
