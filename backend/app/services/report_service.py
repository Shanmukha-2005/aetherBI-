import io
import json
from datetime import datetime, timezone
from typing import Dict, Any
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.models.dataset import Dataset
from app.db.session import engine

def generate_executive_pdf_report(dataset: Dataset, user_name: str) -> io.BytesIO:
    """
    Constructs a branded, publication-grade Executive Intelligence Dossier in PDF format.
    Includes data health score, remediation audit trail, discovered relationships/facts,
    and profile metrics.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette (Modern Dark Slate / Emerald / Indigo)
    c_primary = colors.HexColor("#0f172a")      # Dark Slate 900
    c_accent = colors.HexColor("#4f46e5")       # Indigo 600
    c_emerald = colors.HexColor("#059669")      # Emerald 600
    c_light_bg = colors.HexColor("#f8fafc")     # Slate 50
    c_border = colors.HexColor("#e2e8f0")       # Slate 200
    c_text_dark = colors.HexColor("#1e293b")    # Slate 800
    c_text_muted = colors.HexColor("#64748b")   # Slate 500

    # Typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=c_primary,
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=c_text_muted,
        spaceAfter=12
    )
    h2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=c_accent,
        spaceBefore=14,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=c_text_dark
    )
    body_bold = ParagraphStyle(
        'BodyBoldCustom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=c_text_dark
    )
    badge_style = ParagraphStyle(
        'BadgeCustom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        textColor=c_emerald,
        alignment=1
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("AetherBI • Executive Intelligence Dossier", title_style))
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y • %H:%M UTC")
    story.append(Paragraph(f"Dataset: <b>{dataset.name}</b> | Generated for: <b>{user_name}</b> | Date: {date_str}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_accent, spaceAfter=14))

    # 2. Executive Summary Metrics Cards (Table)
    health_score = dataset.health_score or 100.0
    kpi_data = [
        [
            Paragraph("Health Score", body_style),
            Paragraph("Total Records", body_style),
            Paragraph("Total Attributes", body_style),
            Paragraph("Remediations", body_style)
        ],
        [
            Paragraph(f"{health_score:.1f}%", badge_style),
            Paragraph(f"{dataset.row_count:,}", ParagraphStyle('KpiVal', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, alignment=1, textColor=c_primary)),
            Paragraph(f"{dataset.column_count}", ParagraphStyle('KpiVal', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, alignment=1, textColor=c_primary)),
            Paragraph(f"{len(dataset.remediation_logs)}", ParagraphStyle('KpiVal', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, alignment=1, textColor=c_accent))
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[135, 135, 135, 135])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_light_bg),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # 3. Discovered Facts & Relationships Section
    story.append(Paragraph("1. Discovered Relationships & Analytical Facts", h2_style))
    if dataset.facts:
        facts_data = [[
            Paragraph("Category", body_bold),
            Paragraph("Key Finding & Strategic Impact", body_bold),
            Paragraph("Metric", body_bold)
        ]]
        for fact in dataset.facts[:6]:
            badge_text = fact.fact_type.replace('_', ' ').title()
            facts_data.append([
                Paragraph(f"<b>{badge_text}</b>", body_style),
                Paragraph(f"<b>{fact.title}</b><br/>{fact.description}", body_style),
                Paragraph(fact.metric_value or "-", ParagraphStyle('Pill', parent=body_bold, textColor=c_accent))
            ])
        facts_table = Table(facts_data, colWidths=[110, 350, 80])
        facts_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), c_light_bg),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, c_border),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(facts_table)
    else:
        story.append(Paragraph("No significant skew or correlation outliers detected.", body_style))
    story.append(Spacer(1, 14))

    # 4. Data Health & Remediation Audit Trail
    story.append(Paragraph("2. Autonomous Remediation Audit Trail", h2_style))
    if dataset.remediation_logs:
        remed_data = [[
            Paragraph("Attribute", body_bold),
            Paragraph("Anomaly Detected", body_bold),
            Paragraph("Strategy", body_bold),
            Paragraph("Technical Rationale", body_bold)
        ]]
        for log in dataset.remediation_logs[:8]:
            remed_data.append([
                Paragraph(log.column_name or "Global", body_bold),
                Paragraph(log.issue_type.replace('_', ' ').title(), body_style),
                Paragraph(f"<b>{log.resolution_strategy.replace('_', ' ').title()}</b>", ParagraphStyle('RStr', parent=body_style, textColor=c_emerald)),
                Paragraph(log.resolution_details or log.issue_description, body_style)
            ])
        remed_table = Table(remed_data, colWidths=[90, 110, 110, 230])
        remed_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), c_light_bg),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, c_border),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(remed_table)
    else:
        story.append(Paragraph("Clean dataset: Zero missing values or formatting anomalies required repair.", body_style))
    story.append(Spacer(1, 14))

    # 5. Schema & Profiling Overview
    story.append(Paragraph("3. Dataset Schema & Column Profiling", h2_style))
    columns_meta = json.loads(dataset.columns_meta or "[]")
    if columns_meta:
        meta_data = [[
            Paragraph("Column Name", body_bold),
            Paragraph("Inferred Type", body_bold),
            Paragraph("Distinct Values", body_bold),
            Paragraph("Null Values", body_bold)
        ]]
        for col in columns_meta[:10]:
            meta_data.append([
                Paragraph(f"<code>{col.get('name')}</code>", body_style),
                Paragraph(col.get('type', '').title(), body_style),
                Paragraph(str(col.get('unique_count', '-')), body_style),
                Paragraph(str(col.get('null_count', 0)), body_style)
            ])
        meta_table = Table(meta_data, colWidths=[180, 120, 120, 120])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), c_light_bg),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, c_border),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(meta_table)

    # 6. Sample Cleaned Data Records
    try:
        sample_df = pd.read_sql_query(f'SELECT * FROM "{dataset.physical_table_name}" LIMIT 4', con=engine)
        if not sample_df.empty:
            story.append(Spacer(1, 14))
            story.append(Paragraph("4. Sample Cleaned Data Records (Physical SQLite)", h2_style))
            cols_preview = list(sample_df.columns[:6])
            sample_data = [[Paragraph(f"<b>{c}</b>", body_style) for c in cols_preview]]
            for _, row in sample_df[cols_preview].iterrows():
                sample_data.append([Paragraph(str(val)[:20], body_style) for val in row])
            col_w = int(540 / len(cols_preview))
            sample_table = Table(sample_data, colWidths=[col_w] * len(cols_preview))
            sample_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), c_light_bg),
                ('GRID', (0, 0), (-1, -1), 0.5, c_border),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(sample_table)
    except Exception:
        pass

    # Build the document
    doc.build(story)
    buffer.seek(0)
    return buffer
