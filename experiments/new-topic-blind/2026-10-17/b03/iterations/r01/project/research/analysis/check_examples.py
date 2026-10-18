"""Finite exact-arithmetic checks of examples in research/model/handoff.md.

These assertions validate stated counterexamples and edge cases; they do not
replace the paper proofs.
"""

from fractions import Fraction as Q
from itertools import combinations


def subsets(n):
    items = range(n)
    return [frozenset(s) for k in range(n + 1) for s in combinations(items, k)]


def demand(value, prices):
    scores = {
        s: value[s] - sum((prices[j] for j in s), Q(0))
        for s in value
    }
    best = max(scores.values())
    return {s for s, score in scores.items() if score == best}


def exchange(value):
    for x in value:
        for y in value:
            for i in x - y:
                move = value[x - {i}] + value[y | {i}]
                swaps = [
                    value[(x - {i}) | {j}] + value[(y - {j}) | {i}]
                    for j in y - x
                ]
                if value[x] + value[y] > max([move, *swaps]):
                    return False
    return True


def submodular(value):
    return all(
        value[x] + value[y] >= value[x | y] + value[x & y]
        for x in value
        for y in value
    )


two = subsets(2)
v = {s: Q(len(s)) for s in two}
h = {s: v[s] + (Q(2) if len(s) == 2 else Q(0)) for s in two}
assert exchange(v)
assert not exchange(h)
assert demand(h, (Q(3, 2), Q(3, 2))) == {frozenset({0, 1})}
assert demand(h, (Q(4), Q(3, 2))) == {frozenset()}

three = subsets(3)
coverage = {
    s: Q(bool(s & {0, 2})) + Q(bool(s & {1, 2}))
    for s in three
}
assert submodular(coverage)
assert not exchange(coverage)
assert demand(coverage, (Q(2, 5), Q(2, 5), Q(9, 10))) == {
    frozenset({0, 1})
}
assert demand(coverage, (Q(7, 10), Q(2, 5), Q(9, 10))) == {
    frozenset({2})
}

four = subsets(4)
concave = {s: Q(min(len(s), 2)) for s in four}
convex = {s: Q(len(s) ** 2) for s in four}
assert exchange(concave)
assert not exchange(convex)

additive = [
    {s: sum((Q(a[j]) for j in s), Q(0)) for s in three}
    for a in ((3, -1, 0), (2, 4, -1))
]
prices = (Q(3), Q(4), Q(0))
allocation = (frozenset({0}), frozenset({1}))
assert all(all(s.isdisjoint(t) for t in allocation[i + 1 :])
               for i, s in enumerate(allocation))
assert all(allocation[i] in demand(additive[i], prices) for i in range(2))
assert prices[2] == 0

print("Exact finite checks passed: C1, C2, C3, and P6 boundary case.")
