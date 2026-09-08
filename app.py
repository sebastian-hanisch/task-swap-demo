"""
Task-Swap-Verhandlung nach dem Contract Net Protocol – interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Zweites Stück der "Konzepte"-Reihe, Multi-Agenten-Koordinations-Linie - direkte
Fortsetzung von contract-net-demo (Contract Net Protocol, Smith 1980). Phase 1
(unverändert aus contract-net-demo übernommen) vergibt Aufträge online/myopisch;
Phase 2 (neu) verhandelt danach paarweise Tausche zwischen Agenten - offline
(kennt die vollständige Zuteilung), aber nur lokal (keine erschöpfende Suche).

Lauffähig mit: streamlit run app.py
"""

import time

import streamlit as st

import cn_constants as C
from cn_evaluation import stats_up_to_step
from cn_negotiation import negotiate
from cn_negotiation_evaluation import tier_comparison
from cn_negotiation_visualization import build_negotiation_schedule_figure, describe_swap
from cn_presets import (
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sync_query_params,
)
from cn_protocol import run_protocol
from cn_scenario import generate_instance
from cn_visualization import build_bid_chart, build_schedule_figure

st.set_page_config(page_title="Task-Swap-Verhandlung – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _compute_protocol(n_jobs, n_agents, duration_variability, travel_time_per_unit, seed):
    instance = generate_instance(n_jobs, n_agents, duration_variability, travel_time_per_unit, seed)
    result = run_protocol(instance)
    return instance, result


@st.cache_data(show_spinner=False)
def _compute_negotiation(n_jobs, n_agents, duration_variability, travel_time_per_unit, seed, communication_range):
    instance = generate_instance(n_jobs, n_agents, duration_variability, travel_time_per_unit, seed)
    result = run_protocol(instance)
    negotiation = negotiate(
        instance, result, max_rounds=C.MAX_NEGOTIATION_ROUNDS, communication_range=communication_range,
    )
    return negotiation


@st.cache_data(show_spinner=False)
def _compute_comparison(n_jobs, n_agents, duration_variability, travel_time_per_unit, seed, communication_range):
    negotiation = _compute_negotiation(
        n_jobs, n_agents, duration_variability, travel_time_per_unit, seed, communication_range,
    )
    instance = generate_instance(n_jobs, n_agents, duration_variability, travel_time_per_unit, seed)
    return tier_comparison(
        instance, negotiation, communication_range,
        max_rounds=C.MAX_NEGOTIATION_ROUNDS, time_limit_seconds=C.ORTOOLS_TIME_LIMIT_SECONDS,
    )


st.title("🔄 Task-Swap-Verhandlung nach dem Contract Net Protocol")
st.markdown(
    """
Direkte Fortsetzung von **contract-net-demo**: Nachdem das **Contract Net Protocol**
(Smith, 1980) alle Aufträge vergeben hat - online, myopisch, unwiderruflich -
verhandeln je zwei Agenten anschließend paarweise: wenn ein wechselseitiger Tausch
zweier eigener Aufträge den Makespan senkt, wird er akzeptiert. Wie der aufgeklappte
Abschnitt "Wie funktioniert diese Demo?" zeigt, holt das einiges an verlorener
Qualität zurück - aber nicht alles.
"""
)
st.caption(
    "Drei Stufen, nicht zwei: **Contract Net** (online, keine Rücksicht auf spätere "
    "Aufträge) → **Task-Swap-Verhandlung** (offline, aber nur lokale Suche über "
    "paarweise Tausche) → **CP-SAT** (offline, erschöpfend/global optimal). Die "
    "Verhandlung liegt bewusst dazwischen - besser als reines Contract Net, aber nicht "
    "notwendigerweise so gut wie die zentrale Lösung."
)

with st.expander("Wie funktioniert diese Demo?", expanded=True):
    st.markdown(
        r"""
**Phase 1 - Contract Net Protocol (Rekapitulation)**: Aufträge werden einzeln in
Ankunftsreihenfolge angekündigt, jeder Agent bietet seine eigene Fertigstellungszeit
(`freie_Zeit + Anfahrtszeit + Auftragsdauer`), das niedrigste Gebot gewinnt - endgültig.
(Details siehe contract-net-demo; diese Demo ist eigenständig lauffähig und
wiederholt das Nötigste unten.)

**Phase 2 - Task-Swap-Verhandlung (neu)**: Sobald ALLE Aufträge vergeben sind, kennt
die Verhandlung - anders als die Vergabe selbst - die vollständige Zuteilung. Je zwei
Agenten prüfen, ob ein **wechselseitiger** Tausch (Agent A gibt einen eigenen Auftrag
an Agent B ab, erhält im Gegenzug einen Auftrag von B) den Gesamt-Makespan senkt. Der
beste gefundene Tausch pro Runde wird akzeptiert, dann wird neu geprüft - bis kein
verbessernder Tausch mehr existiert (**lokales Optimum**). Ein Tausch ändert nur, WEM
ein Auftrag gehört, nie die Reihenfolge innerhalb der Warteschlange eines Agenten
(bleibt aufsteigend nach Auftrags-Index) - und es gibt bewusst KEINE einseitigen
"Geschenke" (ein Auftrag wandert ohne Gegenzug). Eine Erweiterung um solche Geschenke
oder um Mehrfach-Tausche wäre denkbar, ist hier aber bewusst nicht Teil des Mechanismus.

**Kommunikationsreichweite**: ein Agentenpaar wird nur betrachtet, wenn die ROHE
physische Distanz ihrer Endpositionen (nach Phase 1) die eingestellte
Kommunikationsreichweite nicht überschreitet - unabhängig von der Anfahrtszeit pro
Positionseinheit (das ist eine zweite, unabhängige Größe: wie teuer eine Fahrt ist,
ist nicht dasselbe wie wie weit ein Agent überhaupt kommunizieren kann). Das ist der
einzige Punkt in dieser Demo, an dem "mehrere Agenten" tatsächlich etwas anderes
bedeutet als "eine zentrale lokale Suche" - ohne dieses Gate würde die Verhandlung
mechanisch exakt einer zentralen Lokalsuche entsprechen, nur mit Agenten-Vokabular.

**Die ehrliche Grenze dieses Stücks - und ihre Kehrseite**: paarweise, wechselseitige
Tausche sind eine **lokale** Suche - sie können in einem lokalen Optimum
steckenbleiben, das oberhalb des von CP-SAT gefundenen globalen Optimums liegt.
Genau das motiviert die übrigen, noch nicht gebauten Stücke dieser Linie
(Kombinatorische Auktionen, Distributed Constraint Optimization, Multi-Agent
Reinforcement Learning), die diese Grenze über jeweils einen anderen Mechanismus
überwinden. Das ist aber nur die halbe Wahrheit: Contract Net selbst (Phase 1)
braucht **überhaupt keine Agent-zu-Agent-Kommunikation** - jeder Agent bietet nur
gegenüber dem Manager. Fällt die Kommunikation für die Verhandlung komplett aus
(Reichweite = 0), liefert dieses System trotzdem eine vollständige, gültige,
sofort ausführbare Zuteilung (das reine Contract-Net-Ergebnis) - nur eben ohne
Verbesserung. Ein zentraler Solver, der zum Rechnen erst alle Information
einsammeln muss, liefert in diesem Fall **gar nichts**. Dezentralität kostet hier
Lösungsqualität, aber sie kauft dafür Ausfallsicherheit - kein Single Point of
Failure. Beides ist Teil der ehrlichen Bilanz, nicht nur die Kosten-Seite.

Damit ergibt sich eine Drei-Stufen-Hierarchie (mit $\text{ALG} \geq \text{LS} \geq
\text{OPT}$ per Konstruktion):

| Stufe | Informationsstand | Suchkraft |
|---|---|---|
| Contract Net ($\text{ALG}$) | Online - keine Zukunftskenntnis | Keine (keine Revision) |
| Task-Swap-Verhandlung ($\text{LS}$) | Offline - kennt die volle Zuteilung | Lokal - nur paarweise Tausche |
| CP-SAT ($\text{OPT}$) | Offline | Erschöpfend / global optimal |
        """
    )

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
PRESET_HELP = C.PRESET_HELP
preset_cols = st.columns(len(C.PRESETS))
for i, name in enumerate(C.PRESETS.keys()):
    with preset_cols[i]:
        st.button(name, use_container_width=True, on_click=apply_preset, args=(name,), help=PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    n_jobs = st.slider("Anzahl Aufträge", *bounds("n_jobs_slider"), key="n_jobs_slider")
    n_agents = st.slider("Anzahl Agenten (Kräne)", *bounds("n_agents_slider"), key="n_agents_slider")
    duration_variability = st.slider(
        "Streuung der Auftragsdauer", *bounds("duration_variability_slider"), key="duration_variability_slider",
        help="0 = alle Aufträge ähnlich lang. Höhere Werte lassen gelegentlich einen ungewöhnlich langen "
        "Auftrag entstehen.",
    )
    travel_time_per_unit = st.slider(
        "Anfahrtszeit pro Positionseinheit", *bounds("travel_time_per_unit_slider"),
        key="travel_time_per_unit_slider",
        help="Wie teuer es einen Agenten kostet, zu einem entfernten Auftrag zu fahren.",
    )
    seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)

    st.button(
        "🎲 Neue Instanz generieren",
        use_container_width=True,
        on_click=randomize_seed,
        help="Würfelt einen neuen Zufalls-Seed für Auftragspositionen und -dauern.",
    )

    st.markdown("---")
    st.caption("📡 Verhandlungsparameter (wirkt nur auf Phase 2, nicht auf die Instanz selbst)")
    communication_range = st.slider(
        "Kommunikationsreichweite", *bounds("communication_range_slider"), key="communication_range_slider",
        help="Wie weit zwei Agenten physisch voneinander entfernt sein dürfen, um überhaupt einen Tausch "
        "zu verhandeln. Maximalwert = uneingeschränkte Kommunikation (kein Agentenpaar wird ausgeschlossen).",
    )

sync_query_params(n_jobs, n_agents, duration_variability, travel_time_per_unit, seed, communication_range)

scenario_key = (int(n_jobs), int(n_agents), duration_variability, travel_time_per_unit, int(seed))

with st.spinner("Führe Contract Net Protocol aus..."):
    instance, result = _compute_protocol(*scenario_key)

# --- Phase 1: Contract Net Rekapitulation -----------------------------------

st.markdown("## 🎯 Phase 1: Contract Net Protocol (online, unumkehrbar)")

if "cn_step" not in st.session_state or st.session_state.get("cn_step_owner") != scenario_key:
    st.session_state["cn_step"] = instance.n_jobs - 1
    st.session_state["cn_step_owner"] = scenario_key

max_step = instance.n_jobs - 1
step_col, play_col = st.columns([5, 1])
with step_col:
    if max_step == 0:
        step = 0
        st.caption("Nur ein Auftrag - kein Regler nötig.")
    else:
        step = st.slider(
            "Schritt (Auftragsvergabe)", 0, max_step, key="cn_step",
            help="Ein Schritt = eine angekündigte und vergebene Auftrags-Runde, in Ankunftsreihenfolge.",
        )
with play_col:
    auto_play_cnp = st.button("▶️ Abspielen", use_container_width=True, key="cnp_play")

with st.spinner("Verhandle Task-Swaps..."):
    negotiation = _compute_negotiation(*scenario_key, communication_range)
cmp = _compute_comparison(*scenario_key, communication_range)
ortools_makespan = cmp["ortools_makespan"] if cmp["ortools_feasible"] else None

chart_col, bid_col = st.columns([3, 2])
schedule_slot = chart_col.empty()
bid_slot = bid_col.empty()


def _render_cnp(current_step):
    schedule_slot.plotly_chart(
        build_schedule_figure(instance, result, current_step, ortools_makespan),
        use_container_width=True, key=f"cnp_schedule_{current_step}",
    )
    bid_slot.plotly_chart(
        build_bid_chart(result.steps[current_step]),
        use_container_width=True, key=f"cnp_bids_{current_step}",
    )


if auto_play_cnp:
    for s in range(0, max_step + 1):
        _render_cnp(s)
        time.sleep(0.4)
    step = max_step
else:
    _render_cnp(step)

live = stats_up_to_step(result, step)
lm1, lm2 = st.columns(2)
lm1.metric("Aufträge bisher vergeben", f"{live['jobs_awarded']} / {instance.n_jobs}")
lm2.metric(
    "Aktuell schlechteste freie Zeit", f"{live['worst_agent_free_time']:.1f} min",
    help="Die späteste Fertigstellungszeit über alle Agenten, nach den bisher gezeigten Schritten.",
)

st.markdown("---")

# --- Phase 2: Task-Swap-Verhandlung -----------------------------------------

st.markdown("## 🤝 Phase 2: Task-Swap-Verhandlung (offline, lokale Suche)")

negotiation_key = scenario_key + (communication_range,)
if "neg_step" not in st.session_state or st.session_state.get("neg_step_owner") != negotiation_key:
    st.session_state["neg_step"] = 0
    st.session_state["neg_step_owner"] = negotiation_key

n_swaps = len(negotiation.swaps)
if n_swaps == 0:
    st.info(
        "Diese Zuteilung ist bereits swap-optimal - es gibt keinen wechselseitigen "
        "Tausch zweier Aufträge, der den Makespan senken würde."
    )
    neg_step = 0
else:
    neg_step_col, neg_play_col = st.columns([5, 1])
    with neg_step_col:
        neg_step = st.slider(
            "Runde (Verhandlung)", 0, n_swaps, key="neg_step",
            help="0 = Zustand direkt nach Contract Net, vor jeder Verhandlung. "
            "Jede weitere Stufe zeigt einen akzeptierten Tausch.",
        )
    with neg_play_col:
        auto_play_neg = st.button("▶️ Abspielen", use_container_width=True, key="neg_play")

    neg_chart_slot = st.empty()
    neg_caption_slot = st.empty()

    def _schedules_and_highlight(s):
        if s == 0:
            return result.schedules, frozenset()
        swap = negotiation.swaps[s - 1]
        return swap.schedules_after, frozenset({swap.job_from_a, swap.job_from_b})

    def _render_negotiation(s):
        schedules, highlight = _schedules_and_highlight(s)
        neg_chart_slot.plotly_chart(
            build_negotiation_schedule_figure(instance, schedules, ortools_makespan, highlight),
            use_container_width=True, key=f"neg_schedule_{s}",
        )
        if s == 0:
            neg_caption_slot.caption(f"Ausgangslage nach Contract Net - Makespan: {result.makespan:.1f} min.")
        else:
            makespan_before = result.makespan if s == 1 else negotiation.swaps[s - 2].makespan_after
            neg_caption_slot.caption(f"Runde {s}: " + describe_swap(negotiation.swaps[s - 1], makespan_before))

    if auto_play_neg:
        for s in range(0, n_swaps + 1):
            _render_negotiation(s)
            time.sleep(0.6)
        neg_step = n_swaps
    else:
        _render_negotiation(neg_step)

nm1, nm2, nm3 = st.columns(3)
nm1.metric("Verhandlungsrunden", f"{n_swaps}")
nm2.metric(
    "Lokales Optimum erreicht?", "Ja" if negotiation.reached_local_optimum else "Nein (Sicherheitslimit)",
)
nm3.metric("Makespan nach Verhandlung", f"{negotiation.final_makespan:.1f} min")

st.markdown("---")

# --- Vergleich ---------------------------------------------------------------

st.subheader("📐 Wie viel schließt die Nachverhandlung von der Lücke?")
st.markdown(
    """
Vier Stufen für Ihre aktuelle Instanz: die rohe **Contract-Net**-Zuteilung, die
Verhandlung bei der **eingestellten Kommunikationsreichweite**, dieselbe
Verhandlung als Diagnose mit **uneingeschränkter** Kommunikation (identischer
Algorithmus, nur ohne das Distanz-Limit), und das zentrale **CP-SAT**-Optimum.
"""
)

vc1, vc2, vc3, vc4 = st.columns(4)
vc1.metric(
    "Contract Net (roh)", f"{cmp['cnp_makespan']:.1f} min",
    help="= Ergebnis bei Kommunikationsreichweite 0 (Verhandlung unmöglich) - siehe Robustheits-Hinweis unten.",
)

delta_constrained = cmp["constrained_makespan"] - cmp["cnp_makespan"]
if abs(delta_constrained) < 1e-6:
    vc2.metric(
        f"+ Verhandlung (Reichweite {communication_range:.1f})", f"{cmp['constrained_makespan']:.1f} min",
        delta="±0.0 min ggü. Contract Net roh - kein Tausch gefunden", delta_color="off",
    )
else:
    vc2.metric(
        f"+ Verhandlung (Reichweite {communication_range:.1f})", f"{cmp['constrained_makespan']:.1f} min",
        delta=f"{delta_constrained:+.1f} min ggü. Contract Net roh", delta_color="inverse",
    )

delta_unconstrained = cmp["unconstrained_makespan"] - cmp["constrained_makespan"]
vc3.metric(
    "+ Verhandlung (⚡ unbeschränkt, Diagnose)", f"{cmp['unconstrained_makespan']:.1f} min",
    delta=f"{delta_unconstrained:+.1f} min ggü. echter Reichweite" if abs(delta_unconstrained) >= 1e-6 else "±0.0 min",
    delta_color="inverse" if abs(delta_unconstrained) >= 1e-6 else "off",
    help="Diagnose-Lauf: gleicher Algorithmus, gleiche Nachbarschaft, aber jedes Agentenpaar dürfte "
    "verhandeln - zeigt, was ohne die Kommunikationsreichweite möglich wäre.",
)

if cmp["ortools_feasible"]:
    delta_ortools = cmp["ortools_makespan"] - cmp["unconstrained_makespan"]
    vc4.metric(
        "Zentrale Optimierung (CP-SAT)", f"{cmp['ortools_makespan']:.1f} min",
        delta=f"{delta_ortools:+.1f} min ggü. Verhandlung (unbeschränkt)", delta_color="inverse",
        help=f"Echter industrieller Solver, {cmp['ortools_wall_time']:.2f}s - "
        + ("beweist Optimalität." if cmp["ortools_optimal"] else "Zeitlimit erreicht, beste gefundene Lösung."),
    )
else:
    vc4.metric("Zentrale Optimierung (CP-SAT)", "kein Ergebnis im Zeitlimit")

if cmp["gap_pct_raw"] is not None:
    st.caption(
        f"Lücke zu CP-SAT: **{cmp['gap_pct_raw']:.1f}%** (roh) → **{cmp['gap_pct_constrained']:.1f}%** "
        f"(Reichweite {communication_range:.1f}) → **{cmp['gap_pct_unconstrained']:.1f}%** (unbeschränkt)."
        + (f" Geschlossen bei aktueller Reichweite: **{cmp['gap_closed_pct_constrained']:.0f}%** der "
           f"ursprünglichen Lücke."
           if cmp["gap_closed_pct_constrained"] is not None else "")
    )

    # Reihenfolge ist wichtig: eine grosse VERBLEIBENDE Lücke ist die eigentliche
    # "eigene Schwäche"-Aussage dieses Stücks - das gilt auch dann, wenn die
    # Verhandlung schon einen großen ANTEIL der ursprünglichen Lücke geschlossen hat
    # (56% geschlossen bei 24.6% verbleibender Lücke ist immnoch kein Erfolg).
    if (
        negotiation.reached_local_optimum
        and cmp["gap_pct_constrained"] >= C.GAP_REMAINING_WARNING_THRESHOLD_PCT
    ):
        st.warning(
            f"⚠️ Die Verhandlung erreicht ein **lokales Optimum** (kein wechselseitiger Tausch hilft mehr), "
            f"aber es bleibt eine spürbare Lücke von **{cmp['gap_pct_constrained']:.1f}%** zum zentralen "
            f"Optimum. Paarweise Tausche allein reichen hier nicht aus - genau das motiviert die übrigen "
            f"Stücke dieser Linie (Kombinatorische Auktionen, Distributed Constraint Optimization, "
            f"Multi-Agent Reinforcement Learning), die diese Grenze über andere Mechanismen überwinden."
        )
    elif cmp["gap_closed_pct_constrained"] is not None and cmp["gap_closed_pct_constrained"] >= C.GAP_CLOSED_HIGHLIGHT_THRESHOLD_PCT:
        st.success(
            f"✅ Die Task-Swap-Verhandlung schließt **{cmp['gap_closed_pct_constrained']:.0f}%** der "
            f"ursprünglichen Lücke zum zentralen Optimum - ein deutlicher Gewinn, ganz ohne zentrale Kontrolle."
        )
    elif cmp["constrained_swap_count"] == 0:
        st.info(
            "Kein wechselseitiger Tausch verbessert diese Zuteilung - das Contract Net Protocol war hier "
            "bereits (zufällig) swap-optimal, obwohl eine reale Lücke zum zentralen Optimum bleibt."
        )
    else:
        st.info("Bei dieser Instanz ist die verbleibende Lücke bereits klein.")

comm_cost = cmp["decentralization_cost_min"]
if comm_cost > 0.05:
    blocked_desc = ", ".join(
        f"Agent {a + 1} und Agent {b + 1} (Distanz {d:.1f})" for a, b, d in cmp["blocked_pairs"][:3]
    )
    st.warning(
        f"📡 **Preis der Dezentralität**: bei Kommunikationsreichweite **{communication_range:.1f}** "
        f"erreicht die Verhandlung {cmp['constrained_makespan']:.1f} min. Mit uneingeschränkter "
        f"Kommunikation (identischer Algorithmus, nur ohne das Distanz-Limit) wären es "
        f"{cmp['unconstrained_makespan']:.1f} min - das kostet **{comm_cost:.1f} min**"
        + (f" (**{cmp['decentralization_cost_pct']:.1f}%**)" if cmp["decentralization_cost_pct"] is not None else "")
        + f", weil {blocked_desc} zu weit auseinander liegen, um zu verhandeln."
    )
else:
    st.caption(
        "📡 Bei der aktuellen Kommunikationsreichweite blockiert keine Distanz einen verbessernden "
        "Tausch - Ergebnis identisch zu uneingeschränkter Kommunikation."
    )

st.info(
    f"🛡️ **Robustheit statt Ausfall**: selbst bei vollständigem Kommunikationsausfall "
    f"(Reichweite = 0) liefert dieses System **{cmp['worst_case_makespan']:.1f} min** - eine "
    f"vollständige, gültige, sofort ausführbare Zuteilung (exakt das Contract-Net-Ergebnis, nur ohne "
    f"Verbesserung). Contract Net selbst braucht in Phase 1 gar keine Agent-zu-Agent-Kommunikation. Ein "
    f"zentraler Solver, der zum Rechnen erst alle Information einsammeln muss, liefert bei einem "
    f"Kommunikationsausfall **gar nichts** - kein Single Point of Failure ist der eigentliche Vorteil "
    f"der Dezentralität, nicht (nur) ihre Lösungsqualität."
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Tausch-Akzeptanzkriterium**: für ein Agentenpaar $(a, b)$ und je einen Auftrag
$i$ von $a$, $j$ von $b$, sei $\Delta(i, j)$ die Änderung des Makespan, wenn $i$ zu
$b$ und $j$ zu $a$ wandert (Reihenfolge sonst unverändert, aufsteigend nach Index).
Ein Tausch wird akzeptiert, wenn

$$
\Delta(i, j) = \text{makespan}(\text{Kandidat}) - \text{makespan}(\text{aktuell}) < -\varepsilon
$$

Pro Runde wird der Tausch mit dem **kleinsten** $\Delta$ über alle Agenten- und
Auftragspaare gewählt (steilster Abstieg). Terminiert, wenn eine vollständige
Abtastung keinen $\Delta < -\varepsilon$ mehr findet - das **lokale Optimum**.

**Kommunikations-Gate, formal**: ein Agentenpaar $(a, b)$ wird überhaupt nur
betrachtet, wenn

$$
|\text{pos}_{\text{final}}(a) - \text{pos}_{\text{final}}(b)| \leq \text{communication\_range}
$$

gilt - unter Verwendung der ROHEN physischen Distanz, nicht der (durch
`travel_time_per_unit` skalierten) Anfahrtszeit. Das trennt zwei unabhängige
Größen: wie teuer eine Fahrt ist, und wie weit ein Agent überhaupt kommunizieren
kann.

**Online/Offline/Lokal, formal**: Contract Net liefert $\text{ALG}$, ein
Online-Ergebnis ohne Zukunftskenntnis. Die Verhandlung liefert $\text{LS}$
("local search") - **offline** (kennt die volle Zuteilung), aber nur über ein
eingeschränktes Nachbarschaftsmodell (paarweise, wechselseitige Tausche, zusätzlich
durch die Kommunikationsreichweite begrenzt) gesucht, nicht erschöpfend. CP-SAT
liefert $\text{OPT}$, das globale Offline-Optimum. Damit ergibt sich die
geschärfte Kette

$$
\text{ALG} = \text{LS}(0) \;\geq\; \text{LS}(\text{range}) \;\geq\; \text{LS}(\infty) \;\geq\; \text{OPT}
$$

Die ERSTE Ungleichung ($\text{LS}(0) = \text{ALG}$) und die dazwischen sind
**beweisbar**: steilster Abstieg akzeptiert nur echte Verbesserungen, und bei
`communication_range=0` existiert kein zulässiges Agentenpaar, also bleibt das
Ergebnis exakt $\text{ALG}$. Die Ungleichung $\text{LS}(\text{range}) \geq
\text{LS}(\infty)$ ist dagegen **nicht** beweisbar - Lokalsuche ist pfadabhängig,
eine engere Nachbarschaft kann in seltenen Fällen einen zufällig besseren Pfad
nehmen; das wird als ehrlicher Fakt behandelt, nicht als erzwungene Testinvariante.
Die **kompetitive Analyse** (Sleator & Tarjan, 1985), die schon den
Contract-Net-vs-CP-SAT-Vergleich in contract-net-demo einordnet, gilt hier
zweifach: $\text{LS}/\text{OPT}$ ist der kompetitive Faktor einer LOKALEN Suche -
eine grundsätzlich andere Größe als $\text{ALG}/\text{OPT}$, da $\text{LS}$ mit
voller Information arbeitet und trotzdem suboptimal bleiben kann, nicht wegen
fehlender Zukunftskenntnis, sondern wegen der eingeschränkten Nachbarschaft.

Implementiert in `cn_negotiation.py` (`negotiate`, das Tauschverfahren inkl.
Kommunikations-Gate), `cn_schedule.py` (`schedule_from_assignment`, die
gemeinsame Neuberechnung) und `cn_negotiation_evaluation.py`
(`tier_comparison`, der Vierweg-Vergleich).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
