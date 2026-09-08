from cn_negotiation import EPSILON, negotiate
from cn_ortools_reference import SCALE, solve_with_ortools
from cn_protocol import ProtocolResult, run_protocol
from cn_scenario import Instance, Job, generate_instance
from cn_schedule import schedule_from_assignment

# Siehe test_ortools_reference.py: CP-SAT rundet Zeiten bewusst AUF.
_ROUNDING_TOLERANCE_PER_JOB = 2.0 / SCALE


def _instance(jobs, n_agents=2, agent_start_positions=None, travel_time_per_unit=1.0):
    if agent_start_positions is None:
        agent_start_positions = tuple(0.0 for _ in range(n_agents))
    return Instance(
        n_jobs=len(jobs), n_agents=n_agents, jobs=jobs,
        agent_start_positions=agent_start_positions, travel_time_per_unit=travel_time_per_unit,
    )


def test_swap_reduces_makespan_hand_computed_tiny_example():
    # Beide Agenten starten bei Position 0. Job0 (dauer 10) und Job1 (dauer 1)
    # liegen bei Agent0/1's Start (0), Job2 (dauer 1) liegt weit weg bei 50.
    # CNP vergibt Job0->A0 (Gleichstand, niedrigere Agenten-ID gewinnt), Job1->A1
    # (A1 ist noch frei), Job2->A1 (A1 ist naeher an 50 als das inzwischen mit
    # Job0 beschaeftigte A0 - Anfahrt dominiert). Ergebnis: A0={0} frei=10,
    # A1={1,2} frei=52, Makespan=52 - schlecht, weil A1 nun den weiten Auftrag 2
    # UND den nahen Auftrag 1 hat, waehrend A0 mit nur einem kurzen Auftrag
    # untätig bleibt. Der Tausch Job0<->Job2 behebt das: A0={2} frei=51 (fährt
    # selbst zu Position 50), A1={0,1} frei=11 - Makespan sinkt auf 51.
    jobs = (
        Job(index=0, position=0.0, duration=10.0),
        Job(index=1, position=0.0, duration=1.0),
        Job(index=2, position=50.0, duration=1.0),
    )
    instance = _instance(jobs, n_agents=2, agent_start_positions=(0.0, 0.0))

    result = run_protocol(instance)
    assert result.schedules == {0: (0,), 1: (1, 2)}
    assert result.makespan == 52.0

    negotiation = negotiate(instance, result)

    assert len(negotiation.swaps) == 1
    swap = negotiation.swaps[0]
    assert swap.round == 1
    assert swap.agent_a == 0
    assert swap.agent_b == 1
    assert swap.job_from_a == 0
    assert swap.job_from_b == 2
    assert swap.schedules_after == {0: (2,), 1: (0, 1)}
    assert swap.agent_finish_times_after == (51.0, 11.0)
    assert swap.makespan_after == 51.0

    assert negotiation.final_schedules == {0: (2,), 1: (0, 1)}
    assert negotiation.final_assignment == {0: 1, 1: 1, 2: 0}
    assert negotiation.final_agent_finish_times == (51.0, 11.0)
    assert negotiation.final_makespan == 51.0
    assert negotiation.reached_local_optimum is True


def test_negotiation_never_increases_makespan_across_random_instances():
    for seed in range(30):
        instance = generate_instance(
            n_jobs=8, n_agents=2, duration_variability=0.4, travel_time_per_unit=1.0, seed=seed
        )
        result = run_protocol(instance)
        negotiation = negotiate(instance, result)
        assert negotiation.final_makespan <= result.makespan + EPSILON, f"seed={seed}"


