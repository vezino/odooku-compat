from collections import OrderedDict

import json
import logging

from odooku.api import environment
from .deserializer import ModelDeserializer, DeserializerContext
from .deserializer.exceptions import NaturalKeyMultipleFound, NaturalKeyNotFound
from .match import match, match_any

_logger = logging.getLogger(__name__)


class Importer(object):

    def __init__(self, registry):
        self._registry = registry


    def get_model_deserializers(self, env):
        model_deserializers = OrderedDict()
        for model_name in env.registry.iterkeys():
            model = env[model_name]
            if model._transient:
                continue

            model_deserializer = ModelDeserializer.factory(
                model_name,
                model
            )
            model_deserializers[model_name] = model_deserializer

        return model_deserializers

    def deserialize(self, data, cr, context):
        for (model_name, entries) in data.iteritems():
            model = context.env[model_name]
            model_deserializer = context.model_deserializers[model_name]
            _logger.info("Deserializing %s records for model %s" % (len(entries), model_name))
            for values in entries:
                pk = values.pop('__pk__')
                record = model_deserializer.deserialize(values, context)
                existing = False
                if isinstance(pk, dict):
                    try:
                        existing = model_deserializer.deserialize_pk(pk, context)
                    except (NaturalKeyNotFound, NaturalKeyMultipleFound):
                        pass

                if not existing:
                    new_pk = model.create(record)._ids[0]
                    if isinstance(pk, dict):
                        try:
                            model_deserializer.deserialize_pk(pk, context)
                        except NaturalKeyNotFound:
                            _logger.warning("Natural key for %s:%s is no longer valid, relinking" % (model_name, new_pk))
                            context.link_nk(model_name, pk, new_pk)
                else:
                    model.browse([existing])[0].write(record)


    def import_(self, fp, fake=False):
        data = json.load(fp, object_pairs_hook=OrderedDict)
        with self._registry.cursor() as cr:
            with environment(cr) as env:
                model_deserializers = self.get_model_deserializers(env)
                context = DeserializerContext(env, model_deserializers)
                try:
                    cr.execute('SAVEPOINT import_save')
                    self.deserialize(data, cr, context)
                except Exception:
                    cr.execute('ROLLBACK TO SAVEPOINT import_save')
                    raise

                if fake:
                    cr.execute('ROLLBACK TO SAVEPOINT import_save')
