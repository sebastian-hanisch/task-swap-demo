# Task-Swap-Verhandlung nach dem Contract Net Protocol – Streamlit-Demo

Zweites Stück der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations
Research und Machine Learning", **Multi-Agenten-Koordinations-Linie** - direkte
Fortsetzung von [contract-net-demo](../contract-net-demo): das **Contract Net
Protocol** (Smith, 1980) vergibt Aufträge online und unwiderruflich; diese Demo
fügt eine **Task-Swap-Verhandlung** hinzu, die danach - mit vollständiger
Information, aber nur lokaler Suche - paarweise Tausche zwischen Agenten prüft.

## Warum dasselbe Vehikel wie contract-net-demo

Dieselbe bewusst vereinfachte Kran-zu-Container-Auftrag-Zuweisung (keine
gemeinsame Schiene, keine Non-Crossing-Regel) - `cn_scenario.py`, `cn_bidding.py`,
`cn_protocol.py` und `cn_ortools_reference.py` sind wortgleiche Kopien aus
contract-net-demo. Jede Demo im Portfolio ist eigenständig lauffähig (eigenes
venv, eigene Tests, eigenes Deployment), daher werden gemeinsame Bausteine
kopiert statt importiert - dieselbe Linie teilt sich das Vehikel über die Zeit,
nicht über gemeinsamen Code.

## Die drei Stufen

| Stufe | Informationsstand | Suchkraft | Symbol |
|---|---|---|---|
| Contract Net | Online - keine Zukunftskenntnis | Keine (keine Revision) | `ALG` |
| Task-Swap-Verhandlung | Offline - kennt die volle Zuteilung | Lokal - nur paarweise Tausche | `LS` |
| CP-SAT | Offline | Erschöpfend / global optimal | `OPT` |

Per Konstruktion gilt `ALG ≥ LS ≥ OPT`. Die Verhandlung (`cn_negotiation.py`)
prüft nach Abschluss des Contract Net Protocol wiederholt alle Agentenpaare und
Auftragspaare auf einen verbessernden, **wechselseitigen** Tausch (ein Auftrag
wandert je Richtung, keine einseitigen "Geschenke", keine Umsortierung innerhalb
eines Agenten) und akzeptiert pro Runde den besten gefundenen Tausch (steilster
Abstieg), bis keiner mehr verbessert (**lokales Optimum**).

## Die gelehrte (und ehrlich begrenzte) Verbesserung

Anders als contract-net-demo, wo die Lücke zu CP-SAT nur wächst, zeigt dieses
Stück eine **teilweise Korrektur**: die Verhandlung schließt oft einen
erheblichen Teil der Lücke, aber - weil paarweise Tausche nur eine eingeschränkte
Nachbarschaft absuchen - nicht immer die ganze. Ein Kalibrierungs-Sweep
(`calibrate_presets.py`, seither gelöscht) zeigte alle drei Fälle real: Instanzen,
die bereits swap-optimal sind (0 Tausche), Instanzen mit einem einzigen Tausch,
der den Großteil der Lücke schließt, und Instanzen, die trotz erreichtem lokalen
Optimum eine spürbare Lücke behalten - genau die Motivation für die übrigen,
noch nicht gebauten Stücke dieser Linie (Kombinatorische Auktionen, Distributed
Constraint Optimization, Multi-Agent Reinforcement Learning).

## Referenzlöser

- **`cn_ortools_reference.py`**: echter Google-OR-Tools-CP-SAT-Solver (`OPT`),
  wortgleich aus contract-net-demo übernommen.
- **`cn_bruteforce.py`**: vollständige Enumeration für Tests, nutzt jetzt
  `cn_schedule.schedule_from_assignment` (derselbe Baustein wie die Verhandlung
  selbst) statt einer eigenen Kopie der Akkumulationsformel.

## Verifikation

- **Nie schlechter als roh**: die Verhandlung kann den Makespan nie erhöhen.
- **Vollständigkeit & Reihenfolge**: jeder Auftrag bleibt genau einmal zugeteilt,
  jede Agenten-Warteschlange bleibt aufsteigend nach Auftrags-Index sortiert.
- **Lokales-Optimum-Verifikation**: wenn die Verhandlung terminiert, wird
  unabhängig erneut jedes Agenten-/Auftragspaar geprüft - keines darf noch
  verbessern.
- **Ein-Agenten-Grenzfall**: ohne zweiten Agenten ist kein Tausch möglich.
- **Optimalitätsschranke**: die Verhandlung schlägt nie das CP-SAT-Optimum (bis
  auf die dokumentierte Rundungstoleranz des skalierten CP-SAT-Modells).
- **Determinismus**: gleiche Instanz, zweimal verhandelt, liefert identische
  Tausch-Sequenz (deterministisches Tie-Breaking).
- **Preset-Kalibrierung**: `test_presets_produce_expected_gap_and_closure_bands`
  hält die gemessenen Lücken-/Schließungsbänder der vier Presets als Regression
  fest.

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Hauptablauf: Presets, Einstellungen, zwei Phasen-Animationen, Dreiweg-Vergleich |
| `cn_constants.py` | Defaults, Regler-Grenzen, `PRESETS`, Verhandlungs-Konstanten |
| `cn_presets.py` | `SettingSpec`/`SETTING_SPECS`, Permalink-Logik (unverändert aus contract-net-demo) |
| `cn_scenario.py` | Zufällige Kran-zu-Auftrag-Instanzen (unverändert aus contract-net-demo) |
| `cn_bidding.py` | Die Gebotsformel (unverändert aus contract-net-demo) |
| `cn_protocol.py` | Contract-Net-Vergabeschleife, Phase 1 (unverändert aus contract-net-demo) |
| `cn_schedule.py` | Gemeinsamer Baustein: Zuteilung → Fertigstellungszeiten/Makespan |
| `cn_negotiation.py` | Die Task-Swap-Verhandlung, Phase 2 - das neue Kernstück |
| `cn_ortools_reference.py` | Echter Google-OR-Tools-CP-SAT-Solver (zentrale Referenz) |
| `cn_bruteforce.py` | Unabhängige Referenzlösung für Tests |
| `cn_evaluation.py` | Contract-Net-Kennzahlen (Phase-1-Rekapitulation) |
| `cn_negotiation_evaluation.py` | Dreiweg-Vergleich (roh / verhandelt / CP-SAT) inkl. Lücken-Schließung |
| `cn_visualization.py` | Gantt-Chart + Gebots-Balkendiagramm für Phase 1 (unverändert aus contract-net-demo) |
| `cn_negotiation_visualization.py` | Gantt-Chart mit Tausch-Hervorhebung für Phase 2 |
| `tests/` | Bausteine-Invarianten, Verhandlungs-Invarianten (inkl. lokales-Optimum-Verifikation), Preset-Regression |

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

Teil des [Operations-Research-Demo-Portfolios](https://sebastianhanisch.net/demos.html) von
[Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning.
Interesse an einer maßgeschneiderten Lösung? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html).
