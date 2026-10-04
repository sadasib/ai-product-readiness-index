from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def render_welcome(
    questions_data: Dict[str, Any],
    sample_assessment: Dict[str, Any],
    start_new_assessment,
    start_product_context,
    set_sample_answers,
) -> None:
    """Render the landing screen."""
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

            start_product_context()

            st.session_state[
                "current_step"
            ] = 1

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
            ] = (
                len(
                    questions_data.get(
                        "gates",
                        [],
                    )
                )
                + 2
            )

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