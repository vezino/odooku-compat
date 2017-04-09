import ijson
import logging

from odooku.api import environment
from odooku.data.serialization import SerializationContext
from odooku.data.exceptions import (
    NaturalKeyMultipleFound,
    NaturalKeyNotFound,
    NaturalKeyError,
    LinkNotFound
)

from odooku.data.ids import is_nk, is_link
from odooku.data.match import match, match_any


_logger = logging.getLogger(__name__)


class Importer(object):

    def __init__(self, registry, config, strict=False):
        self._registry = registry
        self._config = config
        self._strict = strict

    def _deserialize_entry(self, entry, context):
        model = context.env[context.model_name]
        serializer = context.serializers[context.model_name]
        values = serializer.deserialize(entry, context)

        existing = None
        try:
            existing = serializer.deserialize_id(context.id, context)
            if not model.browse([existing]).exists():
                existing = None
        except (LinkNotFound, NaturalKeyError):
            pass


        if not existing:
            # Create new model
            try:
                new_id = model.create(values)._ids[0]
                _logger.info("created %s %s" % (context.model_name, new_id))
            except:
                _logger.warning("%s %s" % (context.model_name, values))
                raise

            if is_link(context.id):
                context.map(context.model_name, context.id, new_id)

            if is_nk(context.id):
                try:
                    serializer.deserialize_id(context.id, context)
                except NaturalKeyNotFound:
                    _logger.warning("Natural key %s for %s:%s is no longer valid, updating" % (context.id, context.model_name, new_id))
                    model.browse([new_id])[0].write(serializer.deserialize_id(context.id, context, no_lookup=True))
                    try:
                        serializer.deserialize_id(context.id, context)
                    except NaturalKeyNotFound:
                        _logger.warning("Natural key %s for %s:%s is no longer valid, remapping" % (context.id, context.model_name, new_id))
                        context.map(context.model_name, context.id, new_id)
        else:
            try:
                model.browse([existing])[0].write(values)
                _logger.info("updated %s %s" % (context.model_name, existing))
            except Exception:
                _logger.warning("%s %s %s" % (context.model_name, existing, values))
                raise


    def import_(self, fp, fake=False):
        with self._registry.cursor() as cr:
            with environment(cr) as env:
                context = SerializationContext(
                    env,
                    strict=self._strict,
                    config=self._config
                )

                try:
                    cr.execute('SAVEPOINT import_save')
                    for entry in ijson.items(fp, 'item'):
                        id = entry.pop('__id__')
                        model_name = entry.pop('__model__')
                        with context.new_entry(model_name, id) as entry_context:
                            self._deserialize_entry(entry, entry_context)
                except Exception:
                    cr.execute('ROLLBACK TO SAVEPOINT import_save')
                    raise

                if fake:
                    cr.execute('ROLLBACK TO SAVEPOINT import_save')
