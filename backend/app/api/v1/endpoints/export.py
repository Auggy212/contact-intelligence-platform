"""
PDF export endpoint — generates a professional contract review report.
"""

import io
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_tenant_id
from app.core.logging import get_logger
from app.models.clause import ClauseFlag
from app.models.project import Project, ProjectFile
from app.models.task import AnalysisTask

router = APIRouter(prefix="/projects/{project_id}/export", tags=["Export"])
logger = get_logger(__name__)

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_SEVERITY_COLOR = {
    "critical": "#c0392b",
    "high": "#d35400",
    "medium": "#b7860b",
    "low": "#1a7a4a",
    "info": "#1a5276",
}
_TASK_LABELS = {
    "template_comparison": "Template Comparison",
    "vendor_diff": "Vendor Diff Analysis",
    "law_validation": "Indian Law Validation",
    "checklist_validation": "Checklist Validation",
}
_FLAG_LABELS = {
    "template_deviation": "Template Deviation",
    "clause_added": "New Clause",
    "clause_missing": "Missing Clause",
    "vendor_redline": "Vendor Redline",
    "law_violation": "Law Violation",
    "law_at_risk": "Law Risk",
    "checklist_violation": "Checklist Violation",
}


@router.get("/pdf")
async def export_pdf(
    project_id: uuid.UUID,
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    proj_result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == uuid.UUID(tenant_id),
        )
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        from app.core.exceptions import not_found
        raise not_found("Project")

    files_result = await session.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.file_role)
    )
    files = files_result.scalars().all()

    tasks_result = await session.execute(
        select(AnalysisTask).where(AnalysisTask.project_id == project_id)
        .order_by(AnalysisTask.task_type)
    )
    tasks = tasks_result.scalars().all()

    flags_result = await session.execute(
        select(ClauseFlag).where(
            ClauseFlag.project_id == project_id,
            ClauseFlag.organization_id == uuid.UUID(tenant_id),
        ).order_by(ClauseFlag.severity, ClauseFlag.created_at)
    )
    flags = flags_result.scalars().all()

    pdf_bytes = _generate_pdf(project, files, tasks, flags)

    filename = f"ContractIQ_Report_{project.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _generate_pdf(project, files, tasks, flags) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable, PageBreak, Paragraph, SimpleDocTemplate,
        Spacer, Table, TableStyle, KeepTogether,
    )

    W, H = A4
    buffer = io.BytesIO()

    BRAND       = colors.HexColor("#1a3a5c")
    BRAND_LIGHT = colors.HexColor("#e8f0f9")
    ACCENT      = colors.HexColor("#2e86c1")
    RULE_GREY   = colors.HexColor("#d5d8dc")
    ROW_ALT     = colors.HexColor("#f4f6f9")
    TEXT_GREY   = colors.HexColor("#555555")

    SEV_COLORS = {k: colors.HexColor(v) for k, v in _SEVERITY_COLOR.items()}

    def _make_doc():
        def _header_footer(canvas, doc):
            canvas.saveState()
            # Header bar
            canvas.setFillColor(BRAND)
            canvas.rect(0, H - 18*mm, W, 18*mm, fill=1, stroke=0)
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 9)
            canvas.drawString(20*mm, H - 11*mm, "ContractIQ — AI Contract Review Report")
            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(W - 20*mm, H - 11*mm, project.name)
            # Footer
            canvas.setFillColor(RULE_GREY)
            canvas.rect(0, 0, W, 12*mm, fill=1, stroke=0)
            canvas.setFillColor(TEXT_GREY)
            canvas.setFont("Helvetica", 7)
            canvas.drawString(20*mm, 4.5*mm,
                f"Generated {datetime.now().strftime('%d %B %Y %H:%M')} IST  |  CONFIDENTIAL — FOR LEGAL REVIEW ONLY")
            canvas.drawRightString(W - 20*mm, 4.5*mm, f"Page {doc.page}")
            canvas.restoreState()

        return SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=22*mm, rightMargin=22*mm,
            topMargin=26*mm, bottomMargin=20*mm,
            onFirstPage=_header_footer,
            onLaterPages=_header_footer,
        )

    doc = _make_doc()
    styles = getSampleStyleSheet()

    # ── Custom styles ──────────────────────────────────────────────────────────
    S = {
        "title": ParagraphStyle("CTitle", fontSize=26, fontName="Helvetica-Bold",
                                textColor=BRAND, spaceAfter=4),
        "subtitle": ParagraphStyle("CSub", fontSize=13, fontName="Helvetica",
                                   textColor=ACCENT, spaceAfter=2),
        "h2": ParagraphStyle("CH2", fontSize=13, fontName="Helvetica-Bold",
                              textColor=BRAND, spaceBefore=10, spaceAfter=4),
        "h3": ParagraphStyle("CH3", fontSize=10, fontName="Helvetica-Bold",
                              textColor=BRAND, spaceBefore=6, spaceAfter=2),
        "body": ParagraphStyle("CBody", fontSize=9, leading=13, textColor=colors.black),
        "small": ParagraphStyle("CSmall", fontSize=8, leading=11, textColor=TEXT_GREY),
        "label": ParagraphStyle("CLabel", fontSize=7.5, fontName="Helvetica-Bold",
                                textColor=TEXT_GREY, spaceAfter=1),
        "disclaimer": ParagraphStyle("CDisc", fontSize=8, leading=11,
                                     textColor=TEXT_GREY, fontName="Helvetica-Oblique"),
    }

    def HR(color=RULE_GREY, thickness=0.6):
        return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=4)

    def sev_pill(sev: str) -> Paragraph:
        c = _SEVERITY_COLOR.get(sev, "#888888")
        return Paragraph(
            f'<font color="{c}"><b>{sev.upper()}</b></font>',
            S["small"],
        )

    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 22*mm))

    # Blue cover block
    cover_data = [[
        Paragraph("CONTRACT REVIEW REPORT", S["title"]),
    ]]
    cover_table = Table(cover_data, colWidths=[165*mm])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
        ("LEFTPADDING", (0, 0), (-1, -1), 8*mm),
        ("TOPPADDING", (0, 0), (-1, -1), 6*mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6*mm),
        ("LINEBELOW", (0, 0), (-1, 0), 3, ACCENT),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph(f"Project: {project.name}", S["subtitle"]))
    story.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%d %B %Y at %H:%M IST')}",
        S["small"],
    ))
    if project.description:
        story.append(Spacer(1, 3))
        story.append(Paragraph(project.description, S["body"]))

    story.append(Spacer(1, 6*mm))
    story.append(HR(ACCENT, 1.5))

    # Document manifest
    if files:
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph("Documents Reviewed", S["h2"]))
        role_labels = {"A": "Template (Master)", "B": "Proposed Draft", "C": "Vendor Reply"}
        doc_data = [["Role", "Filename", "Status"]]
        for f in sorted(files, key=lambda x: x.file_role):
            doc_data.append([
                role_labels.get(f.file_role, f.file_role),
                f.original_filename,
                "Parsed" if f.parse_status == "completed" else f.parse_status.title(),
            ])
        doc_table = Table(doc_data, colWidths=[38*mm, 95*mm, 32*mm])
        doc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
            ("GRID", (0, 0), (-1, -1), 0.4, RULE_GREY),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(doc_table)

    # Analysis tasks run
    if tasks:
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph("Analysis Tasks Performed", S["h2"]))
        task_data = [["Task", "Status"]]
        for t in tasks:
            task_data.append([
                _TASK_LABELS.get(t.task_type, t.task_type),
                t.status.title(),
            ])
        task_table = Table(task_data, colWidths=[120*mm, 45*mm])
        task_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
            ("GRID", (0, 0), (-1, -1), 0.4, RULE_GREY),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(task_table)

    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(
        "⚠  This report is generated by ContractIQ AI and is intended to assist qualified legal "
        "professionals in their review. It does not constitute legal advice. All findings must be "
        "independently verified before any contractual decisions are made.",
        S["disclaimer"],
    ))

    # ══════════════════════════════════════════════════════════════════════════
    # EXECUTIVE SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("Executive Summary", S["h2"]))
    story.append(HR(ACCENT, 1))

    severity_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    review_counts = {"pending": 0, "approved": 0, "rejected": 0}
    high_risk_count = 0
    total_confidence = 0.0
    conf_count = 0

    for f in flags:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
        type_counts[f.flag_type or "other"] = type_counts.get(f.flag_type or "other", 0) + 1
        review_counts[f.reviewer_status or "pending"] = review_counts.get(f.reviewer_status or "pending", 0) + 1
        if f.severity in ("critical", "high"):
            high_risk_count += 1
        if f.confidence is not None:
            total_confidence += f.confidence
            conf_count += 1

    avg_conf = f"{total_confidence / conf_count:.0%}" if conf_count else "N/A"

    # KPI row
    kpi_data = [[
        Paragraph(str(len(flags)), ParagraphStyle("KN", fontSize=22, fontName="Helvetica-Bold", textColor=BRAND, alignment=1)),
        Paragraph(str(severity_counts.get("critical", 0)), ParagraphStyle("KN2", fontSize=22, fontName="Helvetica-Bold", textColor=SEV_COLORS.get("critical", BRAND), alignment=1)),
        Paragraph(str(high_risk_count), ParagraphStyle("KN3", fontSize=22, fontName="Helvetica-Bold", textColor=SEV_COLORS.get("high", BRAND), alignment=1)),
        Paragraph(str(review_counts["pending"]), ParagraphStyle("KN4", fontSize=22, fontName="Helvetica-Bold", textColor=colors.HexColor("#7d6608"), alignment=1)),
        Paragraph(avg_conf, ParagraphStyle("KN5", fontSize=22, fontName="Helvetica-Bold", textColor=ACCENT, alignment=1)),
    ], [
        Paragraph("Total Findings", ParagraphStyle("KL", fontSize=8, textColor=TEXT_GREY, alignment=1)),
        Paragraph("Critical", ParagraphStyle("KL2", fontSize=8, textColor=TEXT_GREY, alignment=1)),
        Paragraph("High Risk", ParagraphStyle("KL3", fontSize=8, textColor=TEXT_GREY, alignment=1)),
        Paragraph("Pending Review", ParagraphStyle("KL4", fontSize=8, textColor=TEXT_GREY, alignment=1)),
        Paragraph("Avg Confidence", ParagraphStyle("KL5", fontSize=8, textColor=TEXT_GREY, alignment=1)),
    ]]
    kpi_table = Table(kpi_data, colWidths=[33*mm]*5)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, RULE_GREY),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE_GREY),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, RULE_GREY),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 5*mm))

    # Severity breakdown table
    story.append(Paragraph("Findings by Severity", S["h3"]))
    sev_data = [["Severity", "Count", "% of Total"]]
    for sev in ["critical", "high", "medium", "low", "info"]:
        cnt = severity_counts.get(sev, 0)
        if cnt:
            pct = f"{cnt / len(flags) * 100:.0f}%" if flags else "0%"
            sev_data.append([
                Paragraph(f'<font color="{_SEVERITY_COLOR[sev]}"><b>{sev.upper()}</b></font>', S["small"]),
                str(cnt),
                pct,
            ])
    if len(sev_data) > 1:
        sev_table = Table(sev_data, colWidths=[55*mm, 30*mm, 30*mm])
        sev_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
            ("GRID", (0, 0), (-1, -1), 0.4, RULE_GREY),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ]))
        story.append(sev_table)

    # Review status
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("Review Status", S["h3"]))
    rev_data = [["Status", "Count"]]
    for status, cnt in review_counts.items():
        if cnt:
            rev_data.append([status.title(), str(cnt)])
    rev_table = Table(rev_data, colWidths=[55*mm, 30*mm])
    rev_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE_GREY),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]))
    story.append(rev_table)

    # ══════════════════════════════════════════════════════════════════════════
    # FINDINGS INDEX
    # ══════════════════════════════════════════════════════════════════════════
    if flags:
        story.append(PageBreak())
        story.append(Paragraph("Findings Index", S["h2"]))
        story.append(HR(ACCENT, 1))

        idx_data = [["#", "Severity", "Finding Title", "Type", "Risk", "Review"]]
        for i, flag in enumerate(flags, 1):
            risk = f"{flag.risk_score}/10" if flag.risk_score is not None else "—"
            idx_data.append([
                str(i),
                sev_pill(flag.severity),
                Paragraph(flag.title[:65] + ("…" if len(flag.title) > 65 else ""), S["small"]),
                Paragraph(_FLAG_LABELS.get(flag.flag_type or "", flag.flag_type or "—"), S["small"]),
                risk,
                (flag.reviewer_status or "pending").capitalize(),
            ])
        idx_table = Table(idx_data, colWidths=[10*mm, 22*mm, 75*mm, 30*mm, 14*mm, 18*mm])
        idx_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
            ("GRID", (0, 0), (-1, -1), 0.3, RULE_GREY),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (4, 0), (5, -1), "CENTER"),
        ]))
        story.append(idx_table)

    # ══════════════════════════════════════════════════════════════════════════
    # FINDING DETAILS
    # ══════════════════════════════════════════════════════════════════════════
    if flags:
        story.append(PageBreak())
        story.append(Paragraph("Finding Details", S["h2"]))
        story.append(HR(ACCENT, 1))

        # Group by task type for organisation
        task_type_order = ["template_comparison", "vendor_diff", "law_validation", "checklist_validation"]
        grouped: dict[str, list] = {t: [] for t in task_type_order}
        for flag in flags:
            # Determine which task type this flag came from by flag_type prefix
            if flag.flag_type in ("template_deviation", "clause_added", "clause_missing"):
                grouped["template_comparison"].append(flag)
            elif flag.flag_type in ("vendor_redline",):
                grouped["vendor_diff"].append(flag)
            elif flag.flag_type in ("law_violation", "law_at_risk"):
                grouped["law_validation"].append(flag)
            elif flag.flag_type in ("checklist_violation", "checklist_fail", "checklist_not_found"):
                grouped["checklist_validation"].append(flag)
            else:
                grouped["template_comparison"].append(flag)

        global_i = 1
        for task_type in task_type_order:
            group_flags = grouped[task_type]
            if not group_flags:
                continue

            story.append(Spacer(1, 4*mm))
            # Section header
            section_header = Table(
                [[Paragraph(_TASK_LABELS.get(task_type, task_type), ParagraphStyle(
                    "SH", fontSize=11, fontName="Helvetica-Bold", textColor=colors.white
                ))]],
                colWidths=[165*mm],
            )
            section_header.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(section_header)
            story.append(Spacer(1, 2*mm))

            for flag in group_flags:
                sev_hex = _SEVERITY_COLOR.get(flag.severity, "#888888")
                sev_bg = colors.HexColor({
                    "critical": "#fdf2f2", "high": "#fef6ee",
                    "medium": "#fefdf0", "low": "#f0faf4", "info": "#eaf4fb",
                }.get(flag.severity, "#f8f9fa"))

                # Finding header block
                header_data = [[
                    Paragraph(
                        f'<font color="{sev_hex}"><b>[{flag.severity.upper()}]</b></font>  '
                        f'<b>Finding #{global_i}: {flag.title}</b>',
                        ParagraphStyle("FH", fontSize=9.5, leading=13)
                    )
                ]]
                header_table = Table(header_data, colWidths=[165*mm])
                header_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), sev_bg),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor(sev_hex)),
                ]))

                # Meta row
                meta_items = []
                meta_items.append(f"Type: {_FLAG_LABELS.get(flag.flag_type or '', flag.flag_type or '—')}")
                if flag.risk_score is not None:
                    meta_items.append(f"Risk Score: {flag.risk_score}/10")
                if flag.confidence is not None:
                    meta_items.append(f"Confidence: {flag.confidence:.0%}")
                meta_items.append(f"Review: {(flag.reviewer_status or 'pending').capitalize()}")
                if flag.law_act_name:
                    law_ref = flag.law_act_name
                    if flag.law_section_number:
                        law_ref += f", §{flag.law_section_number}"
                    meta_items.append(f"Law Ref: {law_ref}")

                meta_para = Paragraph("  |  ".join(meta_items), S["label"])

                # Body
                body_items = [
                    Spacer(1, 2),
                    Paragraph("<b>Description:</b>", S["label"]),
                    Paragraph(flag.description or "—", S["body"]),
                ]
                if flag.recommendation:
                    body_items += [
                        Spacer(1, 2),
                        Paragraph("<b>Recommendation:</b>", S["label"]),
                        Paragraph(flag.recommendation, S["body"]),
                    ]
                if flag.law_retrieved_text:
                    body_items += [
                        Spacer(1, 2),
                        Paragraph("<b>Relevant Law Text:</b>", S["label"]),
                        Paragraph(flag.law_retrieved_text[:400] + ("…" if len(flag.law_retrieved_text) > 400 else ""), S["small"]),
                    ]
                if flag.reviewer_note:
                    body_items += [
                        Spacer(1, 2),
                        Paragraph("<b>Reviewer Note:</b>", S["label"]),
                        Paragraph(flag.reviewer_note, S["body"]),
                    ]

                finding_block = KeepTogether([
                    header_table,
                    meta_para,
                    Spacer(1, 1),
                    *body_items,
                    Spacer(1, 4*mm),
                    HR(),
                ])
                story.append(finding_block)
                global_i += 1

    # ══════════════════════════════════════════════════════════════════════════
    # RISK REGISTER (critical + high only)
    # ══════════════════════════════════════════════════════════════════════════
    high_risk = [f for f in flags if f.severity in ("critical", "high")]
    if high_risk:
        story.append(PageBreak())
        story.append(Paragraph("Risk Register", S["h2"]))
        story.append(HR(colors.HexColor("#c0392b"), 1))
        story.append(Paragraph(
            "The following findings represent the highest-priority items that must be resolved "
            "before this contract can be safely executed. Items are ordered by severity.",
            S["body"],
        ))
        story.append(Spacer(1, 4*mm))

        risk_data = [["#", "Severity", "Finding", "Risk Score", "Recommendation", "Review Status"]]
        for i, flag in enumerate(high_risk, 1):
            risk_data.append([
                str(i),
                sev_pill(flag.severity),
                Paragraph(flag.title[:70], S["small"]),
                f"{flag.risk_score}/10" if flag.risk_score else "—",
                Paragraph((flag.recommendation or "—")[:120], S["small"]),
                (flag.reviewer_status or "pending").capitalize(),
            ])
        risk_table = Table(risk_data, colWidths=[10*mm, 20*mm, 55*mm, 16*mm, 50*mm, 18*mm])
        risk_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#922b21")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fdf2f2")]),
            ("GRID", (0, 0), (-1, -1), 0.4, RULE_GREY),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (3, 0), (3, -1), "CENTER"),
            ("ALIGN", (5, 0), (5, -1), "CENTER"),
        ]))
        story.append(risk_table)

    doc.build(story)
    return buffer.getvalue()
