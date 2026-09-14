from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.assessment_history import (
    create_assessment_record,
    get_assessment_by_id,
    get_assessment_history,
    save_assessment,
)
from utils.helpers import (
    answer_label,
    build_progress,
    count_questions,
    format_score,
    load_json,
)
from utils.recommendations import build_recommendation_payload
from utils.report_builder import build_report_payload
from utils.export_pdf import create_pdf
from utils.scoring import calculate_assessment


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"

QUESTIONS_PATH = DATA_DIR / "questions.json"
SCORING_RULES_PATH = DATA_DIR / "scoring_rules.json"
SAMPLE_ASSESSMENT_PATH = DATA_DIR / "sample_assessment.json"


st.set_page_config(
    page_title="AI Product Readiness Index",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -------------------------------------------------------------------
# DATA LOADING
# -------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_inputs() -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Load app inputs from disk."""
    questions_data = load_json(QUESTIONS_PATH)
    scoring_rules = load_json(SCORING_RULES_PATH)
    sample_assessment = load_json(SAMPLE_ASSESSMENT_PATH)

    return (
        questions_data,
        scoring_rules,
        sample_assessment,
    )


# -------------------------------------------------------------------
# SESSION / NAVIGATION HELPERS
# -------------------------------------------------------------------

def get_gate_index(current_step: int) -> int:
    """Convert app step to gate list index."""
    return current_step - 1


def get_stage_label(
    current_step: int,
    gate_count: int,
) -> str:
    """Return a clean label for the current app stage."""
    if current_step == 0:
        return "Not started"

    if 1 <= current_step <= gate_count:
        return f"Gate {current_step}/{gate_count}"

    return "Final report"


def clear_answer_state(
    questions_data: Dict[str, Any],
) -> None:
    """Clear current assessment answers and widget state."""
    st.session_state["answers"] = {}

    for gate in questions_data.get("gates", []):
        for question in gate.get("questions", []):
            widget_key = f"answer_{question.get('id')}"

            if widget_key in st.session_state:
                del st.session_state[widget_key]


def start_new_assessment(
    questions_data: Dict[str, Any],
) -> None:
    """Reset current assessment state while preserving saved history."""
    clear_answer_state(questions_data)

    st.session_state["current_step"] = 1
    st.session_state["current_assessment_id"] = None
    st.session_state["selected_history_id"] = None

    st.session_state.pop(
        "report_payload",
        None,
    )

    st.session_state.pop(
        "report_pdf",
        None,
    )


def set_sample_answers(
    questions_data: Dict[str, Any],
    sample_assessment: Dict[str, Any],
) -> None:
    """Load sample answers into session state and widget state."""
    answers = sample_assessment.get(
        "answers",
        {},
    )

    st.session_state["answers"] = dict(answers)
    st.session_state["current_assessment_id"] = None
    st.session_state["selected_history_id"] = None

    for gate in questions_data.get("gates", []):
        for question in gate.get("questions", []):
            qid = question.get("id")
            widget_key = f"answer_{qid}"

            raw_answer = answer_label(
                answers.get(qid)
            )

            st.session_state[widget_key] = (
                raw_answer
                if raw_answer in {
                    "Yes",
                    "Partial",
                    "No",
                }
                else "Select an answer"
            )


def generate_assessment_id() -> str:
    """Generate a unique ID for the current assessment."""
    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S%f"
    )

    return f"assessment_{timestamp}"


# -------------------------------------------------------------------
# DISPLAY HELPERS
# -------------------------------------------------------------------

def get_readiness_grade(
    overall_pct: float,
) -> str:
    """Convert a percentage into a simple grade."""
    if overall_pct >= 95:
        return "A+"

    if overall_pct >= 90:
        return "A"

    if overall_pct >= 85:
        return "A-"

    if overall_pct >= 80:
        return "B+"

    if overall_pct >= 75:
        return "B"

    if overall_pct >= 70:
        return "C"

    return "Needs Review"


