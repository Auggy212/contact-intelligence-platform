"""
Generate 3 sample Indian contract PDFs for platform demo testing.

File A (Role A): Master Service Agreement — Company Template
File B (Role B): Vendor Proposed Contract — same MSA with unfavourable changes
File C (Role C): Vendor Redline — further vendor edits marked as changes

Run from backend/:
    python tests/fixtures/generate_test_contracts.py
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

OUT_DIR = Path(__file__).parent / "contracts"
OUT_DIR.mkdir(exist_ok=True)

W, H = A4
MARGIN = 2.2 * cm

# ── Shared style setup ────────────────────────────────────────────────────────

def _styles(accent=colors.HexColor("#1a3c6e")):
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"],
            fontSize=16, textColor=accent, spaceAfter=6, alignment=TA_CENTER),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"],
            fontSize=10, textColor=colors.grey, spaceAfter=14, alignment=TA_CENTER),
        "h1": ParagraphStyle("h1", parent=base["Heading1"],
            fontSize=11, textColor=accent, spaceBefore=14, spaceAfter=4,
            borderPad=2),
        "h2": ParagraphStyle("h2", parent=base["Heading2"],
            fontSize=10, textColor=accent, spaceBefore=8, spaceAfter=3),
        "body": ParagraphStyle("body", parent=base["Normal"],
            fontSize=9, leading=14, spaceAfter=6, alignment=TA_JUSTIFY),
        "clause": ParagraphStyle("clause", parent=base["Normal"],
            fontSize=9, leading=14, spaceAfter=5, leftIndent=12, alignment=TA_JUSTIFY),
        "redline_add": ParagraphStyle("redline_add", parent=base["Normal"],
            fontSize=9, leading=14, spaceAfter=5, leftIndent=12,
            textColor=colors.HexColor("#006400"), alignment=TA_JUSTIFY),
        "redline_del": ParagraphStyle("redline_del", parent=base["Normal"],
            fontSize=9, leading=14, spaceAfter=5, leftIndent=12,
            textColor=colors.red, alignment=TA_JUSTIFY),
        "label": ParagraphStyle("label", parent=base["Normal"],
            fontSize=8, textColor=colors.grey, spaceAfter=2),
        "footer": ParagraphStyle("footer", parent=base["Normal"],
            fontSize=7, textColor=colors.grey, alignment=TA_CENTER),
        "note": ParagraphStyle("note", parent=base["Normal"],
            fontSize=8, textColor=colors.HexColor("#8B6914"),
            leftIndent=10, spaceAfter=6),
    }


def _header(story, s, doc_type, file_role, badge_color):
    story.append(Paragraph("CONTRACT INTELLIGENCE PLATFORM", s["subtitle"]))
    story.append(Paragraph("Master Service Agreement", s["title"]))

    badge_data = [[
        Paragraph(f"<b>{doc_type}</b>", ParagraphStyle("b", fontSize=9,
            textColor=colors.white, alignment=TA_CENTER)),
        Paragraph(f"<b>File Role: {file_role}</b>", ParagraphStyle("b", fontSize=9,
            textColor=colors.white, alignment=TA_CENTER)),
    ]]
    badge = Table(badge_data, colWidths=[8*cm, 8*cm])
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), badge_color),
        ("BACKGROUND", (1,0), (1,0), colors.HexColor("#444444")),
        ("ROUNDEDCORNERS", [4]),
        ("PADDING", (0,0), (-1,-1), 6),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(badge)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5,
        color=badge_color, spaceAfter=10))


def _parties_table(story, s, vendor_name, vendor_addr, company_name, company_addr):
    data = [
        [Paragraph("<b>SERVICE PROVIDER (Vendor)</b>", s["label"]),
         Paragraph("<b>CLIENT (Company)</b>", s["label"])],
        [Paragraph(vendor_name, s["body"]),
         Paragraph(company_name, s["body"])],
        [Paragraph(vendor_addr, s["clause"]),
         Paragraph(company_addr, s["clause"])],
    ]
    t = Table(data, colWidths=[8.5*cm, 8.5*cm])
    t.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.5, colors.grey),
        ("INNERGRID", (0,0), (-1,-1), 0.25, colors.lightgrey),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f0f4f8")),
        ("PADDING", (0,0), (-1,-1), 6),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))


def _sig_table(story, s):
    data = [
        [Paragraph("<b>FOR SERVICE PROVIDER</b>", s["label"]),
         Paragraph("<b>FOR CLIENT</b>", s["label"])],
        [Paragraph("Authorised Signatory", s["clause"]),
         Paragraph("Authorised Signatory", s["clause"])],
        [Paragraph("Name: _______________________", s["clause"]),
         Paragraph("Name: _______________________", s["clause"])],
        [Paragraph("Designation: ________________", s["clause"]),
         Paragraph("Designation: ________________", s["clause"])],
        [Paragraph("Date: _______________________", s["clause"]),
         Paragraph("Date: _______________________", s["clause"])],
        [Paragraph("Place: ______________________", s["clause"]),
         Paragraph("Place: ______________________", s["clause"])],
    ]
    t = Table(data, colWidths=[8.5*cm, 8.5*cm])
    t.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.5, colors.grey),
        ("LINEBELOW", (0,0), (-1,0), 0.5, colors.grey),
        ("PADDING", (0,0), (-1,-1), 6),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(t)


# =============================================================================
# FILE A — Company Master Template (the gold standard)
# =============================================================================

def generate_file_a():
    s = _styles(accent=colors.HexColor("#1a3c6e"))
    path = OUT_DIR / "FILE_A_Company_Template_MSA.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN)

    story = []
    _header(story, s,
        "COMPANY MASTER TEMPLATE — UPLOAD AS FILE ROLE A",
        "A (Template / Gold Standard)",
        colors.HexColor("#1a3c6e"))

    story.append(Paragraph(
        "This document is the company's standard Master Service Agreement template. "
        "It represents the preferred contractual position. Upload this as <b>File Role A</b> "
        "when creating a new project.",
        s["note"]))

    story.append(Paragraph("1. PARTIES", s["h1"]))
    _parties_table(story, s,
        "TechVendor Solutions Private Limited",
        "CIN: U72900MH2018PTC123456\n412, Pinnacle Business Park,\nAndheri East, Mumbai – 400 093\nGSTIN: 27AAACT1234C1Z5",
        "Meridian Enterprises Private Limited",
        "CIN: U74999MH2010PTC200001\n8th Floor, One BKC Tower,\nBandra Kurla Complex, Mumbai – 400 051\nGSTIN: 27AAACM5678D1Z2")

    story.append(Paragraph("2. DEFINITIONS", s["h1"]))
    definitions = [
        (1, "<b>\"Agreement\"</b> means this Master Service Agreement including all Schedules and annexures."),
        (2, "<b>\"Services\"</b> means the software development, maintenance, and consulting services described in Schedule 1."),
        (3, "<b>\"Confidential Information\"</b> means all non-public technical, commercial, and financial information disclosed by either Party."),
        (4, "<b>\"Intellectual Property\"</b> means all patents, copyrights, trademarks, trade secrets, and other proprietary rights."),
        (5, "<b>\"Force Majeure Event\"</b> means any event beyond the reasonable control of a Party, including acts of God, war, pandemic, or government action."),
    ]
    for num, defn in definitions:
        story.append(Paragraph(f"2.{num}  {defn}", s["clause"]))

    story.append(Paragraph("3. TERM AND COMMENCEMENT", s["h1"]))
    story.append(Paragraph(
        "3.1  This Agreement shall commence on the Effective Date and shall remain in force for a period of <b>twenty-four (24) months</b>, "
        "unless earlier terminated in accordance with Clause 13.",
        s["clause"]))
    story.append(Paragraph(
        "3.2  This Agreement shall be deemed effective from the date of execution by both Parties (<b>\"Effective Date\"</b>: 01 June 2026).",
        s["clause"]))
    story.append(Paragraph(
        "3.3  Upon expiry, this Agreement may be renewed by mutual written consent for successive periods of twelve (12) months each.",
        s["clause"]))

    story.append(Paragraph("4. SCOPE OF SERVICES", s["h1"]))
    story.append(Paragraph(
        "4.1  The Vendor shall provide the Services as detailed in Schedule 1 attached hereto. Any modification to the scope shall require "
        "a written Change Order executed by authorised representatives of both Parties.",
        s["clause"]))
    story.append(Paragraph(
        "4.2  The Vendor shall assign a dedicated Project Manager who shall be the single point of contact for all communications relating to delivery.",
        s["clause"]))

    story.append(Paragraph("5. PAYMENT TERMS", s["h1"]))
    story.append(Paragraph(
        "5.1  The Client shall pay the Vendor the fees set out in Schedule 2 within <b>thirty (30) days</b> of receipt of a valid GST invoice.",
        s["clause"]))
    story.append(Paragraph(
        "5.2  Advance payment shall not exceed <b>ten percent (10%)</b> of the total contract value.",
        s["clause"]))
    story.append(Paragraph(
        "5.3  The total contract value shall not exceed <b>Indian Rupees Fifty Lakhs (₹50,00,000)</b> excluding applicable taxes.",
        s["clause"]))
    story.append(Paragraph(
        "5.4  Late payments shall attract interest at the rate prescribed under the Micro, Small and Medium Enterprises Development "
        "Act, 2006 (MSMED Act) — currently three (3) times the bank rate notified by the Reserve Bank of India.",
        s["clause"]))
    story.append(Paragraph(
        "5.5  All invoices shall include valid GSTIN of both Parties and comply with the GST Act, 2017.",
        s["clause"]))

    story.append(Paragraph("6. INTELLECTUAL PROPERTY RIGHTS", s["h1"]))
    story.append(Paragraph(
        "6.1  All Intellectual Property created by the Vendor specifically for the Client under this Agreement shall vest exclusively "
        "in the Client upon full payment of the applicable fees.",
        s["clause"]))
    story.append(Paragraph(
        "6.2  Pre-existing IP of either Party shall remain the sole property of that Party. The Vendor grants the Client a "
        "non-exclusive, royalty-free licence to use Vendor's pre-existing IP solely to the extent necessary to enjoy the Services.",
        s["clause"]))

    story.append(Paragraph("7. CONFIDENTIALITY", s["h1"]))
    story.append(Paragraph(
        "7.1  Each Party agrees to keep the other Party's Confidential Information strictly confidential and not to disclose it "
        "to any third party without prior written consent, during the term of this Agreement and for a period of <b>three (3) years</b> thereafter.",
        s["clause"]))
    story.append(Paragraph(
        "7.2  Confidentiality obligations shall not apply to information that: (a) is or becomes publicly available through no breach "
        "of this Agreement; (b) is independently developed; or (c) is required to be disclosed by law or court order.",
        s["clause"]))

    story.append(Paragraph("8. DATA PROTECTION", s["h1"]))
    story.append(Paragraph(
        "8.1  The Vendor shall process all personal data in compliance with the Information Technology (Amendment) Act, 2008 and "
        "the Digital Personal Data Protection Act, 2023.",
        s["clause"]))
    story.append(Paragraph(
        "8.2  The Vendor shall implement appropriate technical and organisational security measures to protect personal data "
        "against unauthorised access, loss, or destruction.",
        s["clause"]))

    story.append(Paragraph("9. LIABILITY AND INDEMNIFICATION", s["h1"]))
    story.append(Paragraph(
        "9.1  <b>Limitation of Liability:</b> The aggregate liability of either Party under this Agreement shall not exceed "
        "the total fees paid by the Client in the <b>twelve (12) months</b> immediately preceding the event giving rise to the claim.",
        s["clause"]))
    story.append(Paragraph(
        "9.2  Neither Party shall be liable for indirect, consequential, special, or punitive damages, even if advised of the possibility.",
        s["clause"]))
    story.append(Paragraph(
        "9.3  The Vendor shall indemnify and hold harmless the Client against any third-party claims arising out of the Vendor's "
        "gross negligence, wilful misconduct, or infringement of third-party intellectual property rights.",
        s["clause"]))

    story.append(Paragraph("10. REPRESENTATIONS AND WARRANTIES", s["h1"]))
    story.append(Paragraph(
        "10.1  The Vendor warrants that: (a) it has full authority to enter into this Agreement; (b) the Services shall be performed "
        "by qualified professionals; (c) the deliverables shall be free from material defects for ninety (90) days from delivery.",
        s["clause"]))

    story.append(Paragraph("11. FORCE MAJEURE", s["h1"]))
    story.append(Paragraph(
        "11.1  Neither Party shall be liable for delay or failure in performance resulting from a Force Majeure Event, provided "
        "the affected Party notifies the other in writing within <b>seven (7) days</b> of the occurrence.",
        s["clause"]))
    story.append(Paragraph(
        "11.2  If a Force Majeure Event continues for more than sixty (60) days, either Party may terminate this Agreement "
        "by giving thirty (30) days' written notice without any liability.",
        s["clause"]))

    story.append(Paragraph("12. DISPUTE RESOLUTION", s["h1"]))
    story.append(Paragraph(
        "12.1  The Parties shall first attempt to resolve any dispute through good-faith negotiation within thirty (30) days "
        "of written notice of the dispute.",
        s["clause"]))
    story.append(Paragraph(
        "12.2  If unresolved, disputes shall be referred to arbitration under the Arbitration and Conciliation Act, 1996 "
        "by a sole arbitrator mutually appointed by the Parties.",
        s["clause"]))
    story.append(Paragraph(
        "12.3  The seat of arbitration shall be <b>Mumbai</b>. The language of arbitration shall be English.",
        s["clause"]))
    story.append(Paragraph(
        "12.4  This Agreement shall be governed by and construed in accordance with the laws of India. "
        "Subject to the arbitration clause, the courts at <b>Mumbai</b> shall have exclusive jurisdiction.",
        s["clause"]))

    story.append(Paragraph("13. TERMINATION", s["h1"]))
    story.append(Paragraph(
        "13.1  Either Party may terminate this Agreement without cause by providing <b>sixty (60) days'</b> prior written notice.",
        s["clause"]))
    story.append(Paragraph(
        "13.2  Either Party may terminate immediately upon written notice if the other Party: (a) commits a material breach "
        "and fails to remedy it within thirty (30) days of notice; (b) becomes insolvent or enters liquidation.",
        s["clause"]))
    story.append(Paragraph(
        "13.3  Upon termination, the Vendor shall deliver all Client data and deliverables within <b>fifteen (15) days</b> "
        "and permanently delete all copies of Client Confidential Information.",
        s["clause"]))

    story.append(Paragraph("14. GENERAL PROVISIONS", s["h1"]))
    story.append(Paragraph(
        "14.1  <b>Entire Agreement:</b> This Agreement constitutes the entire agreement between the Parties and supersedes all prior negotiations.",
        s["clause"]))
    story.append(Paragraph(
        "14.2  <b>Amendments:</b> No amendment shall be valid unless in writing and signed by authorised representatives of both Parties.",
        s["clause"]))
    story.append(Paragraph(
        "14.3  <b>Severability:</b> If any provision is found invalid or unenforceable, the remaining provisions shall continue in full force.",
        s["clause"]))
    story.append(Paragraph(
        "14.4  <b>Notices:</b> All notices shall be in writing and delivered by email (with read receipt) or registered post to the addresses above.",
        s["clause"]))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=10))
    story.append(Paragraph("SIGNATURES", s["h1"]))
    _sig_table(story, s)

    doc.build(story)
    print(f"  Generated: {path.name}")
    return path


# =============================================================================
# FILE B — Vendor Proposed Contract (unfavourable deviations from template)
# =============================================================================

def generate_file_b():
    s = _styles(accent=colors.HexColor("#7B3F00"))
    path = OUT_DIR / "FILE_B_Vendor_Proposed_Contract.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN)

    story = []
    _header(story, s,
        "VENDOR PROPOSED CONTRACT — UPLOAD AS FILE ROLE B",
        "B (Vendor Proposed / For Review)",
        colors.HexColor("#7B3F00"))

    story.append(Paragraph(
        "⚠  This is the vendor's proposed version of the MSA. It contains several deviations from the company template "
        "that the AI will detect and flag. Upload this as <b>File Role B</b> (Proposed Contract).",
        s["note"]))

    story.append(Paragraph("1. PARTIES", s["h1"]))
    _parties_table(story, s,
        "TechVendor Solutions Private Limited",
        "CIN: U72900MH2018PTC123456\n412, Pinnacle Business Park,\nAndheri East, Mumbai – 400 093\nGSTIN: 27AAACT1234C1Z5",
        "Meridian Enterprises Private Limited",
        "CIN: U74999MH2010PTC200001\n8th Floor, One BKC Tower,\nBandra Kurla Complex, Mumbai – 400 051\nGSTIN: 27AAACM5678D1Z2")

    story.append(Paragraph("2. DEFINITIONS", s["h1"]))
    for defn in [
        "<b>\"Agreement\"</b> means this Master Service Agreement including all Schedules and annexures.",
        "<b>\"Services\"</b> means the software development, maintenance, and consulting services described in Schedule 1.",
        "<b>\"Confidential Information\"</b> means all non-public technical, commercial, and financial information disclosed by either Party.",
        "<b>\"Intellectual Property\"</b> means all patents, copyrights, trademarks, trade secrets, and other proprietary rights.",
    ]:
        story.append(Paragraph(defn, s["clause"]))

    # DEVIATION 1: Term changed from 24 months to 48 months (too long)
    story.append(Paragraph("3. TERM AND COMMENCEMENT", s["h1"]))
    story.append(Paragraph(
        "3.1  This Agreement shall commence on the Effective Date and shall remain in force for a period of <b>forty-eight (48) months</b>, "
        "unless earlier terminated in accordance with Clause 13.",
        s["clause"]))
    story.append(Paragraph(
        "⚡ [DEVIATION: Term extended from 24 to 48 months — exceeds company standard of 24 months]",
        s["note"]))
    story.append(Paragraph(
        "3.2  This Agreement shall be deemed effective from the date of execution by both Parties (<b>\"Effective Date\"</b>: 01 June 2026).",
        s["clause"]))

    story.append(Paragraph("4. SCOPE OF SERVICES", s["h1"]))
    story.append(Paragraph(
        "4.1  The Vendor shall provide the Services as detailed in Schedule 1 attached hereto. Any modification to the scope shall require "
        "a written Change Order executed by authorised representatives of both Parties.",
        s["clause"]))

    # DEVIATION 2: Payment terms extended from 30 to 90 days
    story.append(Paragraph("5. PAYMENT TERMS", s["h1"]))
    story.append(Paragraph(
        "5.1  The Client shall pay the Vendor the fees set out in Schedule 2 within <b>ninety (90) days</b> of receipt of a valid GST invoice.",
        s["clause"]))
    story.append(Paragraph(
        "⚡ [DEVIATION: Payment terms extended from 30 to 90 days — violates MSMED Act for MSME vendors]",
        s["note"]))
    # DEVIATION 3: Advance payment increased from 10% to 30%
    story.append(Paragraph(
        "5.2  Advance payment shall not exceed <b>thirty percent (30%)</b> of the total contract value.",
        s["clause"]))
    story.append(Paragraph(
        "⚡ [DEVIATION: Advance payment cap increased from 10% to 30% — exceeds company policy]",
        s["note"]))
    story.append(Paragraph(
        "5.3  The total contract value shall not exceed <b>Indian Rupees One Crore (₹1,00,00,000)</b> excluding applicable taxes.",
        s["clause"]))
    story.append(Paragraph(
        "⚡ [DEVIATION: Contract value cap doubled from ₹50L to ₹1Cr — requires Board approval]",
        s["note"]))
    story.append(Paragraph(
        "5.4  All invoices shall include valid GSTIN of both Parties and comply with the GST Act, 2017.",
        s["clause"]))

    story.append(Paragraph("6. INTELLECTUAL PROPERTY RIGHTS", s["h1"]))
    # DEVIATION 4: IP ownership reversed — vendor retains IP
    story.append(Paragraph(
        "6.1  All Intellectual Property created by the Vendor under this Agreement shall remain the exclusive property of the Vendor. "
        "The Client is granted a non-exclusive, non-transferable licence to use the deliverables solely for its internal business purposes.",
        s["clause"]))
    story.append(Paragraph(
        "⚡ [CRITICAL DEVIATION: IP ownership reversed — Client loses ownership of all custom-built deliverables]",
        s["note"]))

    story.append(Paragraph("7. CONFIDENTIALITY", s["h1"]))
    # DEVIATION 5: Confidentiality period reduced from 3 years to 1 year
    story.append(Paragraph(
        "7.1  Each Party agrees to keep the other Party's Confidential Information strictly confidential and not to disclose it "
        "to any third party without prior written consent, during the term of this Agreement and for a period of <b>one (1) year</b> thereafter.",
        s["clause"]))
    story.append(Paragraph(
        "⚡ [DEVIATION: Confidentiality period reduced from 3 years to 1 year — inadequate protection]",
        s["note"]))

    story.append(Paragraph("8. DATA PROTECTION", s["h1"]))
    story.append(Paragraph(
        "8.1  The Vendor shall process all personal data in compliance with the Information Technology (Amendment) Act, 2008.",
        s["clause"]))
    story.append(Paragraph(
        "⚡ [DEVIATION: Digital Personal Data Protection Act 2023 reference removed — non-compliant with current law]",
        s["note"]))

    story.append(Paragraph("9. LIABILITY AND INDEMNIFICATION", s["h1"]))
    # DEVIATION 6: Liability cap removed entirely
    story.append(Paragraph(
        "9.1  The Vendor's liability under this Agreement shall be unlimited.",
        s["clause"]))
    story.append(Paragraph(
        "⚡ [DEVIATION: Liability cap clause completely removed — unacceptable commercial risk for vendor]",
        s["note"]))
    story.append(Paragraph(
        "9.2  The Client shall indemnify the Vendor against any and all claims arising out of the Client's use of the deliverables.",
        s["clause"]))
    story.append(Paragraph(
        "⚡ [DEVIATION: Indemnification reversed — Client now indemnifies Vendor instead of the other way around]",
        s["note"]))

    story.append(Paragraph("10. FORCE MAJEURE", s["h1"]))
    story.append(Paragraph(
        "10.1  Neither Party shall be liable for delay or failure in performance resulting from a Force Majeure Event, provided "
        "the affected Party notifies the other in writing within <b>seven (7) days</b> of the occurrence.",
        s["clause"]))

    # DEVIATION 7: Jurisdiction changed from Mumbai to Delhi
    story.append(Paragraph("11. DISPUTE RESOLUTION", s["h1"]))
    story.append(Paragraph(
        "11.1  The Parties shall first attempt to resolve any dispute through good-faith negotiation within thirty (30) days.",
        s["clause"]))
    story.append(Paragraph(
        "11.2  This Agreement shall be governed by and construed in accordance with the laws of India. "
        "The courts at <b>New Delhi</b> shall have exclusive jurisdiction.",
        s["clause"]))
    story.append(Paragraph(
        "⚡ [DEVIATION: Jurisdiction changed from Mumbai to New Delhi — requires legal team approval]",
        s["note"]))

    # DEVIATION 8: Termination notice reduced from 60 days to 15 days
    story.append(Paragraph("12. TERMINATION", s["h1"]))
    story.append(Paragraph(
        "12.1  Either Party may terminate this Agreement without cause by providing <b>fifteen (15) days'</b> prior written notice.",
        s["clause"]))
    story.append(Paragraph(
        "⚡ [DEVIATION: Termination notice reduced from 60 days to 15 days — insufficient wind-down time]",
        s["note"]))
    story.append(Paragraph(
        "12.2  Upon termination, the Vendor shall deliver all Client data and deliverables within <b>thirty (30) days</b>.",
        s["clause"]))

    story.append(Paragraph("13. GENERAL PROVISIONS", s["h1"]))
    story.append(Paragraph(
        "13.1  <b>Entire Agreement:</b> This Agreement constitutes the entire agreement between the Parties.",
        s["clause"]))
    story.append(Paragraph(
        "13.2  <b>Amendments:</b> No amendment shall be valid unless in writing and signed by authorised representatives of both Parties.",
        s["clause"]))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=10))
    story.append(Paragraph("SIGNATURES", s["h1"]))
    _sig_table(story, s)

    doc.build(story)
    print(f"  Generated: {path.name}")
    return path


# =============================================================================
# FILE C — Vendor Redline (further edits on top of File B, shown as changes)
# =============================================================================

def generate_file_c():
    s = _styles(accent=colors.HexColor("#2d6a2d"))
    path = OUT_DIR / "FILE_C_Vendor_Redline.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN)

    story = []
    _header(story, s,
        "VENDOR REDLINE — UPLOAD AS FILE ROLE C",
        "C (Vendor Redline / Further Edits)",
        colors.HexColor("#2d6a2d"))

    story.append(Paragraph(
        "This is the vendor's redlined version — showing further edits made on top of File B. "
        "Red strikethrough = deleted text. Green underline = inserted text. "
        "Upload this as <b>File Role C</b> (Vendor Reply / Redline).",
        s["note"]))

    story.append(Paragraph("1. PARTIES", s["h1"]))
    _parties_table(story, s,
        "TechVendor Solutions Private Limited",
        "CIN: U72900MH2018PTC123456\n412, Pinnacle Business Park,\nAndheri East, Mumbai – 400 093",
        "Meridian Enterprises Private Limited",
        "CIN: U74999MH2010PTC200001\n8th Floor, One BKC Tower,\nBandra Kurla Complex, Mumbai – 400 051")

    story.append(Paragraph("3. TERM AND COMMENCEMENT", s["h1"]))
    story.append(Paragraph(
        "3.1  This Agreement shall commence on the Effective Date and shall remain in force for a period of",
        s["clause"]))
    story.append(Paragraph(
        '    <strike><font color="red">forty-eight (48) months</font></strike> '
        '<u><font color="green">thirty-six (36) months</font></u>, '
        "unless earlier terminated in accordance with Clause 12.",
        s["clause"]))
    story.append(Paragraph(
        "📝 Vendor partially conceded: reduced from 48 to 36 months (still above company's 24-month standard)",
        s["note"]))

    story.append(Paragraph("5. PAYMENT TERMS", s["h1"]))
    story.append(Paragraph(
        "5.1  The Client shall pay the Vendor the fees set out in Schedule 2 within",
        s["clause"]))
    story.append(Paragraph(
        '    <strike><font color="red">ninety (90) days</font></strike> '
        '<u><font color="green">forty-five (45) days</font></u> '
        "of receipt of a valid GST invoice.",
        s["clause"]))
    story.append(Paragraph(
        "📝 Vendor conceded partially: 90→45 days. Still exceeds company standard of 30 days.",
        s["note"]))

    story.append(Paragraph(
        "5.2  Advance payment shall not exceed <b>thirty percent (30%)</b> of the total contract value.",
        s["clause"]))
    story.append(Paragraph(
        "📝 No change to advance payment clause — vendor maintained 30% (company standard: 10%).",
        s["note"]))

    story.append(Paragraph(
        "5.3  The total contract value shall not exceed <b>Indian Rupees One Crore (₹1,00,00,000)</b> excluding taxes.",
        s["clause"]))

    story.append(Paragraph("5A. PENALTY FOR LATE PAYMENT [NEW CLAUSE — INSERTED BY VENDOR]", s["h1"]))
    story.append(Paragraph(
        '<u><font color="green">'
        "5A.1  In the event the Client fails to make payment within the stipulated period, the Client shall pay a penalty "
        "of two percent (2%) per month on the outstanding amount, compounded monthly, from the due date until actual payment."
        "</font></u>",
        s["redline_add"]))
    story.append(Paragraph(
        "📝 NEW clause inserted by vendor — 2% compounded monthly penalty is aggressive and unusual.",
        s["note"]))

    story.append(Paragraph("6. INTELLECTUAL PROPERTY RIGHTS", s["h1"]))
    story.append(Paragraph(
        '6.1  All Intellectual Property created by the Vendor under this Agreement shall remain the exclusive property of the Vendor. '
        'The Client is granted a non-exclusive, non-transferable licence to use the deliverables solely for its internal business purposes.',
        s["clause"]))
    story.append(Paragraph(
        "📝 IP clause unchanged from File B — vendor still retains all IP ownership.",
        s["note"]))

    story.append(Paragraph("7. CONFIDENTIALITY", s["h1"]))
    story.append(Paragraph(
        "7.1  Each Party agrees to keep the other Party's Confidential Information strictly confidential",
        s["clause"]))
    story.append(Paragraph(
        '    during the term of this Agreement and for a period of '
        '<strike><font color="red">one (1) year</font></strike> '
        '<u><font color="green">two (2) years</font></u> thereafter.',
        s["clause"]))
    story.append(Paragraph(
        "📝 Vendor increased from 1 to 2 years — still below company standard of 3 years.",
        s["note"]))

    story.append(Paragraph("9. LIABILITY AND INDEMNIFICATION", s["h1"]))
    story.append(Paragraph(
        '9.1  <strike><font color="red">The Vendor\'s liability under this Agreement shall be unlimited.</font></strike>',
        s["redline_del"]))
    story.append(Paragraph(
        '<u><font color="green">'
        "9.1  The aggregate liability of either Party under this Agreement shall not exceed the total fees paid by the Client "
        "in the six (6) months immediately preceding the event giving rise to the claim."
        "</font></u>",
        s["redline_add"]))
    story.append(Paragraph(
        "📝 Liability cap restored but set to 6 months fees (company standard: 12 months fees).",
        s["note"]))

    story.append(Paragraph("10. NON-SOLICITATION [NEW CLAUSE — INSERTED BY VENDOR]", s["h1"]))
    story.append(Paragraph(
        '<u><font color="green">'
        "10.1  The Client agrees that during the term of this Agreement and for a period of twenty-four (24) months thereafter, "
        "it shall not, directly or indirectly, solicit, hire, or engage any employee or contractor of the Vendor who was involved "
        "in the performance of Services under this Agreement."
        "</font></u>",
        s["redline_add"]))
    story.append(Paragraph(
        "📝 NEW non-solicitation clause — 24-month restriction is standard but should be reviewed by HR/Legal.",
        s["note"]))

    story.append(Paragraph("11. DISPUTE RESOLUTION", s["h1"]))
    story.append(Paragraph(
        "11.1  The Parties shall first attempt to resolve any dispute through good-faith negotiation within thirty (30) days.",
        s["clause"]))
    story.append(Paragraph(
        "11.2  This Agreement shall be governed by and construed in accordance with the laws of India. "
        "The courts at <b>New Delhi</b> shall have exclusive jurisdiction.",
        s["clause"]))
    story.append(Paragraph(
        "📝 Jurisdiction remains Delhi — unchanged from File B.",
        s["note"]))

    story.append(Paragraph("12. TERMINATION", s["h1"]))
    story.append(Paragraph(
        "12.1  Either Party may terminate this Agreement without cause by providing",
        s["clause"]))
    story.append(Paragraph(
        '    <strike><font color="red">fifteen (15) days\'</font></strike> '
        '<u><font color="green">thirty (30) days\'</font></u> '
        "prior written notice.",
        s["clause"]))
    story.append(Paragraph(
        "📝 Vendor increased from 15 to 30 days — still below company standard of 60 days.",
        s["note"]))

    story.append(Paragraph("13. LIMITATION ON CLASS ACTIONS [NEW CLAUSE — INSERTED BY VENDOR]", s["h1"]))
    story.append(Paragraph(
        '<u><font color="green">'
        "13.1  Each Party irrevocably waives any right to participate in a class action, collective action, or representative "
        "proceeding in connection with any dispute arising under this Agreement."
        "</font></u>",
        s["redline_add"]))
    story.append(Paragraph(
        "📝 NEW class action waiver — enforceability under Indian law is questionable; requires legal review.",
        s["note"]))

    story.append(Paragraph("14. GENERAL PROVISIONS", s["h1"]))
    story.append(Paragraph(
        "14.1  <b>Entire Agreement:</b> This Agreement constitutes the entire agreement between the Parties.",
        s["clause"]))
    story.append(Paragraph(
        "14.2  <b>Amendments:</b> No amendment shall be valid unless in writing and signed by authorised representatives of both Parties.",
        s["clause"]))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=10))
    story.append(Paragraph("SIGNATURES", s["h1"]))
    _sig_table(story, s)

    doc.build(story)
    print(f"  Generated: {path.name}")
    return path


# =============================================================================
# Summary README
# =============================================================================

def write_readme():
    readme = OUT_DIR / "README.md"
    readme.write_text("""# Test Contract PDFs

