def hash_pk(pk):
    if isinstance(pk, dict):
        return hash(tuple(sorted(
            (k, hash_pk(v)) for (k, v) in pk.iteritems()
        )))
    return pk


def is_pk(pk):
    return isinstance(pk, int)

def is_nk(pk):
    return isinstance(pk, dict)

def is_link(pk):
    return isinstance(pk, basestring)