def get_decision_meta(
    recommendation: str,
) -> Dict[str, str]:
    """Return styling metadata for the launch decision."""
    mapping = {
        "Ready for Production": {
            "label": "READY FOR PRODUCTION",
            "emoji": "✅",
            "subtitle": "Proceed with production rollout.",
            "accent": "#166534",
            "bg": "#f0fdf4",
            "border": "#bbf7d0",
        },
        "Ready for Beta": {
            "label": "READY FOR BETA",
            "emoji": "🟡",
            "subtitle": "Proceed with a controlled Beta rollout.",
            "accent": "#92400e",
            "bg": "#fffbeb",
            "border": "#fcd34d",
        },
        "Additional Review Required": {
            "label": "ADDITIONAL REVIEW REQUIRED",
            "emoji": "🟠",
            "subtitle": "Resolve the open issues before broad launch.",
            "accent": "#c2410c",
            "bg": "#fff7ed",
            "border": "#fdba74",
        },
        "Not Ready": {
            "label": "NOT READY",
            "emoji": "🔴",
            "subtitle": "Address critical blockers before launch.",
            "accent": "#b91c1c",
            "bg": "#fef2f2",
            "border": "#fca5a5",
        },
    }

    return mapping.get(
        recommendation,
        {
            "label": recommendation.upper(),
            "emoji": "ℹ️",
            "subtitle": "Review the launch decision carefully.",
            "accent": "#1f2937",
            "bg": "#f8fafc",
            "border": "#cbd5e1",
        },
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
    """Return a visual status mapping for a gate."""
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


def build_executive_summary(
    recommendation: str,
    blockers: List[Dict[str, Any]],
    next_actions: List[str],
) -> str:
    """Create a concise executive summary sentence."""
    if recommendation == "Ready for Production":
        lead = (
            "The feature shows strong readiness "
            "and can move to production."
        )

    elif recommendation == "Ready for Beta":
        lead = (
            "The feature is ready for a "
            "controlled Beta launch."
        )

    elif recommendation == "Additional Review Required":
        lead = (
            "The feature is close, but still "
            "needs another review cycle before "
            "broader launch."
        )

    else:
        lead = (
            "The feature is not ready for "
            "launch yet."
        )

    blocker_clause = ""

    if blockers:
        first_blocker = blockers[0].get(
            "prompt",
            "a critical blocker",
        )

        blocker_clause = (
            f" One critical blocker remains: "
            f"{first_blocker}."
        )

    action_clause = ""

    if next_actions:
        action_clause = (
            f" Recommended next action: "
            f"{next_actions[0]}."
        )

    return (
        f"{lead}"
        f"{blocker_clause}"
        f"{action_clause}"
    )


# -------------------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------------------

def render_sidebar(
    questions_data: Dict[str, Any],
    current_step: int,
    total_steps: int,
) -> Any:
    """Render sidebar summary, progress and history."""
    total_questions, critical_questions = count_questions(
        questions_data
    )

    answered_count = len(
        st.session_state.get(
            "answers",
            {},
        )
    )

    progress_pct = build_progress(
        answered_count,
        total_questions,
    )

    gate_count = len(
        questions_data.get(
            "gates",
            [],
        )
    )

    stage_label = get_stage_label(
        current_step,
        gate_count,
    )

    history = get_assessment_history(
        st.session_state.get(
            "assessment_history",
            [],
        )
    )

    selected_history_id = st.session_state.get(
        "selected_history_id"
    )

    with st.sidebar:
        st.markdown(
            "## AI Product Readiness Index"
        )

        st.caption(
            "Powered by the AI Product Playbook"
        )

        st.progress(
            progress_pct / 100
            if progress_pct
            else 0.0
        )

        st.write(
            f"**Progress:** "
            f"{progress_pct:.0f}%"
        )

        st.write(
            f"**Answered:** "
            f"{answered_count}/{total_questions}"
        )

        st.write(
            f"**Critical questions:** "
            f"{critical_questions}"
        )

        st.write(
            f"**Stage:** {stage_label}"
        )

        if current_step == 0:
            st.write("**Step:** Start")

        elif 1 <= current_step <= gate_count:
            st.write(
                f"**Step:** "
                f"{current_step}/{gate_count}"
            )

        else:
            st.write(
                "**Step:** Final report"
            )

        st.divider()

        st.caption(
            "This tool reviews five launch gates:"
        )

        st.write("• Customer Value")
        st.write("• AI Quality")
        st.write("• Trust & Safety")
        st.write("• Operational Readiness")
        st.write("• Business Readiness")

        # -----------------------------------------------------------
        # ASSESSMENT HISTORY
        # -----------------------------------------------------------

        st.divider()
        history_container = st.empty()

        render_history_section(
            history_container=history_container,
            history=history,
            selected_history_id=selected_history_id,
        )

        return history_container


def render_history_section(
    history_container: Any,
    history: List[Dict[str, Any]],
    selected_history_id: Any,
) -> None:
    """Render the assessment history list into the provided container."""
    with history_container.container():
        st.markdown("### Assessment History")

        if not history:
            st.caption("No saved assessments yet.")
            return

        for record in history[:5]:
            record_id = str(
                record.get(
                    "id",
                    "",
                )
            )

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


# -------------------------------------------------------------------
# WELCOME
# -------------------------------------------------------------------

def render_welcome(
    questions_data: Dict[str, Any],
    sample_assessment: Dict[str, Any],
) -> None:
    """Render landing screen."""
    st.title(
        "AI Product Readiness Index"
    )

    st.subheader(
        "Assess whether your AI product "
        "is ready for launch."
    )

    st.caption(
        "3–5 minutes · 20 questions · "
        "5 launch gates · Instant recommendation"
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Time",
        "3–5 min",
    )

    c2.metric(
        "Questions",
        "20",
    )

    c3.metric(
        "Launch gates",
        "5",
    )

    st.info(
        "The AI Product Readiness Index "
        "helps AI Product Managers evaluate "
        "launch readiness across five gates "
        "before moving a feature into beta "
        "or production."
    )

    left, right = st.columns(2)

    with left:
        if st.button(
            "Start Index Review",
            type="primary",
            use_container_width=True,
        ):
            start_new_assessment(
                questions_data
            )

            st.rerun()

    with right:
        if st.button(
            "Load Sample Review",
            use_container_width=True,
        ):
            set_sample_answers(
                questions_data,
                sample_assessment,
            )

            st.session_state[
                "current_step"
            ] = len(
                questions_data.get(
                    "gates",
                    [],
                )
            ) + 1

            st.rerun()

    st.markdown("---")

    st.markdown(
        "### What this reviews"
    )

    st.write(
        "The index checks five launch gates: "
        "Customer Value, AI Quality, Trust & Safety, "
        "Operational Readiness, and Business Readiness."
    )

    st.markdown(
        "### How it works"
    )

    st.write(
        "You answer Yes / Partial / No for each "
        "question. The app calculates gate scores, "
        "flags launch blockers, and produces a "
        "launch recommendation."
    )


# -------------------------------------------------------------------
# QUESTION / GATE EXPERIENCE
# -------------------------------------------------------------------

def render_gate(
    gate: Dict[str, Any],
    step_number: int,
    gate_count: int,
) -> None:
    """Render one gate page."""
    st.title(
        "AI Product Readiness Index"
    )

    st.subheader(
        gate.get(
            "title",
            "Gate",
        )
    )

    description = gate.get(
        "description",
        "",
    )

    if description:
        st.caption(description)

    st.caption(
        f"Step {step_number} of "
        f"{gate_count}"
    )

    st.progress(
        min(
            step_number / gate_count,
            1.0,
        )
    )

    questions = gate.get(
        "questions",
        [],
    )

    answers = st.session_state.setdefault(
        "answers",
        {},
    )

    unanswered = 0

    for idx, question in enumerate(
        questions,
        start=1,
    ):
        qid = question.get("id")
        prompt = question.get(
            "prompt",
            "",
        )

        help_text = question.get(
            "help_text",
            "",
        )

        critical = bool(
            question.get(
                "critical",
                False,
            )
        )

        widget_key = f"answer_{qid}"

        current_value = st.session_state.get(
            widget_key,
            "Select an answer",
        )

        if current_value not in {
            "Select an answer",
            "Yes",
            "Partial",
            "No",
        }:
            current_value = (
                "Select an answer"
            )

        st.markdown(
            f"**{idx}. {prompt}**"
        )

        if critical:
            st.caption(
                "Critical launch blocker"
            )

        if help_text:
            st.caption(help_text)

        options = [
            "Select an answer",
            "Yes",
            "Partial",
            "No",
        ]

        selected = st.selectbox(
            "Answer",
            options,
            index=options.index(
                current_value
            ),
            key=widget_key,
            label_visibility="collapsed",
        )

        if selected == "Select an answer":
            answers.pop(
                qid,
                None,
            )

            unanswered += 1

        else:
            answers[qid] = (
                selected.lower()
            )

        st.divider()

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "Back",
            use_container_width=True,
        ):
            st.session_state[
                "current_step"
            ] = max(
                0,
                st.session_state[
                    "current_step"
                ] - 1,
            )

            st.rerun()

    with c2:
        next_label = (
            "View Results"
            if step_number == gate_count
            else "Next"
        )

        if st.button(
            next_label,
            type="primary",
            use_container_width=True,
        ):
            if step_number == gate_count:
                st.session_state[
                    "current_step"
                ] = gate_count + 1

            else:
                st.session_state[
                    "current_step"
                ] = step_number + 1

            st.rerun()

    if unanswered:
        st.caption(
            f"{unanswered} question(s) on "
            f"this gate are still unanswered."
        )


