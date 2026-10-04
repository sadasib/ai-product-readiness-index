from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def render_gate(
    gate: Dict[str, Any],
    step_number: int,
    gate_count: int,
) -> None:
    """Render one assessment gate."""
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
        st.session_state[
            "current_step"
        ] += 1

        st.rerun()

    if unanswered:
        st.caption(
            f"{unanswered} question(s) on "
            f"this gate are still unanswered."
        )