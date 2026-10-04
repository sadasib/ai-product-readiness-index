from __future__ import annotations

import streamlit as st

from utils.product_context import (
    LAUNCH_STAGES,
    PRODUCT_TYPES,
    create_product_context_snapshot,
    empty_product_context,
    normalize_product_context,
    validate_product_context,
)


def render_product_context(
    first_gate_step: int,
) -> None:
    """Render the product context form shown before the gates."""
    current_context = normalize_product_context(
        st.session_state.get(
            "product_context",
            empty_product_context(),
        )
    )

    st.title("AI Product Readiness Index")

    st.subheader(
        "Tell us about the product"
    )

    st.caption(
        "Add a little context so the assessment, history, and report "
        "are easy to identify."
    )

    product_name = st.text_input(
        "Product name *",
        value=current_context.get(
            "product_name",
            "",
        ),
        placeholder="e.g. Customer Support Copilot",
        key="product_context_name",
    )

    product_type_options = [
        "Select a product type",
        *PRODUCT_TYPES,
    ]

    product_type_value = current_context.get(
        "product_type",
        "",
    )

    product_type_index = (
        product_type_options.index(
            product_type_value
        )
        if product_type_value in product_type_options
        else 0
    )

    product_type = st.selectbox(
        "Product type",
        product_type_options,
        index=product_type_index,
        key="product_context_type",
    )

    launch_stage_options = [
        "Select launch stage",
        *LAUNCH_STAGES,
    ]

    launch_stage_value = current_context.get(
        "launch_stage",
        "",
    )

    launch_stage_index = (
        launch_stage_options.index(
            launch_stage_value
        )
        if launch_stage_value in launch_stage_options
        else 0
    )

    launch_stage = st.selectbox(
        "Target launch stage *",
        launch_stage_options,
        index=launch_stage_index,
        key="product_context_stage",
    )

    assessment_owner = st.text_input(
        "Assessment owner",
        value=current_context.get(
            "assessment_owner",
            "",
        ),
        placeholder="e.g. Product Management",
        key="product_context_owner",
    )

    st.caption("* Required")

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "Back",
            use_container_width=True,
        ):
            st.session_state[
                "current_step"
            ] = 0

            st.rerun()

    with c2:
        if st.button(
            "Continue to Assessment",
            type="primary",
            use_container_width=True,
        ):
            context = {
                "product_name": product_name,
                "product_type": (
                    ""
                    if product_type
                    == "Select a product type"
                    else product_type
                ),
                "launch_stage": (
                    ""
                    if launch_stage
                    == "Select launch stage"
                    else launch_stage
                ),
                "assessment_owner": assessment_owner,
            }

            is_valid, errors = (
                validate_product_context(
                    context
                )
            )

            if not is_valid:
                for error in errors:
                    st.error(error)

            else:
                st.session_state[
                    "product_context"
                ] = (
                    create_product_context_snapshot(
                        context
                    )
                )

                st.session_state[
                    "current_step"
                ] = first_gate_step

                st.rerun()