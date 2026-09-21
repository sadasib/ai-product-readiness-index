from __future__ import annotations

from app.utils.product_context import (
    LAUNCH_STAGES,
    PRODUCT_TYPES,
    build_sample_product_context,
    create_product_context_snapshot,
    empty_product_context,
    get_product_display_name,
    normalize_product_context,
    validate_product_context,
)


def test_empty_product_context():
    result = empty_product_context()

    assert result == {
        "product_name": "",
        "product_type": "",
        "launch_stage": "",
        "assessment_owner": "",
    }


def test_normalize_product_context():
    context = {
        "product_name": "  Returns Agent  ",
        "product_type": " AI Agent ",
        "launch_stage": " Beta ",
        "assessment_owner": " Product Management ",
    }

    result = normalize_product_context(context)

    assert result == {
        "product_name": "Returns Agent",
        "product_type": "AI Agent",
        "launch_stage": "Beta",
        "assessment_owner": "Product Management",
    }


def test_normalize_missing_context():
    result = normalize_product_context(None)

    assert result == empty_product_context()


def test_valid_required_context():
    context = {
        "product_name": "Returns Agent",
        "launch_stage": "Beta",
    }

    is_valid, errors = validate_product_context(context)

    assert is_valid is True
    assert errors == []


def test_product_name_is_required():
    context = {
        "product_name": "",
        "launch_stage": "Beta",
    }

    is_valid, errors = validate_product_context(context)

    assert is_valid is False
    assert "Product name is required." in errors


def test_launch_stage_is_required():
    context = {
        "product_name": "Returns Agent",
        "launch_stage": "",
    }

    is_valid, errors = validate_product_context(context)

    assert is_valid is False
    assert "Launch stage is required." in errors


def test_invalid_launch_stage():
    context = {
        "product_name": "Returns Agent",
        "launch_stage": "Pilot",
    }

    is_valid, errors = validate_product_context(context)

    assert is_valid is False
    assert "Launch stage is invalid." in errors


def test_invalid_product_type():
    context = {
        "product_name": "Returns Agent",
        "product_type": "Robot",
        "launch_stage": "Beta",
    }

    is_valid, errors = validate_product_context(context)

    assert is_valid is False
    assert "Product type is invalid." in errors


def test_supported_product_types_and_launch_stages():
    assert "AI Agent" in PRODUCT_TYPES
    assert "Customer-facing AI experience" in PRODUCT_TYPES

    assert LAUNCH_STAGES == [
        "Internal",
        "Beta",
        "Production",
    ]


def test_snapshot_is_detached_from_original():
    context = {
        "product_name": "Returns Agent",
        "product_type": "AI Agent",
        "launch_stage": "Beta",
        "assessment_owner": "Product Management",
    }

    snapshot = create_product_context_snapshot(context)

    context["product_name"] = "Changed Product"
    context["launch_stage"] = "Production"

    assert snapshot["product_name"] == "Returns Agent"
    assert snapshot["launch_stage"] == "Beta"


def test_sample_product_context():
    result = build_sample_product_context()

    assert result == {
        "product_name": "Retail Returns Assistant",
        "product_type": "AI Agent",
        "launch_stage": "Beta",
        "assessment_owner": "Product Management",
    }


def test_get_product_display_name():
    assert (
        get_product_display_name(
            {"product_name": "Returns Agent"}
        )
        == "Returns Agent"
    )

    assert (
        get_product_display_name({})
        == "AI Product Assessment"
    )