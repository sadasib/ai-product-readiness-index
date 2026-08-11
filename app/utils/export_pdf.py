from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT_DIR = Path(__file__).resolve().parents[2]


def _build_styles() -> Dict[str, ParagraphStyle]:
    """Create reusable PDF styles."""
    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            alignment=TA_LEFT,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#6B7280"),
            spaceAfter=18,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#111827"),
            spaceBefore=8,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#374151"),
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#6B7280"),
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#6B7280"),
        ),
        "metric_value": ParagraphStyle(
            "MetricValue",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=21,
            textColor=colors.HexColor("#111827"),
        ),
        "gate_name": ParagraphStyle(
            "GateName",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#111827"),
        ),
        "gate_status": ParagraphStyle(
            "GateStatus",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#166534"),
        ),
    }


def _decision_color(decision: str) -> str:
    """Return a display color for the launch decision."""
    mapping = {
        "Ready for Production": "#166534",
        "Ready for Beta": "#92400E",
        "Additional Review Required": "#C2410C",
        "Not Ready": "#B91C1C",
    }
    return mapping.get(decision, "#374151")


def _gate_status(percentage: float) -> str:
    """Convert gate percentage to a human-readable status."""
    if percentage >= 90:
        return "Healthy"
    if percentage >= 75:
        return "Good"
    if percentage >= 60:
        return "Needs Attention"
    return "Critical"


def _gate_status_color(percentage: float) -> str:
    """Return a display color for gate health."""
    if percentage >= 90:
        return "#166534"
    if percentage >= 75:
        return "#92400E"
    if percentage >= 60:
        return "#C2410C"
    return "#B91C1C"


