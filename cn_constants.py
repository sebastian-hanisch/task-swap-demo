"""Defaults, Slider-Grenzen und Presets für die Task-Swap-Verhandlungs-Demo.
Szenario-Konstanten (Zeilen bis ORTOOLS_TIME_LIMIT_SECONDS) sind wortgleich aus
contract-net-demo übernommen - dasselbe Vehikel, siehe project memory."""

DEFAULT_N_JOBS = 8
DEFAULT_N_AGENTS = 2
DEFAULT_DURATION_VARIABILITY = 0.3
DEFAULT_TRAVEL_TIME_PER_UNIT = 1.0
DEFAULT_SEED = 7

N_JOBS_MIN, N_JOBS_MAX = 4, 16
N_AGENTS_MIN, N_AGENTS_MAX = 2, 4
DURATION_VARIABILITY_MIN, DURATION_VARIABILITY_MAX = 0.0, 1.0
TRAVEL_TIME_PER_UNIT_MIN, TRAVEL_TIME_PER_UNIT_MAX = 0.2, 2.0

POSITION_RANGE_MAX = 20.0

# Kommunikationsreichweite (Phase 2 only): wie weit zwei Agenten physisch voneinander
# entfernt sein dürfen, um überhaupt einen Tausch zu verhandeln - rohe Distanz, NICHT
# durch travel_time_per_unit skaliert (zwei unabhängige Größen: Anfahrtskosten vs.
# Kommunikationsreichweite). Max = POSITION_RANGE_MAX, da Agenten-Endpositionen nie
# weiter auseinander liegen können. Default = Max = uneingeschränkt (reproduziert das
# Verhalten vor Einführung dieses Reglers exakt).
DEFAULT_COMMUNICATION_RANGE = POSITION_RANGE_MAX
COMMUNICATION_RANGE_MIN, COMMUNICATION_RANGE_MAX = 0.0, POSITION_RANGE_MAX
DURATION_BASE_RANGE = (5, 15)
# Ein "Spitzen-Auftrag" macht die Auswirkung fehlender Rücksichtnahme sichtbar: mit
# Wahrscheinlichkeit duration_variability * SPIKE_PROBABILITY_SCALE wird ein Auftrag um
# SPIKE_MULTIPLIER verlängert. Beide Werte empirisch kalibriert (siehe calibrate_presets.py),
# nicht auf den ersten Versuch übernommen.
SPIKE_PROBABILITY_SCALE = 0.4
SPIKE_MULTIPLIER = 4.0

# OR-Tools-Referenzlauf: harte Zeitgrenze, damit ein Preset niemals hängt.
ORTOOLS_TIME_LIMIT_SECONDS = 10.0

# Ab welcher Lückengröße (Contract Net roh vs. CP-SAT) die Kernaussage-Sektion als
# "deutlich" statt "noch klein" gilt - wortgleich aus contract-net-demo übernommen.
GAP_HIGHLIGHT_THRESHOLD_PCT = 10.0

# Sicherheitsnetz gegen Endlosschleifen - bindet bei diesen Instanzgrößen nie
# wirklich (siehe test_max_rounds_cap_can_bind), analog zu ORTOOLS_TIME_LIMIT_SECONDS.
MAX_NEGOTIATION_ROUNDS = 50

# Ab welcher geschlossenen Lücke (in Prozent der ursprünglichen CNP-vs-CP-SAT-Lücke)
# die Verhandlung als "hat deutlich geholfen" statt nur "hat etwas geholfen" gilt.
GAP_CLOSED_HIGHLIGHT_THRESHOLD_PCT = 50.0

# Ab welcher VERBLEIBENDEN Lücke (nach Verhandlung, ggü. CP-SAT) die ehrliche
# Schwäche dieses Stücks (lokales Optimum, aber real bleibende Lücke) betont wird -
# unabhängig davon, wie viel Prozent der ursprünglichen Lücke schon geschlossen
# wurde (eine Instanz kann 56% schließen und trotzdem noch 24.6% Lücke übrig haben -
# das ist immer noch die "Grenzen der lokalen Suche"-Aussage, kein Erfolg).
GAP_REMAINING_WARNING_THRESHOLD_PCT = 20.0

