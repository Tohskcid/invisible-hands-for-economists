"""Exact-arithmetic illustration; paper proofs, not this script, establish claims."""

from fractions import Fraction as F
import json

pi_l = pi_h = F(1, 2)
v_l, c_l, k_l = F(2), F(0), F(1, 10)
v_h, c_h, k_h = F(8), F(3), F(4, 5)
a = F(1, 2)


def evaluate(n):
    A = 1 - (1 - a) ** n
    mean_v = pi_l * v_l + pi_h * v_h
    z = c_h + k_h / A
    t = pi_l * (z - v_l) / (pi_h * (v_h - z))
    assert v_l < z < mean_v and 0 < t < 1
    p = (pi_l * v_l + pi_h * t * v_h) / (pi_l + pi_h * t)
    assert p == z

    def welfare(entry_h):
        return A * (pi_l * (v_l - c_l) + pi_h * entry_h * (v_h - c_h)) - pi_l * k_l - pi_h * entry_h * k_h

    return {"n": n, "A": str(A), "z": str(z), "interior_t": str(t),
            "W_separation": str(welfare(0)), "W_interior": str(welfare(t)),
            "W_pooling": str(welfare(1))}


rows = [evaluate(n) for n in (1, 2)]
assert F(rows[0]["W_pooling"]) == F(13, 10)
assert F(rows[1]["W_separation"]) == F(7, 10)
print(json.dumps({"status": "illustration_only", "rows": rows}, indent=2))
