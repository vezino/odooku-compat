import json


class ModelSerializerConfig(object):

    def __init__(self, excludes=None, includes=None, nk=None):
        if includes and excludes:
            raise ValueError("Define either includes or exlcudes, not both")

        self.excludes = excludes or []
        self.includes = includes or []
        self.nk = nk or []


class ExportConfig(object):

    def __init__(self, excludes=None, includes=None, models=None):
        if includes and excludes:
            raise ValueError("Define either includes or exlcudes, not both")

        self.excludes = excludes or []
        self.includes = includes or []
        self.models = {
            k: ModelSerializerConfig(**v) for
            (k, v) in (models or {}).iteritems()
        }

    @classmethod
    def from_file(cls, path):
        with open(path, 'r') as fp:
            return cls(**json.load(fp))