# Seeds empirisch kalibriert via calibrate_presets.py (2026-09-07, seither gelöscht) -
# nicht der erste Versuch übernommen. Gemessene Werte (gap_raw = CNP roh vs. CP-SAT,
# gap_neg = nach Verhandlung vs. CP-SAT, closed = geschlossener Anteil der Lücke):
#   Bereits swap-optimal:             0 Tausche, gap_raw=16.7%,                closed=0%
#   Ein Tausch schließt spürbar:      1 Tausch,  gap_raw=50.4%, gap_neg=10.4%, closed=79%
#   Mehrere Verhandlungsrunden:       3 Tausche, gap_raw=34.3%, gap_neg=13.0%, closed=62%
#   Verhandlung stößt an ihre Grenzen: 2 Tausche, gap_raw=56.2%, gap_neg=24.6%, closed=56%
# Die ersten 4 Presets haben communication_range=POSITION_RANGE_MAX (uneingeschränkt) -
# ihr Punkt ist die Tausch-Dynamik selbst, nicht Kommunikation. Preset 5 (kalibriert via
# eigenem calibrate_presets.py-Lauf, 2026-09-07, seither gelöscht) zeigt gezielt einen
# durch begrenzte Kommunikationsreichweite blockierten Tausch: die beiden Agenten enden
# 8.8 Positionseinheiten auseinander, die Reichweite ist auf 8.3 gesetzt - knapp zu
# kurz. Uneingeschränkt schließt der eine mögliche Tausch die Lücke fast vollständig
# (76.1% -> 1.0%, praktisch CP-SAT-Niveau); eingeschränkt bleibt exakt das rohe
# CNP-Ergebnis (0 Tausche) - decentralization_cost_pct = 74.4%.
PRESETS = {
    "Bereits swap-optimal": {
        "n_jobs": 6, "n_agents": 2, "duration_variability": 0.0,
        "travel_time_per_unit": 1.0, "seed": 12, "communication_range": POSITION_RANGE_MAX,
    },
    "Ein Tausch schließt spürbar": {
        "n_jobs": 6, "n_agents": 2, "duration_variability": 0.0,
        "travel_time_per_unit": 1.0, "seed": 13, "communication_range": POSITION_RANGE_MAX,
    },
    "Mehrere Verhandlungsrunden": {
        "n_jobs": 10, "n_agents": 3, "duration_variability": 0.3,
        "travel_time_per_unit": 1.0, "seed": 17, "communication_range": POSITION_RANGE_MAX,
    },
    "Verhandlung stößt an ihre Grenzen": {
        "n_jobs": 10, "n_agents": 2, "duration_variability": 0.5,
        "travel_time_per_unit": 1.5, "seed": 21, "communication_range": POSITION_RANGE_MAX,
    },
    "Kommunikation begrenzt den Tausch": {
        "n_jobs": 6, "n_agents": 2, "duration_variability": 0.0,
        "travel_time_per_unit": 1.5, "seed": 60, "communication_range": 8.3,
    },
}

PRESET_HELP = {
    "Bereits swap-optimal": "Es gibt zwar eine reale Lücke zum Optimum, aber keinen "
        "einzigen wechselseitigen Tausch, der sie verkleinern würde - Verhandlung hilft nicht immer.",
    "Ein Tausch schließt spürbar": "Ein einziger akzeptierter Tausch schließt hier "
        "den Großteil der ursprünglichen Lücke zum zentralen Optimum.",
    "Mehrere Verhandlungsrunden": "Größere Instanz, mehrere Agenten - mehrere "
        "Verhandlungsrunden hintereinander schließen einen erheblichen Teil der Lücke.",
    "Verhandlung stößt an ihre Grenzen": "Die Verhandlung erreicht ihr lokales Optimum "
        "und schließt gut die Hälfte der Lücke - doch ein spürbarer Rest bleibt, den nur "
        "ein anderer Mechanismus (Auktionen, DCOP, MARL) noch schließen könnte.",
    "Kommunikation begrenzt den Tausch": "Zwei Agenten könnten sich hier gegenseitig "
        "verbessern - aber ihre Endpositionen liegen weiter auseinander, als die "
        "eingestellte Kommunikationsreichweite erlaubt. Der Preis der Dezentralität "
        "wird hier sichtbar.",
}

# Regressions-Bänder für test_negotiation_evaluation.py::
# test_presets_produce_expected_gap_and_closure_bands - hält die Kalibrierung ehrlich,
# falls cn_scenario/cn_bidding/cn_negotiation sich mal ändern.
PRESET_EXPECTED_BANDS = {
    "Bereits swap-optimal": {
        "constrained_swap_count": lambda n: n == 0, "gap_pct_raw": (8.0, 25.0),
        "gap_closed_pct_constrained": (-0.001, 0.001),
    },
    "Ein Tausch schließt spürbar": {
        "constrained_swap_count": lambda n: n == 1, "gap_pct_raw": (35.0, 65.0),
        "gap_closed_pct_constrained": (65.0, 90.0),
    },
    "Mehrere Verhandlungsrunden": {
        "constrained_swap_count": lambda n: n >= 2, "gap_pct_raw": (20.0, 50.0),
        "gap_closed_pct_constrained": (45.0, 80.0),
    },
    "Verhandlung stößt an ihre Grenzen": {
        "constrained_swap_count": lambda n: n >= 1, "gap_pct_raw": (40.0, 75.0),
        "gap_closed_pct_constrained": (40.0, 70.0),
    },
    "Kommunikation begrenzt den Tausch": {
        "constrained_swap_count": lambda n: n == 0, "unconstrained_swap_count": lambda n: n >= 1,
        "gap_pct_raw": (60.0, 90.0), "decentralization_cost_pct": (50.0, 95.0),
    },
}
