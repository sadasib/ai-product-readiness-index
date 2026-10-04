from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.assessment_history import (
    create_assessment_record,
    get_assessment_by_id,
    save_assessment,
)
from utils.export_pdf import create_pdf
from utils.recommendations import build_recommendation_payload
from utils.report_builder import (
    build_executive_summary,
    build_report_payload,
    get_readiness_grade,
)
from utils.scoring import calculate_assessment


def render_decision_banner(
    overall_score: float,
    overall_max: float,
    overall_pct: float,
    recommendation: str,
    confidence: str,
) -> None:
    """Render the top executive decision section."""
    score_text = (
        f"{round(overall_score):.0f} / "
        f"{round(overall_max):.0f}"
    )

    grade = get_readiness_grade(
        overall_pct
    )

    if recommendation == "Ready for Production":
        st.success(
            "✅ READY FOR PRODUCTION\n\n"
            "Proceed with production rollout."
        )

    elif recommendation == "Ready for Beta":
        st.warning(
            "🟡 READY FOR BETA\n\n"
            "Proceed with a controlled Beta rollout."
        )

    elif recommendation == "Additional Review Required":
        st.warning(
            "🟠 ADDITIONAL REVIEW REQUIRED\n\n"
            "Resolve the open issues before broad launch."
        )

    else:
        st.error(
            "🔴 NOT READY\n\n"
            "Address critical blockers before launch."
        )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Readiness Index",
        score_text,
    )

    c2.metric(
        "Overall Readiness",
        f"{overall_pct:.0f}%",
    )

    c3.metric(
        "Confidence",
        confidence,
    )

    c4.metric(
        "Grade",
        grade,
    )


def render_summary_card(
    summary_text: str,
) -> None:
    """Render the executive summary."""
    st.markdown(
        "### Executive Summary"
    )

    with st.container(
        border=True
    ):
        st.write(
            summary_text
        )


def get_gate_emoji(
    gate_title: str,
) -> str:
    """Return a simple emoji for each gate."""
    mapping = {
        "Customer Value": "🎯",
        "AI Quality": "🤖",
        "Trust & Safety": "🛡",
        "Operational Readiness": "⚙",
        "Business Readiness": "📈",
    }

    return mapping.get(
        gate_title,
        "•",
    )


def get_gate_status_meta(
    percentage: float,
) -> Dict[str, str]:
    """Return visual status metadata for a gate."""
    if percentage >= 90:
        return {
            "label": "HEALTHY",
            "emoji": "🟢",
            "accent": "#166534",
            "bg": "#f0fdf4",
            "border": "#bbf7d0",
        }

    if percentage >= 75:
        return {
            "label": "GOOD",
            "emoji": "🟡",
            "accent": "#92400e",
            "bg": "#fffbeb",
            "border": "#fcd34d",
        }

    if percentage >= 60:
        return {
            "label": "NEEDS ATTENTION",
            "emoji": "🟠",
            "accent": "#c2410c",
            "bg": "#fff7ed",
            "border": "#fdba74",
        }

    return {
        "label": "CRITICAL",
        "emoji": "🔴",
        "accent": "#b91c1c",
        "bg": "#fef2f2",
        "border": "#fca5a5",
    }


def build_bar(
    percentage: float,
    width: int = 12,
) -> str:
    """Create a simple text progress bar."""
    filled = max(
        0,
        min(
            width,
            int(
                round(
                    (percentage / 100) * width
                )
            ),
        ),
    )

    return (
        "█" * filled
        + "░" * (width - filled)
    )


def render_gate_health_cards(
    gate_results: List[Dict[str, Any]],
) -> None:
    """Render a card-based gate health section."""
    st.markdown(
        "### Launch Gate Health"
    )

    st.caption(
        "A quick view of how each launch "
        "gate is performing."
    )

    if not gate_results:
        st.info(
            "No gate results available yet."
        )
        return

    cols = st.columns(
        len(gate_results)
    )

    for idx, gate in enumerate(
        gate_results
    ):
        pct = float(
            gate.get(
                "percentage",
                0.0,
            )
        )

        gate_title = str(
            gate.get(
                "gate_title",
                "Gate",
            )
        )

        status_meta = get_gate_status_meta(
            pct
        )

        score = float(
            gate.get(
                "score",
                0.0,
            )
        )

        max_score = float(
            gate.get(
                "max_score",
                20.0,
            )
        )

        issue_count = len(
            gate.get(
                "failed_questions",
                [],
            )
        )

        with cols[idx]:
            st.markdown(
                f"### "
                f"{get_gate_emoji(gate_title)} "
                f"{gate_title}"
            )

            st.metric(
                "Status",
                status_meta["label"],
            )

            st.metric(
                "Readiness",
                f"{pct:.0f}%",
            )

            st.progress(
                min(
                    pct / 100,
                    1.0,
                )
            )

            st.caption(
                f"{score:.1f}/"
                f"{max_score:.0f}"
                f" · Issues: "
                f"{issue_count}"
            )


