from collections import OrderedDict
import logging

from odooku.data.serialization.model import ModelSerializer
from odooku.data.ids import hash_id

model_map = {}
missing_nks = {}

_logger = logging.getLogger(__name__)


class SerializationContext(object):

    def __init__(self, env, config, strict=False, link=False):
        self.env = env
        self.config = config
        self.strict = strict
        self.link = link
        self._serializers = None

    @property
    def serializers(self):
        if self._serializers is None:
            self._serializers = OrderedDict([
                (model_name, ModelSerializer.factory(
                    model_name,
                    self.env[model_name], # use iterkeys instead of env iteritems for Odoo 9 compatibiltiy,
                    config=self.config
                ))
                for model_name in self.env.registry.iterkeys()
                if not any([
                    # use getattr for Odoo 9 compatibility
                    getattr(self.env[model_name], attr, False)
                    for attr in ['_transient', '_abstract']
                ])
            ])

        return self._serializers

    def _clone(self, cls=None):
        cls = cls or type(self)
        clone = cls(self.env, strict=self.strict, link=self.link, config=self.config)
        clone._serializers = self.serializers
        return clone

    def register_nk(self, model_name, nk):
        if (self.config.includes and model_name not in self.config.includes
                    or self.config.excludes and model_name in self.config.excludes
                ):
            if model_name not in missing_nks:
                missing_nks[model_name] = []

            if nk not in missing_nks[model_name]:
                _logger.info("Natural key %s for model %s required on import" % (nk, model_name))
                missing_nks[model_name].append(nk)

    def resolve_dependencies(self, model_name):
        clone = self._clone(DependencyContext)
        return clone

    def new_entry(self, model_name, id=None):
        clone = self._clone(EntryContext)
        clone.model_name = model_name
        clone.id = id
        return clone

    def new_record(self, model_name, id, delayed=False):
        clone = self._clone(RecordContext)
        clone.model_name = model_name
        clone.id = id
        clone.delayed = delayed
        return clone

    def resolve(self, model_name, a):
        if model_name in model_map:
            return model_map[model_name].get(hash_id(a), None)

    def map(self, model_name, a, b):
        if model_name not in model_map:
            model_map[model_name] = {}

        model_map[model_name][hash_id(a)] = b

class DependencyContext(SerializationContext):

    def __enter__(self):
        self.stack = list()
        return self

    def __exit__(self, type, value, traceback):
        del self.stack


class RecordContext(SerializationContext):

    model_name = None

    def __enter__(self):
        self.dependencies = set()
        self.delayed_fields = set()
        return self

    def __exit__(self, type, value, traceback):
        del self.dependencies
        del self.delayed_fields

    def delay_field(self, field_name):
        self.delayed_fields.add(field_name)

    def add_relation(self, relation, id):
        if relation == self.model_name:
            self.dependencies.add(id)


class EntryContext(SerializationContext):

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass
