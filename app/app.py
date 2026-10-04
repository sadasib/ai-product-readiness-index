from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import streamlit as st

from state import (
    get_stage_label,
    set_sample_answers,
    start_new_assessment,
    start_product_context,
)

from utils.helpers import (
    build_progress,
    count_questions,
    load_json,
)

from utils.assessment_history import (
    get_assessment_by_id,
    get_assessment_history,
)

from utils.product_context import (
    empty_product_context,
)

from views.assessment import render_gate
from views.history import (
    render_historical_assessment,
    render_history_section,
)
from views.product_context import render_product_context
from views.results import render_results
from views.welcome import render_welcome


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"

QUESTIONS_PATH = DATA_DIR / "questions.json"
SCORING_RULES_PATH = DATA_DIR / "scoring_rules.json"
SAMPLE_ASSESSMENT_PATH = DATA_DIR / "sample_assessment.json"

PRODUCT_CONTEXT_STEP = 1
FIRST_GATE_STEP = 2

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

        elif current_step == PRODUCT_CONTEXT_STEP:
            st.write("**Step:** Product context")

        elif FIRST_GATE_STEP <= current_step <= gate_count + 1:
            st.write(
                f"**Step:** "
                f"{current_step - 1}/{gate_count}"
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


# -------------------------------------------------------------------
# WELCOME
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# QUESTION / GATE EXPERIENCE
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# RESULTS UI
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# HISTORICAL ASSESSMENT
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# RESULTS
# -------------------------------------------------------------------

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

    if "product_context" not in st.session_state:
        st.session_state[
            "product_context"
        ] = empty_product_context()

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

    total_steps = gate_count + 3

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
            questions_data=questions_data,
            sample_assessment=sample_assessment,
            start_new_assessment=start_new_assessment,
            start_product_context=start_product_context,
            set_sample_answers=set_sample_answers,
        )

        return

    if current_step == PRODUCT_CONTEXT_STEP:
        render_product_context(
            first_gate_step=FIRST_GATE_STEP,
            )
        return

    if FIRST_GATE_STEP <= current_step <= gate_count + 1:
        gate_index = current_step - FIRST_GATE_STEP
        gate = gates[gate_index]

        render_gate(
            gate=gate,
            step_number=current_step - 1,
            gate_count=gate_count,
        )

        return

    render_results(
        questions_data=questions_data,
        scoring_rules=scoring_rules,
        history_container=history_container,
        render_history_section_fn=render_history_section,
    )


if __name__ == "__main__":
    main()