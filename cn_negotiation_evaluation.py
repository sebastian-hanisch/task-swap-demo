"""Dreiweg-Vergleich: rohe Contract-Net-Zuteilung vs. nach Task-Swap-
Verhandlung vs. zentrales CP-SAT-Optimum - inklusive der Kennzahl, wie viel
der ursprünglichen Lücke die Verhandlung geschlossen hat."""

from cn_ortools_reference import solve_with_ortools


def three_way_comparison(instance, negotiation_result, time_limit_seconds=10.0):
    cnp_makespan = negotiation_result.protocol_result.makespan
    negotiated_makespan = negotiation_result.final_makespan

    ortools_result = solve_with_ortools(instance, time_limit_seconds=time_limit_seconds)
    ortools_makespan = ortools_result.makespan if ortools_result.feasible else None

    gap_pct_raw = None
    gap_pct_negotiated = None
    gap_closed_pct = None
    if ortools_result.feasible and ortools_makespan > 0:
        gap_pct_raw = (cnp_makespan - ortools_makespan) / ortools_makespan * 100.0
        gap_pct_negotiated = (negotiated_makespan - ortools_makespan) / ortools_makespan * 100.0
        if abs(gap_pct_raw) >= 1e-9:
            gap_closed_pct = (gap_pct_raw - gap_pct_negotiated) / gap_pct_raw * 100.0

    return {
        "cnp_makespan": cnp_makespan,
        "negotiated_makespan": negotiated_makespan,
        "negotiated_swap_count": len(negotiation_result.swaps),
        "reached_local_optimum": negotiation_result.reached_local_optimum,
        "ortools_makespan": ortools_makespan,
        "ortools_feasible": ortools_result.feasible,
        "ortools_optimal": ortools_result.optimal,
        "ortools_wall_time": ortools_result.wall_time_ms / 1000.0,
        "gap_pct_raw": gap_pct_raw,
        "gap_pct_negotiated": gap_pct_negotiated,
        "gap_closed_pct": gap_closed_pct,
    }
