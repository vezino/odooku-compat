from collections import OrderedDict


class CyclicDependencyError(Exception):
    def __init__(self, nodes):
        self.message = "Cyclic dependency {0}".format(
            '->'.join(
                [
                    str(x) for x in (
                        nodes
                    )
                ]
            )
        )
        self.nodes = nodes

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, self.message)


def topological_sort(graph):
    """
    Performs a dependency based topological sort. Keeping a stable order.

    Arguments:
        - graph: An (ordered) dictionary representing a directed graph. Where each item
        is { node: [set or list of incomming edges (depedencies)] }
    """

    # Copy graph for lookup purposes
    incomming = OrderedDict(
        [
            (node, list(edges)) for node, edges in graph.iteritems()
        ]
    )

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
                raise CyclicDependencyError(stack + [n])
            for m in remaining:
                # Place dependency at front
                nodes.remove(m)
                nodes.insert(0, m)
        else:
            # No dependencies left, output
            yield nodes.pop(0)
