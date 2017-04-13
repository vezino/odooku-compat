from collections import OrderedDict
import itertools
import logging

from odooku.data.serialization.relations import ManyToOneSerializer


_logger = logging.getLogger(__name__)


class Dependency(object):

    def __init__(self, value, *fields):
        self.value = value
        self.fields = fields

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        if isinstance(other, Dependency):
            return other.value == self.value
        return other == self.value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "Dependency '%s'" % str(self.value)

    @classmethod
    def merge(cls, dependencies):
        return cls(dependencies[0].value, *list(itertools.chain(*[
            dependency.fields for dependency in dependencies
        ])))


class DependencyError(Exception):

    def __init__(self, nodes):
        self.nodes = nodes

    def __str__(self):
        path = []
        for node in self.nodes:
            if isinstance(node, Dependency) and node.fields:
                path.append('(%s : %s)' % ('|'.join([str(field) for field in node.fields]), str(node)))
            else:
                path.append(str(node))
        return "Cyclic dependency detected %s" % " -> ".join(path)


class DependencyGraph(OrderedDict):

    def __getitem__(self, key):
        try:
            return super(DependencyGraph, self).__getitem__(key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        self[key] = value = set()
        return value

    def invert(self):
        g = DependencyGraph()
        for (node, edges) in self.iteritems():
            for edge in edges:
                g[edge].add(node)

        return g

    def sort(self):

        incomming = OrderedDict([
            (node, list(edges)) for node, edges in self.iteritems()
        ])

        # Try to output nodes in initial order
        nodes = [node for node in incomming.iterkeys()]
        # Keep a stack in order to detect cyclic dependencies

        stack = []
        while nodes:
            # Get first node
            n = nodes[0]
            # See if this node has dependencies which haven't yet been
            # outputted.
            remaining = [node for node in reversed(incomming[n]) if node in nodes]
            if remaining:
                if n not in stack:
                    stack.append(n)
                else:
                    raise DependencyError(stack + [n])
                for m in remaining:
                    # Place dependency at front
                    nodes.remove(m)
                    nodes.insert(0, m)
            else:
                # No dependencies left, output
                yield nodes.pop(0)

    @classmethod
    def from_models(cls, models, serializers):
        g = cls()

        def find_dependencies(serializer, nk=False, result=None):
            if result is None:
                result = {}

            fields = nk and serializer.nk or serializer.fields.iterkeys()
            for field_name in fields:
                field = serializer.fields[field_name]
                if isinstance(field, ManyToOneSerializer):
                    if field.relation == serializer.model_name:
                        continue

                    relation_serializer = serializers[field.relation]
                    dependency = Dependency(field.relation, field)
                    if dependency in result:
                        dependency = Dependency.merge([dependency, result[dependency]])
                    result[dependency] = dependency
                    if field.relation not in result:
                        find_dependencies(relation_serializer, nk=True, result=result)

            return list(result.itervalues())

        for model_name in models:
            g[model_name] = find_dependencies(serializers[model_name])

        return g