def test_negotiation_preserves_job_completeness_and_ascending_order():
    for seed in range(30):
        instance = generate_instance(
            n_jobs=10, n_agents=3, duration_variability=0.5, travel_time_per_unit=1.0, seed=seed
        )
        result = run_protocol(instance)
        negotiation = negotiate(instance, result)

        all_jobs = sorted(j for jobs in negotiation.final_schedules.values() for j in jobs)
        assert all_jobs == list(range(10)), f"seed={seed}"
        assert sorted(negotiation.final_assignment.keys()) == list(range(10)), f"seed={seed}"

        for agent_id, jobs in negotiation.final_schedules.items():
            assert list(jobs) == sorted(jobs), f"seed={seed} agent={agent_id}"


def test_negotiation_reaches_verified_local_optimum():
    for seed in range(20):
        instance = generate_instance(
            n_jobs=8, n_agents=3, duration_variability=0.5, travel_time_per_unit=1.2, seed=seed
        )
        result = run_protocol(instance)
        negotiation = negotiate(instance, result)
        if not negotiation.reached_local_optimum:
            continue

        schedules = negotiation.final_schedules
        _, current_makespan = schedule_from_assignment(instance, schedules)
        agent_ids = sorted(a for a in schedules if len(schedules[a]) > 0)
        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                agent_a, agent_b = agent_ids[i], agent_ids[j]
                for job_from_a in schedules[agent_a]:
                    for job_from_b in schedules[agent_b]:
                        candidate = dict(schedules)
                        candidate[agent_a] = tuple(
                            sorted([j for j in schedules[agent_a] if j != job_from_a] + [job_from_b])
                        )
                        candidate[agent_b] = tuple(
                            sorted([j for j in schedules[agent_b] if j != job_from_b] + [job_from_a])
                        )
                        _, candidate_makespan = schedule_from_assignment(instance, candidate)
                        delta = candidate_makespan - current_makespan
                        assert delta >= -EPSILON, (
                            f"seed={seed} found an improving swap after claimed local optimum: "
                            f"agents=({agent_a},{agent_b}) jobs=({job_from_a},{job_from_b}) delta={delta}"
                        )


def test_single_agent_no_swap_possible():
    instance = generate_instance(n_jobs=6, n_agents=1, duration_variability=0.5, travel_time_per_unit=1.0, seed=0)
    result = run_protocol(instance)
    negotiation = negotiate(instance, result)
    assert negotiation.swaps == ()
    assert negotiation.reached_local_optimum is True
    assert negotiation.final_schedules == result.schedules
    assert negotiation.final_makespan == result.makespan


def test_negotiation_never_beats_cp_sat_optimum():
    for seed in range(10):
        instance = generate_instance(
            n_jobs=7, n_agents=2, duration_variability=0.4, travel_time_per_unit=1.0, seed=seed
        )
        result = run_protocol(instance)
        negotiation = negotiate(instance, result)
        exact = solve_with_ortools(instance, time_limit_seconds=5.0)
        assert exact.feasible, f"seed={seed}"
        tolerance = _ROUNDING_TOLERANCE_PER_JOB * instance.n_jobs
        assert negotiation.final_makespan >= exact.makespan - tolerance, f"seed={seed}"


def test_swap_step_schedules_are_internally_consistent():
    for seed in range(15):
        instance = generate_instance(
            n_jobs=9, n_agents=3, duration_variability=0.5, travel_time_per_unit=1.3, seed=seed
        )
        result = run_protocol(instance)
        negotiation = negotiate(instance, result)
        for swap in negotiation.swaps:
            finish_times, makespan = schedule_from_assignment(instance, swap.schedules_after)
            assert finish_times == swap.agent_finish_times_after, f"seed={seed} round={swap.round}"
            assert makespan == swap.makespan_after, f"seed={seed} round={swap.round}"


def test_negotiation_only_considers_genuine_two_for_two_swaps():
    # Ein Agent, der zu Beginn keinen einzigen Auftrag besitzt, darf niemals an
    # einem Tausch beteiligt sein (echte Zwei-fuer-zwei-Tausche, keine
    # einseitigen "Geschenke").
    instance = generate_instance(n_jobs=4, n_agents=4, duration_variability=0.5, travel_time_per_unit=1.0, seed=1)
    result = run_protocol(instance)
    empty_agents = {a for a, jobs in result.schedules.items() if len(jobs) == 0}
    if not empty_agents:
        return
    negotiation = negotiate(instance, result)
    for swap in negotiation.swaps:
        assert swap.agent_a not in empty_agents
        assert swap.agent_b not in empty_agents


