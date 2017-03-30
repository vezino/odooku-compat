class ModelConfig(object):

    def __init__(self):
        self.includes = []
        self.excludes = []
        self.fields = {}

    @classmethod
    def factory(cls, excludes=None, includes=None, models=None):
        config = cls()
        if excludes:
            config.excludes = excludes
        return config

class ExportConfig(object):

    def __init__(self):
        self.includes = []
        self.excludes = []
        self.models = {}

    @classmethod
    def factory(cls, excludes=None, includes=None, models=None):
        config = cls()
        if excludes:
            config.excludes = excludes

        return config

    @classmethod
    def from_file(cls, path):
        return cls.factory()