Three sample Indian Master Service Agreement PDFs for end-to-end platform testing.

## Files

| File | Upload As | Description |
|---|---|---|
| `FILE_A_Company_Template_MSA.pdf` | **File Role A** (Template) | Company's gold-standard MSA template — all clauses favourable |
| `FILE_B_Vendor_Proposed_Contract.pdf` | **File Role B** (Proposed) | Vendor's proposed version — 8 deliberate deviations from template |
| `FILE_C_Vendor_Redline.pdf` | **File Role C** (Redline) | Vendor's further edits — tracked changes shown in red/green |

## What the AI Should Detect

### Template Comparison (A vs B)
- Term extended: 24 → 48 months
- Payment terms: 30 → 90 days (MSMED Act violation)
- Advance payment cap: 10% → 30%
- Contract value: ₹50L → ₹1Cr
- IP ownership reversed (vendor retains all IP)
- Confidentiality period: 3 years → 1 year
- Liability cap removed entirely
- Indemnification reversed
- Jurisdiction changed: Mumbai → New Delhi
- Termination notice: 60 → 15 days

### Vendor Diff (B vs C changes)
- Term partially conceded: 48 → 36 months
- Payment terms partially conceded: 90 → 45 days
- New penalty clause inserted (2% compounded monthly)
- Confidentiality increased: 1 → 2 years
- Liability cap restored but at 6 months (company standard: 12 months)
- New non-solicitation clause (24 months)
- Termination notice increased: 15 → 30 days
- New class action waiver inserted

### Indian Law Validation
- 90-day payment terms violate MSMED Act (max 45 days for MSME vendors)
- Missing DPDP Act 2023 reference in data protection clause
- Class action waiver — questionable enforceability under Indian law

### Checklist Validation
- ✅ Agreement date present
- ❌ Term exceeds 36 months (rule: max 36 months)
- ❌ Governing court not Mumbai (rule: must be Mumbai)
- ❌ Payment terms exceed 30 days
- ❌ Advance payment exceeds 10%
- ❌ Contract value exceeds ₹50L threshold

## How to Test

1. Create a new project on the dashboard
2. Upload FILE_A as Role A (Template)
3. Upload FILE_B as Role B (Proposed)
4. Upload FILE_C as Role C (Vendor Reply)
5. Trigger all 4 analysis tasks
6. Review findings on the Analysis and Findings pages
""", encoding="utf-8")
    print(f"  Generated: {readme.name}")


if __name__ == "__main__":
    print("Generating test contract PDFs...")
    generate_file_a()
    generate_file_b()
    generate_file_c()
    write_readme()
    print(f"\\nDone. Files saved to: {OUT_DIR.resolve()}")
