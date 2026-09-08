"""Vierweg-Vergleich: rohe Contract-Net-Zuteilung / Task-Swap-Verhandlung mit der
ECHTEN (eingestellten) Kommunikationsreichweite / dieselbe Verhandlung mit
uneingeschränkter Kommunikation (Diagnose: bestmöglicher Fall) / zentrales
CP-SAT-Optimum. Die uneingeschränkte Diagnose isoliert den "Preis der
Dezentralität" als echte Zahl (identischer Algorithmus, identische Nachbarschaft,
einzig der Kommunikations-Gate unterscheidet sich) statt ihn nur zu behaupten.

Zusätzlich wird der Worst Case (Reichweite=0, Totalausfall) explizit mitberechnet,
nicht nur angenommen - das belegt im Code, nicht nur in der Prosa, dass ein
Kommunikationsausfall graduell degradiert (Ergebnis = reines Contract-Net-Ergebnis)
statt total zu versagen, wie es ein zentraler Solver ohne vollständige Information
tun würde."""

from cn_negotiation import negotiate
from cn_ortools_reference import solve_with_ortools


def _gap_pct(makespan, ortools_makespan):
    if ortools_makespan is None or ortools_makespan <= 0:
        return None
    return (makespan - ortools_makespan) / ortools_makespan * 100.0


def _gap_closed_pct(gap_pct_raw, gap_pct_after):
    if gap_pct_raw is None or gap_pct_after is None or abs(gap_pct_raw) < 1e-9:
        return None
    return (gap_pct_raw - gap_pct_after) / gap_pct_raw * 100.0


def tier_comparison(
    instance,
    negotiation_result,
    communication_range,
    max_rounds=50,
    epsilon=1e-9,
    time_limit_seconds=10.0,
):
    """negotiation_result muss mit genau dieser instance/communication_range gebaut
    worden sein (negotiate(instance, protocol_result, max_rounds, epsilon,
    communication_range)) - diese Funktion baut daraus zwei zusätzliche Diagnose-Läufe
    (uneingeschränkt und Worst Case) mit denselben max_rounds/epsilon, damit alle drei
    Verhandlungs-Ergebnisse wirklich nur in der Kommunikationsreichweite differieren."""
    protocol_result = negotiation_result.protocol_result
    cnp_makespan = protocol_result.makespan

    unconstrained = negotiate(
        instance, protocol_result, max_rounds=max_rounds, epsilon=epsilon, communication_range=float("inf")
    )
    worst_case = negotiate(
        instance, protocol_result, max_rounds=max_rounds, epsilon=epsilon, communication_range=0.0
    )

    # Startpositionen, nicht Endpositionen - siehe cn_negotiation.py-Docstring:
    # die Verhandlung passiert, bevor irgendein Agent losgefahren ist.
    start_positions = instance.agent_start_positions
    blocked_pairs = tuple(
        (a, b, abs(start_positions[a] - start_positions[b]))
        for a in range(instance.n_agents)
        for b in range(a + 1, instance.n_agents)
        if abs(start_positions[a] - start_positions[b]) > communication_range
    )

    ortools_result = solve_with_ortools(instance, time_limit_seconds=time_limit_seconds)
    ortools_makespan = ortools_result.makespan if ortools_result.feasible else None

    constrained_makespan = negotiation_result.final_makespan
    unconstrained_makespan = unconstrained.final_makespan

    decentralization_cost_min = constrained_makespan - unconstrained_makespan
    decentralization_cost_pct = (
        decentralization_cost_min / unconstrained_makespan * 100.0 if unconstrained_makespan > 0 else None
    )

    gap_pct_raw = _gap_pct(cnp_makespan, ortools_makespan)
    gap_pct_constrained = _gap_pct(constrained_makespan, ortools_makespan)
    gap_pct_unconstrained = _gap_pct(unconstrained_makespan, ortools_makespan)

    return {
        "cnp_makespan": cnp_makespan,
        "communication_range": communication_range,

        "constrained_makespan": constrained_makespan,
        "constrained_swap_count": len(negotiation_result.swaps),
        "constrained_reached_local_optimum": negotiation_result.reached_local_optimum,

        "unconstrained_makespan": unconstrained_makespan,
        "unconstrained_swap_count": len(unconstrained.swaps),

        "worst_case_makespan": worst_case.final_makespan,
        "worst_case_swap_count": len(worst_case.swaps),

        "decentralization_cost_min": decentralization_cost_min,
        "decentralization_cost_pct": decentralization_cost_pct,

        "blocked_pairs": blocked_pairs,

        "ortools_makespan": ortools_makespan,
        "ortools_feasible": ortools_result.feasible,
        "ortools_optimal": ortools_result.optimal,
        "ortools_wall_time": ortools_result.wall_time_ms / 1000.0,

        "gap_pct_raw": gap_pct_raw,
        "gap_pct_constrained": gap_pct_constrained,
        "gap_pct_unconstrained": gap_pct_unconstrained,
        "gap_closed_pct_constrained": _gap_closed_pct(gap_pct_raw, gap_pct_constrained),
        "gap_closed_pct_unconstrained": _gap_closed_pct(gap_pct_raw, gap_pct_unconstrained),
    }
