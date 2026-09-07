"""Gantt-Chart für einen beliebigen Zuteilungszustand (nicht CNP-Schritt-
spezifisch wie `cn_visualization._job_intervals`) - für die Task-Swap-
Verhandlung, die auf der fertigen CNP-Zuteilung weiterarbeitet. Hebt die
beiden gerade getauschten Aufträge optisch hervor."""

import plotly.graph_objects as go

from cn_visualization import AGENT_COLORS


def _negotiation_intervals(instance, schedules):
    intervals = {a: [] for a in range(instance.n_agents)}
    for agent_id in range(instance.n_agents):
        position = instance.agent_start_positions[agent_id]
        free_time = 0.0
        for job_index in schedules.get(agent_id, ()):
            job = instance.jobs[job_index]
            travel = instance.travel_time(position, job.position)
            start = free_time + travel
            end = start + job.duration
            intervals[agent_id].append((job_index, start, end))
            free_time = end
            position = job.position
    return intervals


def build_negotiation_schedule_figure(instance, schedules, ortools_makespan=None, highlight_jobs=frozenset()):
    intervals = _negotiation_intervals(instance, schedules)
    fig = go.Figure()

    for agent_id in range(instance.n_agents):
        color = AGENT_COLORS[agent_id % len(AGENT_COLORS)]
        for job_index, start, end in intervals[agent_id]:
            is_highlighted = job_index in highlight_jobs
            fig.add_trace(
                go.Bar(
                    x=[end - start], y=[f"Agent {agent_id + 1}"], base=start, orientation="h",
                    marker=dict(
                        color=color,
                        line=dict(color="black", width=3 if is_highlighted else 0),
                    ),
                    showlegend=False, hovertext=f"Auftrag {job_index + 1}", hoverinfo="text",
                    text=f"A{job_index + 1}", textposition="inside",
                )
            )

    if ortools_makespan is not None:
        fig.add_vline(
            x=ortools_makespan, line_dash="dash", line_color="gray",
            annotation_text="Zentrales Optimum", annotation_position="top",
        )

    fig.update_layout(
        barmode="overlay",
        xaxis_title="Zeit (min)",
        yaxis_title=None,
        height=120 + 60 * instance.n_agents,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=[f"Agent {a + 1}" for a in range(instance.n_agents)],
        autorange="reversed",
    )
    return fig


def describe_swap(swap, makespan_before):
    return (
        f"Agent {swap.agent_a + 1} gibt Auftrag {swap.job_from_a + 1} an "
        f"Agent {swap.agent_b + 1} ab, erhält im Gegenzug Auftrag "
        f"{swap.job_from_b + 1} - Makespan: {makespan_before:.1f} → {swap.makespan_after:.1f} min"
    )