def create_pdf(
    product_name: str,
    recommendation: str,
    readiness_score: float,
    readiness_max: float,
    grade: str,
    confidence: str,
    executive_summary: str,
    gate_results: List[Dict[str, Any]],
    critical_items: List[str],
    immediate_actions: List[str],
    version: str = "1.1",
) -> bytes:
    """
    Generate an executive launch readiness report.

    Returns PDF content as bytes.
    """
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title="AI Product Readiness Index - Executive Launch Report",
        author="AI Product Readiness Index",
    )

    styles = _build_styles()
    story = []

    generated_date = datetime.now().strftime("%B %d, %Y")
    decision_color = _decision_color(recommendation)

    # ---------------------------------------------------------
    # PAGE 1 - EXECUTIVE SUMMARY
    # ---------------------------------------------------------

    story.append(
        Paragraph(
            "AI Product Readiness Index",
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            "Executive Launch Readiness Report",
            styles["subtitle"],
        )
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor("#E5E7EB"),
            spaceBefore=2,
            spaceAfter=18,
        )
    )

    meta_data = [
        [
            Paragraph("<b>Product</b>", styles["metric_label"]),
            Paragraph("<b>Generated</b>", styles["metric_label"]),
            Paragraph("<b>Version</b>", styles["metric_label"]),
        ],
        [
            Paragraph(escape(product_name), styles["body"]),
            Paragraph(escape(generated_date), styles["body"]),
            Paragraph(escape(version), styles["body"]),
        ],
    ]

    meta_table = Table(
        meta_data,
        colWidths=[3.6 * inch, 1.65 * inch, 1.2 * inch],
    )

    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E5E7EB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(meta_table)
    story.append(Spacer(1, 18))

    decision_table = Table(
        [
            [
                Paragraph("LAUNCH DECISION", styles["metric_label"]),
                Paragraph("READINESS INDEX", styles["metric_label"]),
                Paragraph("GRADE", styles["metric_label"]),
                Paragraph("CONFIDENCE", styles["metric_label"]),
            ],
            [
                Paragraph(
                    f"<font color='{decision_color}'><b>{escape(recommendation.upper())}</b></font>",
                    styles["body"],
                ),
                Paragraph(
                    f"<b>{readiness_score:.0f} / {readiness_max:.0f}</b>",
                    styles["metric_value"],
                ),
                Paragraph(
                    escape(grade),
                    styles["metric_value"],
                ),
                Paragraph(
                    escape(confidence),
                    styles["body"],
                ),
            ],
        ],
        colWidths=[2.45 * inch, 1.55 * inch, 0.9 * inch, 1.55 * inch],
    )

    decision_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#D1D5DB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story.append(decision_table)
    story.append(Spacer(1, 18))

    story.append(
        Paragraph(
            "Executive Summary",
            styles["section"],
        )
    )

    story.append(
        Paragraph(
            escape(executive_summary),
            styles["body"],
        )
    )

    # ---------------------------------------------------------
    # PAGE 2 - GATE HEALTH
    # ---------------------------------------------------------

    story.append(PageBreak())

    story.append(
        Paragraph(
            "Launch Gate Health",
            styles["section"],
        )
    )

    gate_rows = [
        [
            Paragraph("Launch Gate", styles["metric_label"]),
            Paragraph("Score", styles["metric_label"]),
            Paragraph("Readiness", styles["metric_label"]),
            Paragraph("Status", styles["metric_label"]),
        ]
    ]

    for gate in gate_results:
        title = str(gate.get("gate_title", "Gate"))
        score = float(gate.get("score", 0))
        max_score = float(gate.get("max_score", 20))
        percentage = float(gate.get("percentage", 0))

        status = _gate_status(percentage)
        status_color = _gate_status_color(percentage)

        gate_rows.append(
            [
                Paragraph(escape(title), styles["gate_name"]),
                Paragraph(
                    f"{score:.1f} / {max_score:.0f}",
                    styles["body"],
                ),
                Paragraph(
                    f"{percentage:.0f}%",
                    styles["body"],
                ),
                Paragraph(
                    f"<font color='{status_color}'><b>{escape(status)}</b></font>",
                    styles["gate_status"],
                ),
            ]
        )

    gate_table = Table(
        gate_rows,
        colWidths=[3.25 * inch, 1.0 * inch, 1.0 * inch, 1.2 * inch],
        repeatRows=1,
    )

    gate_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#D1D5DB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.append(gate_table)

    # ---------------------------------------------------------
    # PAGE 3 - ACTION CENTER
    # ---------------------------------------------------------

    story.append(PageBreak())

    story.append(
        Paragraph(
            "Action Center",
            styles["section"],
        )
    )

    action_rows = []

    for critical_item in critical_items:
        action_rows.append(
            [
                Paragraph(
                    "<font color='#B91C1C'><b>CRITICAL</b></font>",
                    styles["body"],
                ),
                Paragraph(
                    escape(critical_item),
                    styles["body"],
                ),
            ]
        )

    for action in immediate_actions[:4]:
        action_rows.append(
            [
                Paragraph(
                    "<font color='#92400E'><b>IMMEDIATE</b></font>",
                    styles["body"],
                ),
                Paragraph(
                    escape(action),
                    styles["body"],
                ),
            ]
        )

    if not action_rows:
        action_rows.append(
            [
                Paragraph(
                    "<font color='#166534'><b>NO BLOCKERS</b></font>",
                    styles["body"],
                ),
                Paragraph(
                    "No immediate launch actions are required.",
                    styles["body"],
                ),
            ]
        )

    action_table = Table(
        action_rows,
        colWidths=[1.25 * inch, 5.2 * inch],
    )

    action_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#D1D5DB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story.append(action_table)
    story.append(Spacer(1, 20))

    story.append(
        HRFlowable(
            width="100%",
            thickness=0.6,
            color=colors.HexColor("#E5E7EB"),
            spaceBefore=8,
            spaceAfter=8,
        )
    )

    story.append(
        Paragraph(
            "Generated using AI Product Readiness Index · Personal portfolio project · "
            "Synthetic data and public concepts",
            styles["small"],
        )
    )

    document.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def create_sample_pdf() -> bytes:
    """
    Generate a sample report for PR1 validation.
    """
    sample_gates = [
        {
            "gate_title": "Customer Value",
            "score": 18,
            "max_score": 20,
            "percentage": 90,
        },
        {
            "gate_title": "AI Quality",
            "score": 21,
            "max_score": 25,
            "percentage": 84,
        },
        {
            "gate_title": "Trust & Safety",
            "score": 18,
            "max_score": 20,
            "percentage": 90,
        },
        {
            "gate_title": "Operational Readiness",
            "score": 18,
            "max_score": 20,
            "percentage": 90,
        },
        {
            "gate_title": "Business Readiness",
            "score": 13,
            "max_score": 15,
            "percentage": 87,
        },
    ]

    return create_pdf(
        product_name="Retail Returns Assistant",
        recommendation="Ready for Beta",
        readiness_score=88,
        readiness_max=100,
        grade="A-",
        confidence="Moderate",
        executive_summary=(
            "The feature demonstrates strong overall readiness across Customer Value, "
            "Trust & Safety, Operational Readiness, and Business Readiness. "
            "One critical blocker remains around escalation behavior for high-risk cases."
        ),
        gate_results=sample_gates,
        critical_items=[
            "Validate escalation behavior for high-risk cases.",
        ],
        immediate_actions=[
            "Complete structured human evaluation.",
            "Document the rollback strategy.",
            "Define monitoring and alert thresholds.",
        ],
    )


if __name__ == "__main__":
    output_path = ROOT_DIR / "sample_launch_readiness_report.pdf"

    pdf = create_sample_pdf()

    output_path.write_bytes(pdf)

    print(f"Sample PDF created: {output_path}")