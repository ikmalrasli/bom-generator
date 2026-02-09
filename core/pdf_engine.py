"""core/pdf_engine.py

PDF generation and merging pipeline.

This module implements the 3-step pipeline described in AGENTS.MD:
1) Generate a Summary Table PDF (ReportLab)
2) Generate an Item Header PDF for each BOM item (ReportLab)
3) Merge: [Cover (optional)] + [Summary] + ([Header] + [Datasheet])... (PyMuPDF)

Design goals:
- Keep this independent from the UI framework
- Preserve datasheet vector quality by *inserting PDFs* (not rasterizing)
- Produce a single professional output PDF
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.data_handler import BOMItem


class PDFEngine:
    """High-level PDF generator/merger."""

    def build_summary_table_pdf(self, items: List[BOMItem], out_pdf_path: str) -> None:
        """Create a one-page (or multi-page) summary table."""

        # ReportLab uses a document template that writes directly to `out_pdf_path`.
        doc = SimpleDocTemplate(out_pdf_path, pagesize=LETTER)
        styles = getSampleStyleSheet()

        # Table header row.
        data = [["Item", "Model", "Description", "Make", "Qty"]]
        for i in items:
            data.append([
                str(i.index),
                i.model,
                i.description,
                i.make,
                str(i.quantity),
            ])

        # Build a readable, engineering-style grid.
        table = Table(data, repeatRows=1, colWidths=[40, 120, 220, 110, 50])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0078D4")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        story = [
            Paragraph("Bill of Materials", styles["Title"]),
            Spacer(1, 10),
            table,
        ]

        doc.build(story)

    def build_item_header_pdf(self, item: BOMItem, out_pdf_path: str) -> None:
        """Create a single-page header inserted before each datasheet."""

        c = canvas.Canvas(out_pdf_path, pagesize=LETTER)
        page_width, page_height = LETTER

        styles = getSampleStyleSheet()

        left_margin = 1.0 * inch
        right_margin = 1.0 * inch
        available_width = page_width - left_margin - right_margin

        title_style = ParagraphStyle(
            "item_header_title",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            alignment=TA_LEFT,
        )

        detail_style = ParagraphStyle(
            "item_header_detail",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
        )

        # Keep the header page intentionally simple and consistent.
        # This acts as a separator between datasheets in the final merged PDF.
        title_text = f"Item {item.index}: {item.description or '(No Description)'}"
        make_text = f"Make: {item.make or '-'}"
        model_text = f"Model: {item.model or '-'}"
        qty_text = f"Qty: {item.quantity}"

        blocks = [
            Paragraph(title_text, title_style),
            Paragraph(make_text, detail_style),
            Paragraph(model_text, detail_style),
            Paragraph(qty_text, detail_style),
        ]

        heights: List[float] = []
        for p in blocks:
            _, h = p.wrap(available_width, page_height)
            heights.append(h)

        gap = 6
        total_height = sum(heights) + gap * (len(blocks) - 1)

        # Vertically center the entire block.
        y = (page_height + total_height) / 2
        for p, h in zip(blocks, heights):
            y -= h
            p.drawOn(c, left_margin, y)
            y -= gap

        c.showPage()
        c.save()

    def merge_bom(
        self,
        *,
        cover_pdf_path: Optional[str],
        items: List[BOMItem],
        output_pdf_path: str,
    ) -> None:
        """Create final merged BOM package.

        Raises:
        - FileNotFoundError if any referenced PDF does not exist
        - ValueError if items list is empty
        """

        if not items:
            raise ValueError("No items to generate.")

        # Validate file existence up-front so the user doesn't wait and then fail.
        if cover_pdf_path:
            if not Path(cover_pdf_path).is_file():
                raise FileNotFoundError(f"Cover PDF not found: {cover_pdf_path}")

        for it in items:
            if not it.datasheet_path:
                raise FileNotFoundError(f"Missing datasheet for Item {it.index}: {asdict(it)}")
            if not Path(it.datasheet_path).is_file():
                raise FileNotFoundError(f"Datasheet not found for Item {it.index}: {it.datasheet_path}")

        out_path = Path(output_pdf_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # We generate intermediate PDFs as temp files.
        # NamedTemporaryFile is used with delete=False because Windows keeps the file
        # locked while it's open.
        summary_tmp = tempfile.NamedTemporaryFile(suffix="_summary.pdf", delete=False)
        summary_tmp.close()

        header_tmps: List[str] = []
        try:
            self.build_summary_table_pdf(items, summary_tmp.name)

            for it in items:
                hdr_tmp = tempfile.NamedTemporaryFile(suffix=f"_item_{it.index}_header.pdf", delete=False)
                hdr_tmp.close()
                self.build_item_header_pdf(it, hdr_tmp.name)
                header_tmps.append(hdr_tmp.name)

            # Merge using PyMuPDF to preserve vector content.
            merged = fitz.open()
            try:
                if cover_pdf_path:
                    with fitz.open(cover_pdf_path) as cover_doc:
                        merged.insert_pdf(cover_doc)

                with fitz.open(summary_tmp.name) as summary_doc:
                    merged.insert_pdf(summary_doc)

                for it, header_path in zip(items, header_tmps):
                    with fitz.open(header_path) as header_doc:
                        merged.insert_pdf(header_doc)
                    with fitz.open(it.datasheet_path) as datasheet_doc:
                        merged.insert_pdf(datasheet_doc)

                # Optimize output file size.
                merged.save(str(out_path), garbage=4, deflate=True)
            finally:
                merged.close()

        finally:
            # Best-effort cleanup of temp files.
            _safe_remove(summary_tmp.name)
            for p in header_tmps:
                _safe_remove(p)


def _safe_remove(path: str) -> None:
    try:
        os.remove(path)
    except Exception:
        # Temp-file cleanup failure is non-fatal.
        pass
