class DeserializerContext(object):

    def __init__(self, env, model_deserializers):
        self.env = env
        self.model_deserializers = model_deserializers
        self.nk_links = {}

    def hash_nk(self, nk):
        return hash(tuple(sorted(
            (k, self.hash_nk(v) if isinstance(v, dict) else v) for (k, v) in nk.iteritems()
        )))

    def link_nk(self, model_name, nk, pk):
        if model_name not in self.nk_links:
            self.nk_links[model_name] = {}
        self.nk_links[model_name][self.hash_nk(nk)] = pk

    def resolve_nk(self, model_name, nk):
        if model_name in self.nk_links:
            return self.nk_links[model_name].get(self.hash_nk(nk), None)