def render_action_center(
    blockers: List[Dict[str, Any]],
    next_actions: List[str],
) -> None:
    """Render a compact executive action center."""
    st.markdown(
        "### Action Center"
    )

    st.caption(
        "The highest-priority items "
        "to resolve before launch."
    )

    left, right = st.columns(2)

    with left:
        st.markdown(
            "#### Critical"
        )

        if blockers:
            for blocker in blockers:
                gate_title = blocker.get(
                    "gate_title",
                    "Gate",
                )

                prompt = blocker.get(
                    "prompt",
                    "",
                )

                st.error(
                    f"**HIGH** — "
                    f"{gate_title}: "
                    f"{prompt}"
                )

        else:
            st.success(
                "No critical launch "
                "blockers detected."
            )

    with right:
        st.markdown(
            "#### Immediate"
        )

        if next_actions:
            for action in next_actions:
                st.warning(
                    f"**MEDIUM** — "
                    f"{action}"
                )

        else:
            st.write(
                "No immediate actions required."
            )


def render_advanced_details(
    gate_results: List[Dict[str, Any]],
) -> None:
    """Render detailed assessment information."""
    st.markdown(
        "### Advanced Details"
    )

    with st.expander(
        "View detailed gate assessment",
        expanded=False,
    ):
        if not gate_results:
            st.info(
                "No gate results available yet."
            )
            return

        results_df = pd.DataFrame(
            [
                {
                    "Gate": gate.get(
                        "gate_title",
                        "",
                    ),
                    "Score": (
                        f"{float(gate.get('score', 0.0)):.1f}/"
                        f"{float(gate.get('max_score', 20.0)):.0f}"
                    ),
                    "Percentage": (
                        f"{float(gate.get('percentage', 0.0)):.1f}%"
                    ),
                    "Status": (
                        get_gate_status_meta(
                            float(
                                gate.get(
                                    "percentage",
                                    0.0,
                                )
                            )
                        )["label"].title()
                    ),
                }
                for gate in gate_results
            ]
        )

        st.dataframe(
            results_df,
            use_container_width=True,
            hide_index=True,
        )

        chart_df = pd.DataFrame(
            {
                "Gate": [
                    g.get(
                        "gate_title",
                        "",
                    )
                    for g in gate_results
                ],
                "Score %": [
                    float(
                        g.get(
                            "percentage",
                            0.0,
                        )
                    )
                    for g in gate_results
                ],
            }
        )

        fig = px.bar(
            chart_df,
            x="Gate",
            y="Score %",
            text="Score %",
            range_y=[0, 100],
        )

        fig.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside",
        )

        fig.update_layout(
            yaxis_title="Score %",
            xaxis_title="",
            showlegend=False,
            margin=dict(
                l=10,
                r=10,
                t=30,
                b=10,
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

        st.markdown(
            "#### Gate-level issues"
        )

        for gate in gate_results:
            gate_title = gate.get(
                "gate_title",
                "Gate",
            )

            failed_questions = gate.get(
                "failed_questions",
                [],
            )

            with st.expander(
                f"{gate_title} — "
                f"{float(gate.get('score', 0.0)):.1f}/"
                f"{float(gate.get('max_score', 20.0)):.0f}"
            ):
                if failed_questions:
                    for failed in failed_questions:
                        label = failed.get(
                            "prompt",
                            "",
                        )

                        answer = failed.get(
                            "answer",
                            "no answer",
                        )

                        points = failed.get(
                            "points",
                            0,
                        )

                        critical = (
                            "Critical"
                            if failed.get(
                                "critical",
                                False,
                            )
                            else "Non-critical"
                        )

                        st.write(
                            f"• {label} — "
                            f"Answer: "
                            f"{str(answer).title()} — "
                            f"{points} points — "
                            f"{critical}"
                        )

                else:
                    st.write(
                        "All questions in "
                        "this gate passed."
                    )


def render_results(
    questions_data: Dict[str, Any],
    scoring_rules: Dict[str, Any],
    history_container: Any,
    render_history_section_fn: Any,
) -> None:
    """Render the final readiness report."""
    st.title(
        "AI Product Readiness Index"
    )

    st.subheader(
        "Launch Readiness Report"
    )

    answers = st.session_state.get(
        "answers",
        {},
    )

    assessment = calculate_assessment(
        questions_data,
        scoring_rules,
        answers,
    )

    recommendation_payload = (
        build_recommendation_payload(
            assessment
        )
    )

    overall_score = float(
        assessment.get(
            "overall_score",
            0.0,
        )
    )

    overall_max = float(
        assessment.get(
            "overall_max_score",
            100.0,
        )
    )

    overall_pct = float(
        assessment.get(
            "overall_percentage",
            0.0,
        )
    )

    recommendation = (
        recommendation_payload.get(
            "recommendation",
            "Not Ready",
        )
    )

    confidence = (
        recommendation_payload.get(
            "confidence",
            "Low",
        )
    )

    next_actions = (
        recommendation_payload.get(
            "next_actions",
            [],
        )
    )

    product_context = st.session_state.get(
        "product_context",
        {},
    )

    product_name = (
        str(
            product_context.get(
                "product_name",
                "",
            )
        ).strip()
        or "AI Product Assessment"
    )

    report_payload = build_report_payload(
        assessment_result=assessment,
        recommendation_payload=recommendation_payload,
        product_name=product_name,
        product_context=product_context,
        version="1.1",
    )

    pdf_bytes = create_pdf(
        **report_payload
    )

    st.session_state[
        "report_payload"
    ] = report_payload

    st.session_state[
        "report_pdf"
    ] = pdf_bytes

    render_decision_banner(
        overall_score=overall_score,
        overall_max=overall_max,
        overall_pct=overall_pct,
        recommendation=recommendation,
        confidence=confidence,
    )

    st.caption(
        f"Product: **{product_name}**"
    )

    if product_context:
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

    gate_results = assessment.get(
        "gate_results",
        [],
    )

    blockers = assessment.get(
        "launch_blockers",
        [],
    )

    summary_text = build_executive_summary(
        recommendation,
        blockers,
        next_actions,
    )

    st.divider()

    render_summary_card(
        report_payload["executive_summary"]
        or summary_text
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

    render_advanced_details(
        gate_results
    )

    st.divider()

    st.markdown(
        "### Share the Launch Review"
    )

    st.caption(
        "Save the assessment for this session "
        "or export it as an executive-ready PDF."
    )

    save_col, export_col = st.columns(2)

    with save_col:
        if st.button(
            "Save Assessment",
            use_container_width=True,
        ):
            existing_history = (
                st.session_state.get(
                    "assessment_history",
                    [],
                )
            )

            current_assessment_id = (
                st.session_state.get(
                    "current_assessment_id"
                )
            )

            if current_assessment_id is None:
                current_assessment_id = (
                    f"assessment_"
                    f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                )

                st.session_state[
                    "current_assessment_id"
                ] = current_assessment_id

            existing_record = get_assessment_by_id(
                existing_history,
                current_assessment_id,
            )

            if existing_record is not None:
                st.info(
                    "This assessment is already saved."
                )

            else:
                record = create_assessment_record(
                    answers=answers,
                    assessment_result=assessment,
                    recommendation_payload=recommendation_payload,
                    report_payload=report_payload,
                    product_context=product_context,
                    product_name=product_name,
                    version="1.1",
                    assessment_id=current_assessment_id,
                )

                updated_history = save_assessment(
                    history=existing_history,
                    assessment_record=record,
                )

                st.session_state[
                    "assessment_history"
                ] = updated_history

                render_history_section_fn(
                    history_container=history_container,
                    history=updated_history,
                    selected_history_id=st.session_state.get(
                        "selected_history_id"
                    ),
                )

                st.success(
                    "Assessment saved."
                )

    with export_col:
        st.download_button(
            label="Export Executive Report",
            data=st.session_state[
                "report_pdf"
            ],
            file_name=(
                f"{product_name.replace(' ', '_')}"
                "_AI_Product_Readiness_Report.pdf"
            ),
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

    st.divider()

    st.markdown(
        "### What this means"
    )

    st.write(
        "This result should support a launch "
        "decision discussion. It does not "
        "replace product judgment; it makes "
        "readiness explicit and easier to "
        "review with engineering, operations, "
        "and risk partners."
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "Back to Review",
            use_container_width=True,
        ):
            st.session_state[
                "current_step"
            ] = len(
                questions_data.get(
                    "gates",
                    [],
                )
            ) + 1

            st.rerun()

    with c2:
        if st.button(
            "Restart Review",
            type="primary",
            use_container_width=True,
        ):
            st.session_state[
                "answers"
            ] = {}

            st.session_state[
                "current_step"
            ] = 0

            st.session_state[
                "current_assessment_id"
            ] = None

            st.session_state[
                "selected_history_id"
            ] = None

            st.session_state[
                "product_context"
            ] = {}

            st.session_state.pop(
                "report_payload",
                None,
            )

            st.session_state.pop(
                "report_pdf",
                None,
            )

            st.rerun()