from .base import BaseFieldSerializer


class RelationSerializer(BaseFieldSerializer):

    def __init__(self, field_name, relation):
        self._field_name = field_name
        self._relation = relation

    @property
    def dependencies(self):
        return [self._relation]

    @classmethod
    def factory(cls, field_name, field, config=None):
        return cls(field_name, field['relation'])


class ManyToOneSerializer(RelationSerializer):
    pass
