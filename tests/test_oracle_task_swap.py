"""Unabhängige Orakel: (1) Vollenumeration (cn_bruteforce) als untere Schranke für CP-SAT,
Contract Net und Verhandlung; (2) exakt rationale Neuimplementierung der Steilster-Abstieg-
Verhandlung (Fractions, eigene Schleifen); (3) reale statt aufgerundeter CP-SAT-Zielwert."""
import random
from fractions import Fraction as F

import cn_negotiation as neg
import cn_ortools_reference as ref
import cn_protocol
from cn_bruteforce import solve_bruteforce
from cn_scenario import generate_instance


def _finish_times(inst, sched):
    out = []
    for a in range(inst.n_agents):
        t, pos = F(0), F(inst.agent_start_positions[a])
        for j in sched.get(a, ()):
            jb = inst.jobs[j]
            t += abs(pos - F(jb.position)) * F(inst.travel_time_per_unit) + F(jb.duration)
            pos = F(jb.position)
        out.append(t)
    return out


def _negotiate_ref(inst, sched, comm_range):
    sched = {a: list(v) for a, v in sched.items()}
    cur = max(_finish_times(inst, sched))
    swaps = []
    for _ in range(50):
        best, best_d = None, -F(1e-9)
        ids = [a for a in sorted(sched) if sched[a]]
        for ia, a in enumerate(ids):
            for b in ids[ia + 1:]:
                if abs(inst.agent_start_positions[a] - inst.agent_start_positions[b]) > comm_range:
                    continue
                for ja in sched[a]:
                    for jb in sched[b]:
                        s2 = dict(sched)
                        s2[a] = sorted([x for x in sched[a] if x != ja] + [jb])
                        s2[b] = sorted([x for x in sched[b] if x != jb] + [ja])
                        d = max(_finish_times(inst, s2)) - cur
                        if d < best_d:
                            best, best_d = (a, b, ja, jb, s2, cur + d), d
        if best is None:
            break
        a, b, ja, jb, sched, cur = best
        swaps.append((a, b, ja, jb))
    return swaps, cur


def test_negotiation_matches_exact_rational_reimplementation():
    rng = random.Random(3)
    for _ in range(40):
        inst = generate_instance(rng.randint(3, 8), rng.randint(2, 4), rng.choice([0.0, 0.5, 1.0]),
                                 rng.choice([0.2, 1.0, 2.0]), rng.randrange(10 ** 4))
        pr = cn_protocol.run_protocol(inst)
        for rr in (float("inf"), 0.0, 5.0, 10.0):
            res = neg.negotiate(inst, pr, communication_range=rr)
            swaps, final = _negotiate_ref(inst, pr.schedules, rr)
            assert [(s.agent_a, s.agent_b, s.job_from_a, s.job_from_b) for s in res.swaps] == swaps
            assert abs(res.final_makespan - float(final)) < 1e-7


def test_cp_sat_reports_real_makespan_close_to_bruteforce_optimum():
    rng = random.Random(7)
    for _ in range(40):
        inst = generate_instance(rng.randint(4, 5), rng.randint(1, 3), rng.choice([0.0, 0.5, 1.0]),
                                 rng.choice([0.2, 1.0, 2.0]), rng.randrange(10 ** 4))
        bf, _ = solve_bruteforce(inst)
        ex = ref.solve_with_ortools(inst, time_limit_seconds=5.0)
        assert ex.feasible and ex.optimal
        assert ex.makespan >= bf - 1e-9  # reales Makespan einer zulässigen Lösung
        assert ex.makespan <= bf + 0.25  # nur Rest der aufgerundeten Modellwahl
        assert ex.model_makespan >= ex.makespan - 1e-9  # Modellwert ist aufgerundet


def test_heuristics_are_never_below_the_reported_optimum_on_regression_instances():
    # Auf diesen Instanzen lag der AUFGERUNDETE Modellwert ueber Contract Net/Verhandlung
    # (negative "Luecke" in der App); der reale Optimalwert darf sie nie unterbieten.
    for args in [(4, 3, 0.5, 0.2, 1485), (4, 4, 1.0, 1.0, 2580), (4, 4, 0.0, 0.2, 584),
                 (5, 2, 0.0, 1.0, 5345), (4, 4, 0.5, 1.0, 3762), (4, 4, 0.0, 0.2, 3436)]:
        inst = generate_instance(*args)
        pr = cn_protocol.run_protocol(inst)
        res = neg.negotiate(inst, pr)
        ex = ref.solve_with_ortools(inst, time_limit_seconds=5.0)
        assert res.final_makespan >= ex.makespan - 1e-9, args
        assert pr.makespan >= res.final_makespan - 1e-9, args
