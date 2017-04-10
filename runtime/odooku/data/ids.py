def hash_id(id):
    if isinstance(id, dict):
        return hash(tuple(sorted(
            (k, hash_id(v)) for (k, v) in id.iteritems()
        )))
    return id


def is_pk(id):
    return isinstance(id, int)

def is_nk(id):
    return isinstance(id, dict)

def is_link(id):
    return isinstance(id, basestring)
