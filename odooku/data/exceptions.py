class NaturalKeyError(Exception):
    pass


class NaturalKeyMultipleFound(NaturalKeyError):
    pass


class NaturalKeyNotFound(NaturalKeyError):
    pass


class NaturalKeyMissing(NaturalKeyError):
    pass


class NaturalKeyInvalid(NaturalKeyError):
    pass


class LinkNotFound(Exception):
    pass


class ModelMissing(Exception):
    pass
