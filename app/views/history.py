from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

from views.results import (
    build_executive_summary,
    get_readiness_grade,
    render_action_center,
    render_decision_banner,
    render_gate_health_cards,
    render_summary_card,
)


def render_history_section(
    history_container: Any,
    history: List[Dict[str, Any]],
    selected_history_id: Any,
) -> None:
    """Render the assessment history list."""
    with history_container.container():
        st.markdown(
            "### Assessment History"
        )

        if not history:
            st.caption(
                "No saved assessments yet."
            )
            return

        for record in history[:5]:
            record_id = str(
                record.get(
                    "id",
                    "",
                )
            )

            product_name = str(
                record.get(
                    "product_name",
                    "AI Product Assessment",
                )
            ).strip()

            recommendation = str(
                record.get(
                    "recommendation",
                    "Not Ready",
                )
            )

            score = float(
                record.get(
                    "overall_score",
                    0.0,
                )
            )

            created_at = str(
                record.get(
                    "created_at",
                    "",
                )
            )

            display_date = (
                created_at[:10]
                if created_at
                else "Unknown date"
            )

            display_label = (
                f"{product_name} · "
                f"{recommendation} · "
                f"{score:.1f} · "
                f"{display_date}"
            )

            button_type = (
                "primary"
                if record_id == selected_history_id
                else "secondary"
            )

            if st.button(
                display_label,
                key=f"history_{record_id}",
                use_container_width=True,
                type=button_type,
            ):
                st.session_state[
                    "selected_history_id"
                ] = record_id

                st.rerun()


def render_historical_assessment(
    record: Dict[str, Any],
) -> None:
    """Render a saved assessment as a read-only snapshot."""
    st.title(
        "AI Product Readiness Index"
    )

    st.subheader(
        "Historical Launch Readiness Report"
    )

    product_context = record.get(
        "product_context",
        {},
    )

    product_name = str(
        product_context.get(
            "product_name",
            record.get(
                "product_name",
                "AI Product Assessment",
            ),
        )
    ).strip()

    created_at = str(
        record.get(
            "created_at",
            "",
        )
    )

    display_date = (
        created_at[:10]
        if created_at
        else "Unknown date"
    )

    st.caption(
        f"{product_name} · "
        f"Saved assessment · "
        f"{display_date}"
    )

    context_items = []

    product_type = str(
        product_context.get(
            "product_type",
            "",
        )
    ).strip()

    launch_stage = str(
        product_context.get(
            "launch_stage",
            "",
        )
    ).strip()

    owner = str(
        product_context.get(
            "assessment_owner",
            "",
        )
    ).strip()

    if product_type:
        context_items.append(
            f"Type: **{product_type}**"
        )

    if launch_stage:
        context_items.append(
            f"Launch stage: **{launch_stage}**"
        )

    if owner:
        context_items.append(
            f"Owner: **{owner}**"
        )

    if context_items:
        st.caption(
            " · ".join(context_items)
        )

    assessment_result = record.get(
        "assessment_result",
        {},
    )

    recommendation_payload = record.get(
        "recommendation_payload",
        {},
    )

    overall_score = float(
        record.get(
            "overall_score",
            assessment_result.get(
                "overall_score",
                0.0,
            ),
        )
    )

    overall_percentage = float(
        record.get(
            "overall_percentage",
            assessment_result.get(
                "overall_percentage",
                0.0,
            ),
        )
    )

    overall_max = float(
        assessment_result.get(
            "overall_max_score",
            100.0,
        )
    )

    recommendation = str(
        record.get(
            "recommendation",
            "Not Ready",
        )
    )

    confidence = str(
        record.get(
            "confidence",
            "Low",
        )
    )

    grade = str(
        record.get(
            "report_payload",
            {},
        ).get(
            "grade",
            get_readiness_grade(
                overall_percentage
            ),
        )
    )

    gate_results = assessment_result.get(
        "gate_results",
        [],
    )

    blockers = assessment_result.get(
        "launch_blockers",
        [],
    )

    next_actions = recommendation_payload.get(
        "next_actions",
        [],
    )

    render_decision_banner(
        overall_score=overall_score,
        overall_max=overall_max,
        overall_pct=overall_percentage,
        recommendation=recommendation,
        confidence=confidence,
    )

    st.caption(
        f"Readiness Grade: **{grade}**"
    )

    st.divider()

    summary_text = str(
        record.get(
            "report_payload",
            {},
        ).get(
            "executive_summary",
            build_executive_summary(
                recommendation,
                blockers,
                next_actions,
            ),
        )
    )

    render_summary_card(
        summary_text
    )

    st.divider()

    render_gate_health_cards(
        gate_results
    )

    st.divider()

    render_action_center(
        blockers,
        next_actions,
    )

    st.divider()

    st.info(
        "This is a read-only snapshot of the "
        "assessment at the time it was saved. "
        "It does not modify the current assessment."
    )

    if st.button(
        "Back to Current Assessment",
        use_container_width=True,
    ):
        st.session_state[
            "selected_history_id"
        ] = None

        st.rerun()