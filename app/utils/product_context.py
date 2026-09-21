from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple


PRODUCT_TYPES = [
    "Customer-facing AI experience",
    "Employee/Internal Copilot",
    "AI Agent",
    "AI-powered workflow",
    "AI Platform/Infrastructure",
    "Other",
]

LAUNCH_STAGES = [
    "Internal",
    "Beta",
    "Production",
]


def empty_product_context() -> Dict[str, str]:
    """Return an empty product-context object."""
    return {
        "product_name": "",
        "product_type": "",
        "launch_stage": "",
        "assessment_owner": "",
    }


def normalize_product_context(
    context: Dict[str, Any] | None,
) -> Dict[str, str]:
    """Normalize product-context values into clean strings."""
    source = context or {}

    return {
        "product_name": str(
            source.get("product_name", "")
        ).strip(),
        "product_type": str(
            source.get("product_type", "")
        ).strip(),
        "launch_stage": str(
            source.get("launch_stage", "")
        ).strip(),
        "assessment_owner": str(
            source.get("assessment_owner", "")
        ).strip(),
    }


def validate_product_context(
    context: Dict[str, Any] | None,
) -> Tuple[bool, List[str]]:
    """
    Validate required product context.

    Product name and launch stage are required.
    Product type and assessment owner are optional.
    """
    normalized = normalize_product_context(context)

    errors: List[str] = []

    if not normalized["product_name"]:
        errors.append("Product name is required.")

    if not normalized["launch_stage"]:
        errors.append("Launch stage is required.")

    elif normalized["launch_stage"] not in LAUNCH_STAGES:
        errors.append("Launch stage is invalid.")

    product_type = normalized["product_type"]

    if product_type and product_type not in PRODUCT_TYPES:
        errors.append("Product type is invalid.")

    return len(errors) == 0, errors


def create_product_context_snapshot(
    context: Dict[str, Any] | None,
) -> Dict[str, str]:
    """
    Create a detached snapshot of product context.

    Saved assessments should retain the context that existed
    when the assessment was created.
    """
    normalized = normalize_product_context(context)

    return deepcopy(normalized)


def build_sample_product_context() -> Dict[str, str]:
    """Return synthetic context for the sample assessment."""
    return {
        "product_name": "Retail Returns Assistant",
        "product_type": "AI Agent",
        "launch_stage": "Beta",
        "assessment_owner": "Product Management",
    }


def get_product_display_name(
    context: Dict[str, Any] | None,
) -> str:
    """Return a safe display name for reports and history."""
    normalized = normalize_product_context(context)

    return (
        normalized["product_name"]
        or "AI Product Assessment"
    )