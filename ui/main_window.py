"""ui/main_window.py

Primary application window.

Responsibilities:
- Own the in-memory project state (cover path + list of BOMItem)
- Render and manage the scrollable list of BOMItemRow widgets
- Implement project save/load
- Implement drag-and-drop reordering
- Orchestrate PDF generation via `core.pdf_engine.PDFEngine`
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk

from config import (
    APP_TITLE,
    COLOR_BG,
    COLOR_CARD_BG,
    COLOR_ROW_BG,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SUBTLE,
    COLOR_INPUT_TEXT,
    FONT_SIZE_APP_BRAND,
    FONT_SIZE_PROJECT_TITLE,
    FONT_SIZE_SECTION_HEADER,
    FONT_SIZE_INPUT,
    FONT_SIZE_BUTTON,
    PADDING_OUTER,
    PADDING_SECTION,
    PADDING_ROW,
    PADDING_INPUT,
    INPUT_HEIGHT,
    DEFAULT_OUTPUT_DIRNAME,
)
from core.data_handler import BOMItem, load_from_json, save_to_json
from core.pdf_engine import PDFEngine
from core.reorder_logic import move_item, refresh_item_indices
from ui.components import init_ui_theme, make_app_frame, make_divider, make_icon_button, make_primary_button, make_section_title
from ui.item_row import BOMItemRow, DEFAULT_COLUMN_WIDTHS


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        init_ui_theme()

        # --- Window chrome ---
        self.geometry("1100x720")
        self.title(APP_TITLE)
        self.configure(fg_color=COLOR_BG)

        # Project state (source of truth)
        self.project_file_path: Optional[str] = None
        self.cover_page_path: Optional[str] = None
        self.items: List[BOMItem] = []
        self.rows: List[BOMItemRow] = []

        # Shared column widths for header row + item rows.
        self.column_widths = dict(DEFAULT_COLUMN_WIDTHS)

        # Drag state
        self._drag_row: Optional[BOMItemRow] = None
        self._drag_last_root_y: Optional[int] = None

        # --- Layout root ---
        self.root_frame = make_app_frame(self)
        self.root_frame.pack(fill="both", expand=True, padx=PADDING_OUTER, pady=PADDING_OUTER)

        self._build_header()
        self._build_cover_section()
        make_divider(self.root_frame).pack(fill="x", pady=(0, 10))
        self._build_items_section()
        self._build_footer()

        # Start with one blank item for convenience.
        self.add_item()

    # -------------------------------------------------------------------------
    # UI sections
    # -------------------------------------------------------------------------
    def _load_icon(self, icon_path: str, size: tuple[int, int] = (16, 16)):
        """Load icon from file path and resize if needed."""
        if icon_path:
            try:
                from PIL import Image
                image = Image.open(icon_path)
                image = image.resize(size, Image.Resampling.LANCZOS)
                return ctk.CTkImage(light_image=image, size=size)
            except Exception as e:
                print(f"Warning: Could not load icon {icon_path}: {e}")
                return None
    
    def _build_header(self) -> None:
        # App brand header (subtle, top-right positioning)
        brand_header = ctk.CTkFrame(self.root_frame, fg_color="transparent", height=40)
        brand_header.pack(fill="x", pady=(0, 5))
        brand_header.pack_propagate(False)
        
        # Left side - App brand (small, grey)
        brand_left = ctk.CTkFrame(brand_header, fg_color="transparent")
        brand_left.pack(side="left", padx=10, pady=5)
        
        self.brand_label = ctk.CTkLabel(
            brand_left,
            text="BOM GENERATOR PRO",
            text_color=COLOR_TEXT_SUBTLE,
            font=ctk.CTkFont(size=FONT_SIZE_APP_BRAND, weight="normal")
        )
        self.brand_label.pack(side="left")
        
        # Right side - Save/Load buttons
        right = ctk.CTkFrame(brand_header, fg_color="transparent")
        right.pack(side="right", padx=10, pady=5)
        
        self.save_btn = make_icon_button(right, "Save", self.save_project, width=110, height=40, icon_path="ui/icons/save.png")
        self.save_btn.pack(side="left", padx=(0, 8))
        
        self.load_btn = make_icon_button(right, "Load", self.load_project, width=110, height=40, icon_path="ui/icons/folder-open.png")
        self.load_btn.pack(side="left")
        
        # Project title header (prominent, hero text) - now includes cover action
        project_header = ctk.CTkFrame(self.root_frame, fg_color="transparent", height=50)
        project_header.pack(fill="x", pady=(0, 8))
        project_header.pack_propagate(False)
        
        # Left side - Project title
        project_left = ctk.CTkFrame(project_header, fg_color="transparent")
        project_left.pack(side="left", padx=10, pady=10)
        
        # Project title container (acts like an inline editable field)
        self.project_title_frame = ctk.CTkFrame(project_left, fg_color="transparent")
        self.project_title_frame.pack(side="left")
        
        # Project title label (looks like text, but is clickable)
        self.project_label = ctk.CTkLabel(
            self.project_title_frame,
            text="Untitled Project",
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(size=FONT_SIZE_PROJECT_TITLE, weight="bold"),
            cursor="hand2"
        )
        self.project_label.pack(side="left")
        
        # Edit icon (subtle pencil)
        self.edit_icon = ctk.CTkLabel(
            self.project_title_frame,
            text="",
            image=self._load_icon("ui/icons/pencil.png"),
            cursor="hand2"
        )
        self.edit_icon.pack(side="left", padx=(8, 0))
        
        # Right side - Cover page action
        project_right = ctk.CTkFrame(project_header, fg_color="transparent")
        project_right.pack(side="right", padx=10, pady=10)
        
        # Cover action container
        self.cover_action_frame = ctk.CTkFrame(project_right, fg_color="transparent")
        self.cover_action_frame.pack(side="right")
        
        # Initialize cover action button
        self.cover_action_btn = None
        self._update_cover_action()
        
        # Hidden entry field for inline editing
        self.project_entry = ctk.CTkEntry(
            self.project_title_frame,
            font=ctk.CTkFont(size=FONT_SIZE_PROJECT_TITLE, weight="bold"),
            fg_color=COLOR_CARD_BG,
            text_color=COLOR_INPUT_TEXT,
            border_width=0,
            height=INPUT_HEIGHT,
            width=300
        )
        
        # Bind click events to make title editable
        self.project_label.bind("<Button-1>", self._start_edit_project_name)
        self.edit_icon.bind("<Button-1>", self._start_edit_project_name)
        self.project_entry.bind("<Return>", self._finish_edit_project_name)
        self.project_entry.bind("<FocusOut>", self._finish_edit_project_name)
        
        # Hover effect for project title
        self.project_label.bind("<Enter>", self._on_project_title_hover)
        self.project_label.bind("<Leave>", self._on_project_title_leave)
        self.edit_icon.bind("<Enter>", self._on_project_title_hover)
        self.edit_icon.bind("<Leave>", self._on_project_title_leave)

    def _build_cover_section(self) -> None:
        """Cover section is now integrated into header - this method is deprecated."""
        pass

    def _build_items_section(self) -> None:
        # Add horizontal divider line
        # divider = make_divider(self.root_frame)
        # divider.pack(fill="x", pady=(0, 16))
        
        items_frame = ctk.CTkFrame(self.root_frame, fg_color="transparent")
        items_frame.pack(fill="both", expand=True)

        make_section_title(items_frame, "BOM ITEMS").pack(anchor="w")

        # Explicit column headers (matches wireframe request).
        self.columns_header = ctk.CTkFrame(items_frame, fg_color="transparent")
        self.columns_header.pack(fill="x", pady=(8, 0))
        self._build_columns_header()

        # Scrollable list where each BOMItemRow is packed vertically.
        self.scroll = ctk.CTkScrollableFrame(items_frame, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, pady=(8, 0))

    def _build_columns_header(self) -> None:
        """Create a single header row aligned to the item row columns."""

        font = ctk.CTkFont(size=FONT_SIZE_SECTION_HEADER, weight="bold")

        def _lbl(text: str, width: int):
            w = ctk.CTkLabel(self.columns_header, text=text, text_color=COLOR_TEXT_MUTED, width=width, font=font)
            w.pack(side="left", padx=4)
            return w

        _lbl("#", self.column_widths["index"]).pack_configure(padx=(8, 4))
        _lbl("MODEL", self.column_widths["model"])
        _lbl("DESCRIPTION", self.column_widths["description"])
        _lbl("MAKE", self.column_widths["make"])
        _lbl("QTY", self.column_widths["qty"])
        _lbl("PDF", self.column_widths["pdf"])
        _lbl("", self.column_widths["handle"])
        _lbl("", self.column_widths["delete"]).pack_configure(padx=(4, 10))

    def _build_footer(self) -> None:
        # Bottom-docked footer (fixed) matches wireframe.
        footer = ctk.CTkFrame(self.root_frame, fg_color="transparent")
        footer.pack(fill="x", pady=(PADDING_SECTION, 0))

        self.add_btn = ctk.CTkButton(
            footer, 
            text="+ ADD NEW ITEM", 
            width=160, 
            height=42,  # Match Generate button height
            command=self.add_item,
            font=ctk.CTkFont(size=FONT_SIZE_BUTTON, weight="normal"),
            fg_color=COLOR_CARD_BG,
            text_color=COLOR_TEXT,
            hover_color="#2a2a2a",
            border_width=1,
            border_color="#333333"
        )
        self.add_btn.pack(side="left", padx=PADDING_OUTER, pady=PADDING_ROW)

        self.generate_btn = make_primary_button(footer, "\u26A1 GENERATE BOM", self.generate_bom)
        self.generate_btn.configure(
            width=200, 
            height=42,  # Match Add Item button
            font=ctk.CTkFont(size=FONT_SIZE_BUTTON, weight="bold")
        )
        self.generate_btn.pack(side="right", padx=PADDING_OUTER, pady=PADDING_ROW)

    # -------------------------------------------------------------------------
    # Project actions (Save/Load)
    # -------------------------------------------------------------------------
    def save_project(self) -> None:
        """Save project JSON.

        If the project doesn't have a path yet, prompt the user.
        """

        if not self.project_file_path:
            path = filedialog.asksaveasfilename(
                title="Save Project",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
            )
            if not path:
                return
            self.project_file_path = path

        try:
            save_to_json(self.project_file_path, self.items, self.cover_page_path)
            # Update project name from file
            filename = Path(self.project_file_path).stem
            self.project_label.configure(text=filename)
        except Exception as e:
            messagebox.showerror("Save Failed", str(e))

    def load_project(self) -> None:
        path = filedialog.askopenfilename(
            title="Load Project",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return

        try:
            payload = load_from_json(path)
        except Exception as e:
            messagebox.showerror("Load Failed", str(e))
            return

        self.project_file_path = path
        self.cover_page_path = payload.get("cover_page_path")
        self._update_cover_action()
        
        # Update project name from file
        if path:
            filename = Path(path).stem
            self.project_label.configure(text=filename)
        else:
            self.project_label.configure(text="Untitled Project")

        # Rebuild the UI list from scratch to avoid stale widgets.
        self._clear_all_items()
        for it in payload.get("items", []):
            self._append_item(it)

    def clear_cover(self) -> None:
        self.cover_page_path = None
        self._update_cover_action()
    
    def _start_edit_project_name(self, event=None) -> None:
        """Start inline editing of project name."""
        current_text = self.project_label.cget("text")
        
        # Hide label, show entry
        self.project_label.pack_forget()
        self.edit_icon.pack_forget()
        
        # Configure and show entry
        self.project_entry.delete(0, "end")
        self.project_entry.insert(0, current_text)
        self.project_entry.pack(side="left")
        self.project_entry.focus_set()
        self.project_entry.select_range(0, "end")
    
    def _finish_edit_project_name(self, event=None) -> None:
        """Finish inline editing of project name."""
        new_text = self.project_entry.get().strip()
        
        if new_text and new_text != "Untitled Project":
            self.project_label.configure(text=new_text)
            # Update window title
            self.title(f"{APP_TITLE} - {new_text}")
        else:
            self.project_label.configure(text="Untitled Project")
        
        # Hide entry, show label
        self.project_entry.pack_forget()
        self.project_label.pack(side="left")
        self.edit_icon.pack(side="left", padx=(8, 0))
    
    def _on_project_title_hover(self, event=None) -> None:
        """Add hover effect to project title."""
        self.project_title_frame.configure(fg_color="#2a2a2a")
    
    def _on_project_title_leave(self, event=None) -> None:
        """Remove hover effect from project title."""
        self.project_title_frame.configure(fg_color="transparent")

    # -------------------------------------------------------------------------
    # Cover actions
    # -------------------------------------------------------------------------
    def _update_cover_action(self) -> None:
        """Update cover action button in header based on cover state."""
        
        # Clear existing button
        if self.cover_action_btn:
            self.cover_action_btn.destroy()
        
        if not self.cover_page_path:
            # Empty state - show add cover button
            self.cover_action_btn = ctk.CTkButton(
                self.cover_action_frame,
                text="Add cover page (optional)",
                command=self.pick_cover,
                fg_color="transparent",
                text_color=COLOR_TEXT_MUTED,
                hover_color="#2a2a2a",
                font=ctk.CTkFont(size=12, weight="normal"),
                cursor="hand2",
                height=30,
                image=self._load_icon("ui/icons/paperclip.png")
            )
            self.cover_action_btn.pack()
        else:
            # Selected state - show pill with filename and close button
            filename = self._truncate_filename(Path(self.cover_page_path).name)
            
            # Create pill container
            pill_frame = ctk.CTkFrame(
                self.cover_action_frame,
                fg_color="#1a3a2a",  # Greenish background
                corner_radius=15,
                border_width=1,
                border_color=COLOR_SUCCESS
            )
            pill_frame.pack(side="right")
            
            # PDF icon
            pdf_icon = ctk.CTkLabel(
                pill_frame,
                text="",
                image=self._load_icon("ui/icons/paperclip.png")
            )
            pdf_icon.pack(side="left", padx=(8, 4))
            
            # Filename
            filename_label = ctk.CTkLabel(
                pill_frame,
                text=filename,
                text_color=COLOR_TEXT,
                font=ctk.CTkFont(size=12, weight="normal")
            )
            filename_label.pack(side="left", padx=(0, 4))
            
            # Close button
            close_btn = ctk.CTkButton(
                pill_frame,
                text="",
                command=self.clear_cover,
                fg_color="transparent",
                text_color=COLOR_TEXT_MUTED,
                hover_color=COLOR_DANGER,
                width=20,
                height=20,
                font=ctk.CTkFont(size=10),
                corner_radius=10,
                image=self._load_icon("ui/icons/x.png")
            )
            close_btn.pack(side="left", padx=(0, 6))
            
            self.cover_action_btn = pill_frame
    
    def _truncate_filename(self, filename: str, max_length: int = 20) -> str:
        """Truncate filename if longer than max_length."""
        if len(filename) <= max_length:
            return filename
        return filename[:max_length-3] + "..."
    
    def pick_cover(self) -> None:
        filename = filedialog.askopenfilename(
            title="Select Cover PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not filename:
            return

        self.cover_page_path = filename
        self._update_cover_action()


    # -------------------------------------------------------------------------
    # Item list management
    # -------------------------------------------------------------------------
    def add_item(self) -> None:
        new_item = BOMItem(index=len(self.items) + 1)
        self._append_item(new_item)

    def _append_item(self, item: BOMItem) -> None:
        """Append a new row + item to the UI and internal model."""

        self.items.append(item)

        row = BOMItemRow(
            self.scroll,
            item=item,
            column_widths=self.column_widths,
            on_delete=self.delete_row,
            on_drag_start=self._drag_start,
            on_drag_motion=self._drag_motion,
        )
        row.pack(fill="x", pady=6)
        self.rows.append(row)

    def delete_row(self, row: BOMItemRow) -> None:
        """Delete an item row and refresh indices."""

        if row not in self.rows:
            return

        idx = self.rows.index(row)

        # Remove from UI.
        row.pack_forget()
        row.destroy()

        # Remove from model.
        self.rows.pop(idx)
        self.items.pop(idx)

        self._refresh_indices_and_repack()

    def _clear_all_items(self) -> None:
        for r in self.rows:
            r.pack_forget()
            r.destroy()
        self.rows.clear()
        self.items.clear()

    def _refresh_indices_and_repack(self) -> None:
        """Ensure `.index` values match visible order and UI is packed in correct order."""

        refresh_item_indices(self.items)
        for item, row in zip(self.items, self.rows):
            row.update_index(item.index)

        # Re-pack to match list order.
        for r in self.rows:
            r.pack_forget()
        for r in self.rows:
            r.pack(fill="x", pady=6)

    # -------------------------------------------------------------------------
    # Drag-and-drop reordering
    # -------------------------------------------------------------------------
    def _drag_start(self, row: BOMItemRow, y_root: int) -> None:
        self._drag_row = row
        self._drag_last_root_y = y_root

    def _drag_motion(self, row: BOMItemRow, y_root: int) -> None:
        """Swap rows when the pointer crosses neighbor midpoints.

        This implements the blueprint behavior:
        - Drag handle emits motion events
        - If the mouse crosses the midpoint of the neighboring row, swap.
        """

        if self._drag_row is None:
            return
        if row is not self._drag_row:
            return

        current_index = self.rows.index(row)
        if current_index < 0:
            return

        # Determine if we should swap up/down based on crossing neighbor midpoints.
        # Using `winfo_rooty()` gives screen coordinates which match `event.y_root`.
        if current_index > 0:
            prev_row = self.rows[current_index - 1]
            prev_mid = prev_row.winfo_rooty() + (prev_row.winfo_height() // 2)
            if y_root < prev_mid:
                self._swap(current_index, current_index - 1)
                return

        if current_index < len(self.rows) - 1:
            next_row = self.rows[current_index + 1]
            next_mid = next_row.winfo_rooty() + (next_row.winfo_height() // 2)
            if y_root > next_mid:
                self._swap(current_index, current_index + 1)
                return

    def _swap(self, i: int, j: int) -> None:
        """Swap both UI rows and model items, then re-pack."""

        move_item(self.rows, i, j)
        move_item(self.items, i, j)
        self._refresh_indices_and_repack()

    # -------------------------------------------------------------------------
    # Progress + generation
    # -------------------------------------------------------------------------

    def generate_bom(self) -> None:
        """Create the final merged BOM package."""

        if not self.items:
            messagebox.showwarning("Nothing to Generate", "Add at least one item.")
            return

        # Default output folder is a sibling of the project file when possible.
        if self.project_file_path:
            default_dir = str(Path(self.project_file_path).parent / DEFAULT_OUTPUT_DIRNAME)
        else:
            default_dir = str(Path(os.getcwd()) / DEFAULT_OUTPUT_DIRNAME)

        Path(default_dir).mkdir(parents=True, exist_ok=True)
        default_name = f"BOM_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        out_path = filedialog.asksaveasfilename(
            title="Save Generated BOM",
            initialdir=default_dir,
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not out_path:
            return

        try:
            engine = PDFEngine()
            engine.merge_bom(cover_pdf_path=self.cover_page_path, items=self.items, output_pdf_path=out_path)
            messagebox.showinfo("Success", f"Generated BOM:\n{out_path}")
        except Exception as e:
            messagebox.showerror("Generate Failed", str(e))