def test_max_rounds_cap_can_bind():
    found = False
    for seed in range(40):
        instance = generate_instance(
            n_jobs=10, n_agents=3, duration_variability=0.5, travel_time_per_unit=1.5, seed=seed
        )
        result = run_protocol(instance)
        full = negotiate(instance, result)
        if len(full.swaps) >= 2:
            found = True
            capped = negotiate(instance, result, max_rounds=1)
            assert capped.reached_local_optimum is False
            assert len(capped.swaps) == 1
            assert capped.swaps[0] == full.swaps[0]
            break
    assert found, "no swept seed needed >=2 rounds - widen the sweep"


def test_tie_break_is_deterministic():
    for seed in range(15):
        instance = generate_instance(
            n_jobs=8, n_agents=3, duration_variability=0.5, travel_time_per_unit=1.0, seed=seed
        )
        result = run_protocol(instance)
        first = negotiate(instance, result)
        second = negotiate(instance, result)
        assert first.swaps == second.swaps, f"seed={seed}"


def test_default_communication_range_is_truly_unconstrained():
    for seed in range(15):
        instance = generate_instance(
            n_jobs=8, n_agents=3, duration_variability=0.5, travel_time_per_unit=1.0, seed=seed
        )
        result = run_protocol(instance)
        default = negotiate(instance, result)
        explicit_inf = negotiate(instance, result, communication_range=float("inf"))
        assert default.swaps == explicit_inf.swaps, f"seed={seed}"
        assert default.final_makespan == explicit_inf.final_makespan, f"seed={seed}"


def _fake_protocol_result(instance, schedules):
    # Baut einen minimalen ProtocolResult direkt aus einer Zuteilung, ohne den echten
    # CNP-Bietprozess zu durchlaufen - legitim hier, weil negotiate() nur .schedules
    # liest (agent_finish_times/makespan werden intern über schedule_from_assignment
    # neu berechnet, .steps wird für das Kommunikations-Gate nicht mehr gebraucht -
    # das Gate nutzt instance.agent_start_positions direkt, siehe cn_negotiation.py).
    finish_times, makespan = schedule_from_assignment(instance, schedules)
    return ProtocolResult(steps=(), assignment={}, schedules=schedules, agent_finish_times=finish_times, makespan=makespan)


def test_communication_range_hand_computed_gate_boundary():
    # Agent 0 startet bei 0.0, Agent 1 bei 50.0 - Distanz 50.0 exakt. Agent 0 haelt
    # Job0 (pos0, dauer10) und Job1 (pos50, dauer1), Agent 1 haelt Job2 (pos0, dauer1).
    # Agent 0: 0 -> Job0 (0+0+10=10) -> Job1 (10+50+1=61). Agent 1: 50 -> Job2
    # (0+50+1=51). Makespan=61. Der Tausch Job1<->Job2 (Agent0 gibt den weiten
    # Auftrag ab, Agent1 den nahen) senkt den Makespan drastisch auf 11.
    jobs = (
        Job(index=0, position=0.0, duration=10.0),
        Job(index=1, position=50.0, duration=1.0),
        Job(index=2, position=0.0, duration=1.0),
    )
    instance = _instance(jobs, n_agents=2, agent_start_positions=(0.0, 50.0))
    schedules = {0: (0, 1), 1: (2,)}
    result = _fake_protocol_result(instance, schedules)
    assert result.makespan == 61.0

    blocked = negotiate(instance, result, communication_range=49.0)
    assert blocked.swaps == ()
    assert blocked.final_makespan == 61.0

    allowed = negotiate(instance, result, communication_range=50.0)
    assert len(allowed.swaps) == 1
    assert allowed.swaps[0].job_from_a == 1
    assert allowed.swaps[0].job_from_b == 2
    assert allowed.final_makespan == 11.0


