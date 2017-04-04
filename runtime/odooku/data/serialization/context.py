from collections import OrderedDict

from odooku.data.serialization.model import ModelSerializer


nk_links = {}


def hash_nk(nk):
    return hash(tuple(sorted(
        (k, hash_nk(v) if isinstance(v, dict) else v) for (k, v) in nk.iteritems()
    )))


class SerializationContext(object):

    def __init__(self, env, strict=False, config=None):
        self.env = env
        self.strict = strict
        self._config = config
        self._serializers = None

    @property
    def serializers(self):
        if self._serializers is None:
            self._serializers = OrderedDict([
                (model_name, ModelSerializer.factory(
                    model_name,
                    self.env[model_name], # use iterkeys instead of env iteritems for Odoo 9 compatibiltiy,
                    config=self._config.models.get(model_name, None)
                ))
                for model_name in self.env.registry.iterkeys()
                if not (self.env[model_name]._transient)
            ])

        return self._serializers

    def _clone(self, cls=None):
        cls = cls or type(self)
        clone = cls(self.env, strict=self.strict, config=self._config)
        clone._serializers = self.serializers
        return clone

    def resolve_dependencies(self, model_name):
        clone = self._clone(DependencyContext)
        return clone

    def new_entry(self, model_name, pk=None):
        clone = self._clone(EntryContext)
        clone.model_name = model_name
        clone.pk = pk
        return clone

    def new_record(self, model_name, pk):
        clone = self._clone(RecordContext)
        clone.model_name = model_name
        clone.pk = pk
        return clone

class DependencyContext(SerializationContext):

    def __enter__(self):
        self.stack = list()
        return self

    def __exit__(self, type, value, traceback):
        del self.stack


class RecordContext(SerializationContext):

    def __enter__(self):
        self.dependencies = set()
        self.delayed_fields = set()
        return self

    def __exit__(self, type, value, traceback):
        del self.dependencies
        del self.delayed_fields

    def delay_field(self, field_name):
        self.delayed_fields.add(field_name)

    def add_relation(self, relation, pk):
        if relation == self.model_name:
            self.dependencies.add(pk)


class EntryContext(SerializationContext):

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

    def relink_pk(self, pk):
        if self.model_name not in nk_links:
            nk_links[self.model_name] = {}
        nk_links[self.model_name][hash_nk(self.pk)] = pk

    def resolve_nk(self, model_name, nk):
        if model_name in nk_links:
            return nk_links[model_name].get(hash_nk(nk), None)
