from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.helpers import (
    answer_label,
    build_progress,
    count_questions,
    format_score,
    load_json,
)
from utils.recommendations import build_recommendation_payload
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


@st.cache_data(show_spinner=False)
def load_inputs() -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Load app inputs from disk."""
    questions_data = load_json(QUESTIONS_PATH)
    scoring_rules = load_json(SCORING_RULES_PATH)
    sample_assessment = load_json(SAMPLE_ASSESSMENT_PATH)
    return questions_data, scoring_rules, sample_assessment


def get_gate_index(current_step: int) -> int:
    """Convert app step to gate list index."""
    return current_step - 1


def get_stage_label(current_step: int, gate_count: int) -> str:
    """Return a clean label for the current app stage."""
    if current_step == 0:
        return "Not started"
    if 1 <= current_step <= gate_count:
        return f"Gate {current_step}/{gate_count}"
    return "Final report"


def clear_answer_state(questions_data: Dict[str, Any]) -> None:
    """Clear all stored answers and widget state."""
    st.session_state["answers"] = {}
    for gate in questions_data.get("gates", []):
        for question in gate.get("questions", []):
            widget_key = f"answer_{question.get('id')}"
            if widget_key in st.session_state:
                del st.session_state[widget_key]


def set_sample_answers(
    questions_data: Dict[str, Any],
    sample_assessment: Dict[str, Any],
) -> None:
    """Load sample answers into session state and widget state."""
    answers = sample_assessment.get("answers", {})
    st.session_state["answers"] = dict(answers)

    for gate in questions_data.get("gates", []):
        for question in gate.get("questions", []):
            qid = question.get("id")
            widget_key = f"answer_{qid}"
            raw_answer = answer_label(answers.get(qid))
            st.session_state[widget_key] = (
                raw_answer if raw_answer in {"Yes", "Partial", "No"} else "Select an answer"
            )


def render_sidebar(
    questions_data: Dict[str, Any],
    current_step: int,
    total_steps: int,
) -> None:
    """Sidebar summary and progress."""
    total_questions, critical_questions = count_questions(questions_data)
    answered_count = len(st.session_state.get("answers", {}))
    progress_pct = build_progress(answered_count, total_questions)
    gate_count = len(questions_data.get("gates", []))
    stage_label = get_stage_label(current_step, gate_count)

    with st.sidebar:
        st.markdown("## AI Product Readiness Index")
        st.caption("Powered by the AI Product Playbook")

        st.progress(progress_pct / 100 if progress_pct else 0.0)
        st.write(f"**Progress:** {progress_pct:.0f}%")
        st.write(f"**Answered:** {answered_count}/{total_questions}")
        st.write(f"**Critical questions:** {critical_questions}")
        st.write(f"**Stage:** {stage_label}")

        if current_step == 0:
            st.write("**Step:** Start")
        elif 1 <= current_step <= gate_count:
            st.write(f"**Step:** {current_step}/{gate_count}")
        else:
            st.write("**Step:** Final report")

        st.divider()
        st.caption("This tool reviews five launch gates:")
        st.write("• Customer Value")
        st.write("• AI Quality")
        st.write("• Trust & Safety")
        st.write("• Operational Readiness")
        st.write("• Business Readiness")


def render_welcome(
    questions_data: Dict[str, Any],
    sample_assessment: Dict[str, Any],
) -> None:
    """Landing screen."""
    st.title("AI Product Readiness Index")
    st.subheader("Assess whether your AI product is ready for launch.")
    st.caption("3–5 minutes · 20 questions · 5 launch gates · Instant recommendation")

    c1, c2, c3 = st.columns(3)
    c1.metric("Time", "3–5 min")
    c2.metric("Questions", "20")
    c3.metric("Launch gates", "5")

    st.info(
        "The AI Product Readiness Index helps AI Product Managers evaluate launch readiness "
        "across five gates before moving a feature into beta or production."
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button("Start Index Review", type="primary", use_container_width=True):
            clear_answer_state(questions_data)
            st.session_state["current_step"] = 1
            st.rerun()

    with c2:
        if st.button("Load Sample Review", use_container_width=True):
            set_sample_answers(questions_data, sample_assessment)
            st.session_state["current_step"] = len(questions_data.get("gates", [])) + 1
            st.rerun()

    st.markdown("---")
    st.markdown("### What this reviews")
    st.write(
        "The index checks five launch gates: Customer Value, AI Quality, Trust & Safety, "
        "Operational Readiness, and Business Readiness."
    )

    st.markdown("### How it works")
    st.write(
        "You answer Yes / Partial / No for each question. The app calculates gate scores, "
        "flags launch blockers, and produces a launch recommendation."
    )


def render_gate(
    gate: Dict[str, Any],
    step_number: int,
    gate_count: int,
) -> None:
    """Render one gate page."""
    st.title("AI Product Readiness Index")
    st.subheader(gate.get("title", "Gate"))

    description = gate.get("description", "")
    if description:
        st.caption(description)

    st.caption(f"Step {step_number} of {gate_count}")
    st.progress(min(step_number / gate_count, 1.0))

    questions = gate.get("questions", [])
    answers = st.session_state.setdefault("answers", {})

    unanswered = 0

    for idx, question in enumerate(questions, start=1):
        qid = question.get("id")
        prompt = question.get("prompt", "")
        help_text = question.get("help_text", "")
        critical = bool(question.get("critical", False))

        widget_key = f"answer_{qid}"
        current_value = st.session_state.get(widget_key, "Select an answer")
        if current_value not in {"Select an answer", "Yes", "Partial", "No"}:
            current_value = "Select an answer"

        st.markdown(f"**{idx}. {prompt}**")
        if critical:
            st.caption("Critical launch blocker")
        if help_text:
            st.caption(help_text)

        options = ["Select an answer", "Yes", "Partial", "No"]
        selected = st.selectbox(
            "Answer",
            options,
            index=options.index(current_value),
            key=widget_key,
            label_visibility="collapsed",
        )

        if selected == "Select an answer":
            answers.pop(qid, None)
            unanswered += 1
        else:
            answers[qid] = selected.lower()

        st.divider()

    c1, c2 = st.columns(2)

    with c1:
        if st.button("Back", use_container_width=True):
            st.session_state["current_step"] = max(0, st.session_state["current_step"] - 1)
            st.rerun()

    with c2:
        next_label = "View Results" if step_number == gate_count else "Next"
        if st.button(next_label, type="primary", use_container_width=True):
            if step_number == gate_count:
                st.session_state["current_step"] = gate_count + 1
            else:
                st.session_state["current_step"] = step_number + 1
            st.rerun()

    if unanswered:
        st.caption(f"{unanswered} question(s) on this gate are still unanswered.")


def render_results(
    questions_data: Dict[str, Any],
    scoring_rules: Dict[str, Any],
) -> None:
    """Render the final scorecard."""
    st.title("AI Product Readiness Index")
    st.subheader("Launch Readiness Report")

    answers = st.session_state.get("answers", {})
    assessment = calculate_assessment(questions_data, scoring_rules, answers)
    recommendation_payload = build_recommendation_payload(assessment)

    overall_score = float(assessment["overall_score"])
    overall_max = float(assessment["overall_max_score"])
    overall_pct = float(assessment["overall_percentage"])

    recommendation = recommendation_payload["recommendation"]
    confidence = recommendation_payload["confidence"]
    top_missing_items = recommendation_payload["top_missing_items"]
    next_actions = recommendation_payload["next_actions"]

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Readiness Index", format_score(round(overall_score), round(overall_max)))

    with c2:
        st.metric("Overall Readiness", f"{overall_pct:.1f}%")

    with c3:
        st.metric("Decision", recommendation)

    if recommendation == "Ready for Production":
        st.success(f"Confidence: {confidence}")
    elif recommendation == "Ready for Beta":
        st.info(f"Confidence: {confidence}")
    elif recommendation == "Additional Review Required":
        st.warning(f"Confidence: {confidence}")
    else:
        st.error(f"Confidence: {confidence}")

    st.markdown("### Gate Scores")

    gate_results = assessment.get("gate_results", [])
    if gate_results:
        chart_df = pd.DataFrame(
            {
                "Gate": [g["gate_title"] for g in gate_results],
                "Score %": [g["percentage"] for g in gate_results],
            }
        )

        fig = px.bar(
            chart_df,
            x="Gate",
            y="Score %",
            text="Score %",
            range_y=[0, 100],
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(
            yaxis_title="Score %",
            xaxis_title="",
            showlegend=False,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Launch Blockers")
    blockers = assessment.get("launch_blockers", [])
    if blockers:
        for blocker in blockers:
            st.error(f"**{blocker.get('gate_title', 'Gate')}** — {blocker.get('prompt', '')}")
    else:
        st.success("No critical launch blockers detected.")

    st.markdown("### Top Risks")
    if top_missing_items:
        for item in top_missing_items:
            st.write(f"• {item}")
    else:
        st.write("No major missing items detected.")

    st.markdown("### Next Actions")
    if next_actions:
        for action in next_actions:
            st.write(f"• {action}")
    else:
        st.write("No additional actions required.")

    st.markdown("### Gate Details")
    for gate in gate_results:
        gate_title = gate["gate_title"]
        gate_score = float(gate["score"])
        gate_max_score = float(gate["max_score"])
        gate_percentage = float(gate["percentage"])

        with st.expander(
            f"{gate_title} — {gate_score:.1f}/{gate_max_score:.0f} ({gate_percentage:.1f}%)"
        ):
            failed_questions = gate.get("failed_questions", [])
            if failed_questions:
                for failed in failed_questions:
                    label = failed.get("prompt", "")
                    answer = failed.get("answer", "no answer")
                    points = failed.get("points", 0)
                    critical = "Critical" if failed.get("critical", False) else "Non-critical"
                    st.write(
                        f"• {label} — Answer: {answer.title()} — {points} points — {critical}"
                    )
            else:
                st.write("All questions in this gate passed.")

    st.markdown("### What this means")
    st.write(
        "This result should support a launch decision discussion. It does not replace product judgment; "
        "it makes readiness explicit and easier to review with engineering, operations, and risk partners."
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Back to Review", use_container_width=True):
            st.session_state["current_step"] = len(questions_data.get("gates", []))
            st.rerun()
    with c2:
        if st.button("Restart Review", type="primary", use_container_width=True):
            clear_answer_state(questions_data)
            st.session_state["current_step"] = 0
            st.rerun()


def main() -> None:
    questions_data, scoring_rules, sample_assessment = load_inputs()

    if "current_step" not in st.session_state:
        st.session_state["current_step"] = 0

    if "answers" not in st.session_state:
        st.session_state["answers"] = {}

    gate_count = len(questions_data.get("gates", []))
    total_steps = gate_count + 2
    current_step = int(st.session_state["current_step"])

    render_sidebar(
        questions_data=questions_data,
        current_step=current_step,
        total_steps=total_steps,
    )

    gates = questions_data.get("gates", [])

    if current_step == 0:
        render_welcome(questions_data, sample_assessment)
        return

    if 1 <= current_step <= gate_count:
        gate = gates[get_gate_index(current_step)]
        render_gate(
            gate=gate,
            step_number=current_step,
            gate_count=gate_count,
        )
        return

    render_results(questions_data, scoring_rules)


if __name__ == "__main__":
    main()