def test_communication_range_uses_raw_distance_not_travel_time():
    jobs = (
        Job(index=0, position=0.0, duration=10.0),
        Job(index=1, position=50.0, duration=1.0),
        Job(index=2, position=0.0, duration=1.0),
    )
    schedules = {0: (0, 1), 1: (2,)}
    for travel_time_per_unit in (0.2, 1.0, 2.0):
        instance = _instance(
            jobs, n_agents=2, agent_start_positions=(0.0, 50.0), travel_time_per_unit=travel_time_per_unit
        )
        result = _fake_protocol_result(instance, schedules)
        blocked = negotiate(instance, result, communication_range=49.0)
        assert blocked.swaps == (), f"travel_time_per_unit={travel_time_per_unit}"


def test_communication_range_ignores_idle_agents_regardless_of_position_source():
    instance = generate_instance(n_jobs=2, n_agents=4, duration_variability=0.5, travel_time_per_unit=1.0, seed=1)
    result = run_protocol(instance)
    empty_agents = {a for a, jobs in result.schedules.items() if len(jobs) == 0}
    assert empty_agents, "expected at least one idle agent for this fixture"
    for communication_range in (0.0, 5.0, 20.0):
        negotiation = negotiate(instance, result, communication_range=communication_range)
        for swap in negotiation.swaps:
            assert swap.agent_a not in empty_agents
            assert swap.agent_b not in empty_agents


def test_communication_range_zero_on_single_agent_is_a_noop():
    instance = generate_instance(n_jobs=6, n_agents=1, duration_variability=0.5, travel_time_per_unit=1.0, seed=0)
    result = run_protocol(instance)
    negotiation = negotiate(instance, result, communication_range=0.0)
    assert negotiation.swaps == ()
    assert negotiation.final_schedules == result.schedules


def test_communication_range_preserves_job_completeness_and_determinism_when_constrained():
    for communication_range in (0.0, 5.0, 10.0, float("inf")):
        for seed in range(10):
            instance = generate_instance(
                n_jobs=10, n_agents=3, duration_variability=0.5, travel_time_per_unit=1.0, seed=seed
            )
            result = run_protocol(instance)
            first = negotiate(instance, result, communication_range=communication_range)
            second = negotiate(instance, result, communication_range=communication_range)
            assert first.swaps == second.swaps, f"range={communication_range} seed={seed}"

            all_jobs = sorted(j for jobs in first.final_schedules.values() for j in jobs)
            assert all_jobs == list(range(10)), f"range={communication_range} seed={seed}"
            for agent_id, jobs in first.final_schedules.items():
                assert list(jobs) == sorted(jobs), f"range={communication_range} seed={seed} agent={agent_id}"


def test_zero_communication_range_reduces_to_raw_cnp_result():
    # Der Robustheits-Kern: bei Totalausfall (Reichweite=0) existiert kein zulaessiges
    # Agentenpaar - das Ergebnis ist dann EXAKT das unveraenderte Contract-Net-Ergebnis,
    # nie ein Absturz oder ein ungueltiger Zustand.
    for n_agents in (1, 2, 3, 4):
        for seed in range(15):
            instance = generate_instance(
                n_jobs=8, n_agents=n_agents, duration_variability=0.5, travel_time_per_unit=1.0, seed=seed
            )
            result = run_protocol(instance)
            negotiation = negotiate(instance, result, communication_range=0.0)
            assert negotiation.swaps == (), f"n_agents={n_agents} seed={seed}"
            assert negotiation.final_makespan == result.makespan, f"n_agents={n_agents} seed={seed}"
            assert negotiation.final_schedules == result.schedules, f"n_agents={n_agents} seed={seed}"
