from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether


def generate_report(filename: str, document_name: str, risks: list[dict], report_dir: str) -> str:
    Path(report_dir).mkdir(parents=True, exist_ok=True)
    path = str(Path(report_dir) / filename)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallNote", parent=styles["BodyText"], fontSize=8, leading=11, textColor="#4b5563"))

    safe_document_name = document_name if document_name.isascii() else "Uploaded document (Bangla filename retained in workspace)"
    story = [
        Paragraph("LEGAL COPILOT BD", styles["Title"]),
        Paragraph("Preliminary AI-Assisted Document Review Report", styles["Heading2"]),
        Spacer(1, 5 * mm),
        Paragraph(f"Document: {escape(safe_document_name)}", styles["BodyText"]),
        Paragraph("Jurisdiction: Bangladesh | Review status: Preliminary screening", styles["BodyText"]),
        Spacer(1, 5 * mm),
        Paragraph("Executive Summary", styles["Heading1"]),
        Paragraph(f"The screening returned {len(risks)} document-evidence risk signal(s). Each signal requires review in the context of the complete source document.", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Risk Findings", styles["Heading1"]),
    ]

    if not risks:
        story.append(Paragraph("No supported risk findings were returned by the current screening workflow. This does not establish that the document is risk-free.", styles["BodyText"]))

    for index, risk in enumerate(risks, 1):
        block = [
            Paragraph(f"{index}. {escape(str(risk.get('title', 'Risk finding')))} — {escape(str(risk.get('severity', 'unknown')).upper())}", styles["Heading2"]),
            Paragraph(f"Category: {escape(str(risk.get('category', 'Not specified')))} | Page: {escape(str(risk.get('page') or 'Not available'))}", styles["SmallNote"]),
            Paragraph(f"Explanation: {escape(str(risk.get('explanation', '')))}", styles["BodyText"]),
            Paragraph(f"Document evidence: {escape(str(risk.get('clause_excerpt', '')))}", styles["BodyText"]),
            Paragraph(f"Recommendation: {escape(str(risk.get('recommendation', '')))}", styles["BodyText"]),
            Paragraph(f"Evidence status: {escape(str(risk.get('evidence_status', 'document_evidence_only')))}", styles["SmallNote"]),
            Spacer(1, 4 * mm),
        ]
        story.append(KeepTogether(block))

    story.extend([
        Spacer(1, 3 * mm),
        Paragraph("Legal Authority and Verification Status", styles["Heading1"]),
        Paragraph(
            "No statutory citation is presented as verified in this memorandum. "
            "The current system has not completed official-source retrieval, amendment and "
            "commencement checks, repeal/status checks, or legal applicability verification. "
            "Document evidence matching is not legal citation verification.",
            styles["BodyText"],
        ),
        Spacer(1, 3 * mm),
        Paragraph(
            "Important: This is a preliminary AI-assisted screening report, not legal advice, "
            "a legal opinion, or a substitute for review by a qualified Bangladesh lawyer. "
            "The PDF generator currently uses standard ReportLab fonts; Bangla font embedding "
            "and scanned-document OCR are not yet included.",
            styles["SmallNote"],
        ),
    ])

    SimpleDocTemplate(
        path, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    ).build(story)
    return path
