import cn_constants as C
import cn_negotiation_evaluation
from cn_negotiation import negotiate
from cn_negotiation_evaluation import three_way_comparison
from cn_ortools_reference import ExactResult
from cn_protocol import run_protocol
from cn_scenario import generate_instance


def test_three_way_comparison_matches_manual_gap_computation():
    instance = generate_instance(n_jobs=8, n_agents=2, duration_variability=0.4, travel_time_per_unit=1.0, seed=0)
    result = run_protocol(instance)
    negotiation = negotiate(instance, result)
    cmp = three_way_comparison(instance, negotiation)

    assert cmp["ortools_feasible"]
    ortools = cmp["ortools_makespan"]
    expected_gap_raw = (cmp["cnp_makespan"] - ortools) / ortools * 100.0
    expected_gap_negotiated = (cmp["negotiated_makespan"] - ortools) / ortools * 100.0
    assert abs(cmp["gap_pct_raw"] - expected_gap_raw) < 1e-9
    assert abs(cmp["gap_pct_negotiated"] - expected_gap_negotiated) < 1e-9

    if abs(expected_gap_raw) >= 1e-9:
        expected_closed = (expected_gap_raw - expected_gap_negotiated) / expected_gap_raw * 100.0
        assert abs(cmp["gap_closed_pct"] - expected_closed) < 1e-9


def test_gap_closed_pct_none_when_raw_gap_is_zero(monkeypatch):
    # CP-SATs bewusstes Aufrunden macht eine exakt-null Lücke über einen echten
    # Solver-Lauf praktisch unerreichbar (siehe feedback_cp_sat_lexicographic_
    # tiebreak.md) - der Divide-by-zero-Schutz wird daher hier direkt über einen
    # Stub-Solver getestet, der exakt den CNP-Makespan zurückgibt.
    instance = generate_instance(n_jobs=4, n_agents=2, duration_variability=0.0, travel_time_per_unit=1.0, seed=0)
    result = run_protocol(instance)
    negotiation = negotiate(instance, result)

    def _stub_solve(instance, time_limit_seconds=10.0):
        return ExactResult(
            feasible=True, optimal=True, assignment={}, starts={},
            makespan=negotiation.protocol_result.makespan, wall_time_ms=0.0,
        )

    monkeypatch.setattr(cn_negotiation_evaluation, "solve_with_ortools", _stub_solve)
    cmp = three_way_comparison(instance, negotiation)
    assert cmp["gap_pct_raw"] is not None
    assert abs(cmp["gap_pct_raw"]) < 1e-9
    assert cmp["gap_closed_pct"] is None


def test_negotiated_gap_never_negative_beyond_floating_point_noise():
    for seed in range(15):
        instance = generate_instance(
            n_jobs=8, n_agents=2, duration_variability=0.4, travel_time_per_unit=1.0, seed=seed
        )
        result = run_protocol(instance)
        negotiation = negotiate(instance, result)
        cmp = three_way_comparison(instance, negotiation)
        assert cmp["gap_pct_negotiated"] >= -1e-6, f"seed={seed}"


def test_negotiated_gap_never_exceeds_raw_gap():
    for seed in range(15):
        instance = generate_instance(
            n_jobs=8, n_agents=2, duration_variability=0.4, travel_time_per_unit=1.0, seed=seed
        )
        result = run_protocol(instance)
        negotiation = negotiate(instance, result)
        cmp = three_way_comparison(instance, negotiation)
        assert cmp["gap_pct_negotiated"] <= cmp["gap_pct_raw"] + 1e-6, f"seed={seed}"


def test_presets_produce_expected_gap_and_closure_bands():
    expected_bands = C.PRESET_EXPECTED_BANDS
    for name, params in C.PRESETS.items():
        instance = generate_instance(
            n_jobs=params["n_jobs"], n_agents=params["n_agents"],
            duration_variability=params["duration_variability"],
            travel_time_per_unit=params["travel_time_per_unit"], seed=params["seed"],
        )
        result = run_protocol(instance)
        negotiation = negotiate(instance, result)
        cmp = three_way_comparison(instance, negotiation)

        band = expected_bands[name]
        assert band["swap_count"](len(negotiation.swaps)), (
            f"{name}: swap_count={len(negotiation.swaps)}"
        )
        assert band["gap_pct_raw"][0] <= cmp["gap_pct_raw"] <= band["gap_pct_raw"][1], (
            f"{name}: gap_pct_raw={cmp['gap_pct_raw']}"
        )
        if band["gap_closed_pct"] is not None:
            lo, hi = band["gap_closed_pct"]
            assert lo <= cmp["gap_closed_pct"] <= hi, f"{name}: gap_closed_pct={cmp['gap_closed_pct']}"
