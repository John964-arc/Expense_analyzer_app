"""
export_service.py
────────────────────────────────────────────────────────
Generates downloadable CSV and PDF reports from expense data.
PDF: produced with reportlab (pure-Python, no system deps).
CSV: produced with Python stdlib csv module.
"""
import io
import csv
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT


class ExportService:

    # ─── CSV ────────────────────────────────────────────────────────────────

    @staticmethod
    def generate_csv(expenses: list, month_label: str = '') -> io.BytesIO:
        """Return a BytesIO buffer containing a UTF-8 CSV of expenses."""
        buf = io.StringIO()
        writer = csv.writer(buf)

        writer.writerow(['AI Expense Analyzer Report', month_label])
        writer.writerow([])
        writer.writerow(['#', 'Date', 'Name', 'Category', 'Amount',
                         'Currency', 'Converted (INR)', 'Recurring', 'Description'])

        for i, e in enumerate(expenses, 1):
            writer.writerow([
                i,
                e.date.strftime('%Y-%m-%d') if e.date else '',
                e.name,
                e.category,
                f'{e.amount:.2f}',
                e.currency or 'INR',
                f'{e.converted_amount:.2f}' if e.converted_amount else '',
                'Yes' if e.is_recurring else 'No',
                e.description or '',
            ])

        writer.writerow([])
        total = sum(e.amount for e in expenses)
        writer.writerow(['', '', '', 'TOTAL', f'{total:.2f}'])

        # Category breakdown
        writer.writerow([])
        writer.writerow(['Category Breakdown'])
        cat_totals: dict = {}
        for e in expenses:
            cat_totals[e.category] = cat_totals.get(e.category, 0) + e.amount
        for cat, amt in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
            pct = (amt / total * 100) if total else 0
            writer.writerow([cat, f'{amt:.2f}', f'{pct:.1f}%'])

        bytes_buf = io.BytesIO(buf.getvalue().encode('utf-8-sig'))
        bytes_buf.seek(0)
        return bytes_buf

    # ─── PDF ────────────────────────────────────────────────────────────────

    @staticmethod
    def generate_pdf(expenses: list, username: str = 'User',
                     month_label: str = '', category_totals: dict = None) -> io.BytesIO:
        """Return a BytesIO buffer containing a styled PDF report."""
        buf = io.BytesIO()

        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            rightMargin=2 * cm, leftMargin=2 * cm,
            topMargin=2 * cm,   bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'Title2', parent=styles['Title'],
            fontSize=22, textColor=colors.HexColor('#6C63FF'),
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            'Subtitle', parent=styles['Normal'],
            fontSize=11, textColor=colors.HexColor('#888888'),
            spaceAfter=12,
        )
        section_style = ParagraphStyle(
            'Section', parent=styles['Heading2'],
            fontSize=13, textColor=colors.HexColor('#1E293B'),
            spaceBefore=16, spaceAfter=8,
        )
        cell_style = ParagraphStyle(
            'Cell', parent=styles['Normal'],
            fontSize=9, leading=12,
        )
        right_style = ParagraphStyle(
            'Right', parent=styles['Normal'],
            fontSize=9, alignment=TA_RIGHT,
        )

        story = []

        # ── Header ──────────────────────────────────────────────────────────
        story.append(Paragraph('AI Expense Analyzer', title_style))
        story.append(Paragraph(
            f'Expense Report — {month_label} | Generated for <b>{username}</b> | '
            f'{datetime.now().strftime("%d %b %Y, %H:%M")}',
            subtitle_style
        ))
        story.append(HRFlowable(width='100%', thickness=1,
                                color=colors.HexColor('#6C63FF'), spaceAfter=16))

        # ── Summary KPIs ────────────────────────────────────────────────────
        total = sum(e.amount for e in expenses)
        cats  = category_totals or {}
        top_cat = max(cats, key=cats.get) if cats else '—'

        kpi_data = [
            ['Total Spent', f'₹{total:,.2f}'],
            ['Transactions', str(len(expenses))],
            ['Top Category', top_cat],
            ['Report Period', month_label],
        ]
        kpi_table = Table(kpi_data, colWidths=[5 * cm, 8 * cm])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F7FF')),
            ('TEXTCOLOR',  (0, 0), (0, -1), colors.HexColor('#6C63FF')),
            ('FONTNAME',   (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE',   (0, 0), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1),
             [colors.HexColor('#F8F7FF'), colors.white]),
            ('GRID',       (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
            ('LEFTPADDING',  (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING',   (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 16))

        # ── Category Breakdown ──────────────────────────────────────────────
        if cats:
            story.append(Paragraph('Category Breakdown', section_style))
            cat_rows = [['Category', 'Amount', 'Share']]
            for cat, amt in sorted(cats.items(), key=lambda x: x[1], reverse=True):
                pct = (amt / total * 100) if total else 0
                cat_rows.append([
                    Paragraph(cat, cell_style),
                    Paragraph(f'₹{amt:,.2f}', right_style),
                    Paragraph(f'{pct:.1f}%', right_style),
                ])
            cat_table = Table(cat_rows, colWidths=[7 * cm, 5 * cm, 4 * cm])
            cat_table.setStyle(_table_style(header_color='#6C63FF'))
            story.append(cat_table)
            story.append(Spacer(1, 16))

        # ── Transaction List ─────────────────────────────────────────────────
        story.append(Paragraph('All Transactions', section_style))

        tx_rows = [['Date', 'Name', 'Category', 'Amount', 'Currency']]
        for e in expenses:
            tx_rows.append([
                Paragraph(e.date.strftime('%d %b %Y') if e.date else '—', cell_style),
                Paragraph(e.name[:40], cell_style),
                Paragraph(e.category, cell_style),
                Paragraph(f'₹{e.amount:,.2f}', right_style),
                Paragraph(e.currency or 'INR', cell_style),
            ])

        tx_table = Table(tx_rows, colWidths=[3 * cm, 7 * cm, 3.5 * cm, 2.5 * cm, 1.5 * cm],
                         repeatRows=1)
        tx_table.setStyle(_table_style(header_color='#1E293B'))
        story.append(tx_table)

        doc.build(story)
        buf.seek(0)
        return buf


def _table_style(header_color: str = '#1E293B') -> TableStyle:
    return TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor(header_color)),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.white),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#F8F7FF')]),
        ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor('#DDDDDD')),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ])