# -------------------------------------------------------------------
# RESULTS UI
# -------------------------------------------------------------------

def render_decision_banner(
    overall_score: float,
    overall_max: float,
    overall_pct: float,
    recommendation: str,
    confidence: str,
) -> None:
    """Render the top executive decision section."""
    score_text = format_score(
        round(overall_score),
        round(overall_max),
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
    """Render the executive summary using native Streamlit."""
    st.markdown(
        "### Executive Summary"
    )

    with st.container(
        border=True
    ):
        st.write(summary_text)


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


# -------------------------------------------------------------------
# HISTORICAL ASSESSMENT
# -------------------------------------------------------------------

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
        f"Saved assessment · "
        f"{display_date}"
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
            {}
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

    # -----------------------------------------------------------
    # HERO
    # -----------------------------------------------------------

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

    # -----------------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------------

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

    # -----------------------------------------------------------
    # GATE HEALTH
    # -----------------------------------------------------------

    st.divider()

    render_gate_health_cards(
        gate_results
    )

    # -----------------------------------------------------------
    # ACTION CENTER
    # -----------------------------------------------------------

    st.divider()

    render_action_center(
        blockers,
        next_actions,
    )

    # -----------------------------------------------------------
    # READ-ONLY MESSAGE
    # -----------------------------------------------------------

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


# -------------------------------------------------------------------
# RESULTS
# -------------------------------------------------------------------

def render_results(
    questions_data: Dict[str, Any],
    scoring_rules: Dict[str, Any],
    history_container: Any,
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

    # -----------------------------------------------------------
    # BUILD LIVE REPORT PAYLOAD
    # -----------------------------------------------------------

    report_payload = build_report_payload(
        assessment_result=assessment,
        recommendation_payload=recommendation_payload,
        product_name="AI Product Assessment",
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

    # -----------------------------------------------------------
    # EXECUTIVE HERO
    # -----------------------------------------------------------

    render_decision_banner(
        overall_score=overall_score,
        overall_max=overall_max,
        overall_pct=overall_pct,
        recommendation=recommendation,
        confidence=confidence,
    )

    # -----------------------------------------------------------
    # EXECUTIVE SUMMARY
    # -----------------------------------------------------------

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

    # -----------------------------------------------------------
    # GATE HEALTH
    # -----------------------------------------------------------

    st.divider()

    render_gate_health_cards(
        gate_results
    )

    # -----------------------------------------------------------
    # ACTION CENTER
    # -----------------------------------------------------------

    st.divider()

    render_action_center(
        blockers,
        next_actions,
    )

    # -----------------------------------------------------------
    # ADVANCED DETAILS
    # -----------------------------------------------------------

    st.divider()

    render_advanced_details(
        gate_results
    )

    # -----------------------------------------------------------
    # DOWNLOAD / SAVE
    # -----------------------------------------------------------

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
                    generate_assessment_id()
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
                    product_name="AI Product Assessment",
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

                render_history_section(
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
                "AI_Product_Readiness_Report.pdf"
            ),
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

    # -----------------------------------------------------------
    # CONTEXT
    # -----------------------------------------------------------

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

    # -----------------------------------------------------------
    # NAVIGATION
    # -----------------------------------------------------------

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
            )

            st.rerun()

    with c2:
        if st.button(
            "Restart Review",
            type="primary",
            use_container_width=True,
        ):
            clear_answer_state(
                questions_data
            )

            st.session_state[
                "current_step"
            ] = 0

            st.session_state[
                "current_assessment_id"
            ] = None

            st.session_state[
                "selected_history_id"
            ] = None

            st.session_state.pop(
                "report_payload",
                None,
            )

            st.session_state.pop(
                "report_pdf",
                None,
            )

            st.rerun()


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

def main() -> None:
    """Application entry point."""
    questions_data, scoring_rules, sample_assessment = (
        load_inputs()
    )

    # -----------------------------------------------------------
    # SESSION STATE INITIALIZATION
    # -----------------------------------------------------------

    if "current_step" not in st.session_state:
        st.session_state[
            "current_step"
        ] = 0

    if "answers" not in st.session_state:
        st.session_state[
            "answers"
        ] = {}

    if "assessment_history" not in st.session_state:
        st.session_state[
            "assessment_history"
        ] = []

    if "current_assessment_id" not in st.session_state:
        st.session_state[
            "current_assessment_id"
        ] = None

    if "selected_history_id" not in st.session_state:
        st.session_state[
            "selected_history_id"
        ] = None

    gate_count = len(
        questions_data.get(
            "gates",
            [],
        )
    )

    total_steps = gate_count + 2

    current_step = int(
        st.session_state[
            "current_step"
        ]
    )

    # -----------------------------------------------------------
    # SIDEBAR
    # -----------------------------------------------------------

    history_container = render_sidebar(
        questions_data=questions_data,
        current_step=current_step,
        total_steps=total_steps,
    )

    # -----------------------------------------------------------
    # HISTORICAL VIEW
    # -----------------------------------------------------------

    selected_history_id = (
        st.session_state.get(
            "selected_history_id"
        )
    )

    if selected_history_id:
        selected_record = get_assessment_by_id(
            st.session_state.get(
                "assessment_history",
                [],
            ),
            selected_history_id,
        )

        if selected_record is not None:
            render_historical_assessment(
                selected_record
            )

            return

        st.session_state[
            "selected_history_id"
        ] = None

    # -----------------------------------------------------------
    # CURRENT ASSESSMENT FLOW
    # -----------------------------------------------------------

    gates = questions_data.get(
        "gates",
        [],
    )

    if current_step == 0:
        render_welcome(
            questions_data,
            sample_assessment,
        )

        return

    if 1 <= current_step <= gate_count:
        gate = gates[
            get_gate_index(
                current_step
            )
        ]

        render_gate(
            gate=gate,
            step_number=current_step,
            gate_count=gate_count,
        )

        return

    render_results(
        questions_data,
        scoring_rules,
        history_container,
    )


if __name__ == "__main__":
    main()