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
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.data_handler import BOMItem


class PDFEngine:
    """High-level PDF generator/merger."""

    def format_text(self, text: str, uppercase: bool = True) -> str:
        """Apply text formatting based on uppercase flag."""
        return text.upper() if uppercase and text else text

    def build_summary_table_pdf(self, items: List[BOMItem], out_pdf_path: str, uppercase: bool = True) -> None:
        """Create a one-page (or multi-page) summary table."""

        # ReportLab uses a document template that writes directly to `out_pdf_path`.
        doc = SimpleDocTemplate(out_pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()

        # Create paragraph style for table cells
        cell_style = ParagraphStyle(
            "table_cell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,  # Line spacing
            alignment=TA_LEFT,
        )

        # Table header row (keep as strings for header)
        headers = ["Item", "Model", "Description", "Make", "Qty"]
        data = [[self.format_text(header, uppercase) for header in headers]]

        # Convert cell content to Paragraphs for wrapping
        for i in items:
            data.append([
                self.format_text(str(i.index), uppercase),  # Item number - no wrapping needed
                Paragraph(self.format_text(i.model or "", uppercase), cell_style),  # Model - wrap if needed
                Paragraph(self.format_text(i.description or "", uppercase), cell_style),  # Description - wrap if needed
                Paragraph(self.format_text(i.make or "", uppercase), cell_style),  # Make - wrap if needed
                self.format_text(str(i.quantity), uppercase),  # Quantity - no wrapping needed
            ])

        # Build a readable, engineering-style grid.
        table = Table(data, repeatRows=1, colWidths=[30, 100, 280, 100, 30])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.white]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

        story = [
            table,
        ]

        doc.build(story)

    def build_item_header_pdf(self, item: BOMItem, out_pdf_path: str, uppercase: bool = True) -> None:
        """Create a single-page header inserted before each datasheet."""

        c = canvas.Canvas(out_pdf_path, pagesize=A4)
        page_width, page_height = A4

        styles = getSampleStyleSheet()

        left_margin = 1.0 * inch
        right_margin = 1.0 * inch
        available_width = page_width - left_margin - right_margin

        title_style = ParagraphStyle(
            "item_header_title",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=15,
            alignment=TA_LEFT,
        )

        detail_style = ParagraphStyle(
            "item_header_detail",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=14,
            alignment=TA_LEFT,
        )

        qty_detail_style = ParagraphStyle(
            "item_header_detail",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=14,
            alignment=TA_LEFT,
        )

        # Keep the header page intentionally simple and consistent.
        # This acts as a separator between datasheets in the final merged PDF.
        title_text = f"ITEM {item.index}: {self.format_text(item.description or '(No Description)', uppercase)}"
        make_text = f"MAKE: {self.format_text(item.make or '-', uppercase)}"
        model_text = f"MODEL: {self.format_text(item.model or '-', uppercase)}"
        qty_text = f"QTY: {item.quantity}"

        blocks = [
            Paragraph(title_text, title_style),
            Paragraph(make_text, detail_style),
            Paragraph(model_text, detail_style),
            Paragraph(qty_text, qty_detail_style),
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
        uppercase: bool = True,
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
            self.build_summary_table_pdf(items, summary_tmp.name, uppercase)

            for it in items:
                hdr_tmp = tempfile.NamedTemporaryFile(suffix=f"_item_{it.index}_header.pdf", delete=False)
                hdr_tmp.close()
                self.build_item_header_pdf(it, hdr_tmp.name, uppercase)
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
