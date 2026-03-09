"""ui/item_row.py

The BOM item row widget.

Each row owns:
- Editable fields (Model, Description, Make, Qty)
- Datasheet attach button + visual status
- Delete action
- Drag handle for reordering

The row updates its bound `BOMItem` as the user types, so the main window always
has a current in-memory model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Optional

import customtkinter as ctk
from tkinter import filedialog

from config import COLOR_ACCENT, COLOR_DANGER, COLOR_CARD_BG, COLOR_SUCCESS, COLOR_TEXT, COLOR_INPUT_TEXT, FONT_SIZE_INPUT, FONT_SIZE_BUTTON, PADDING_INPUT, PADDING_ROW, INPUT_HEIGHT
from core.data_handler import BOMItem

# Icon loading helper
from PIL import Image


DEFAULT_COLUMN_WIDTHS: Dict[str, int] = {
    "index": 40,
    "model": 150,
    "description": 340,
    "make": 170,
    "qty": 70,
    "pdf": 54,
    "handle": 46,
    "delete": 46,
}


class BOMItemRow(ctk.CTkFrame):
    """A single row in the BOM list."""

    def _load_icon(self, icon_path: str, size: tuple[int, int] = (16, 16)):
        """Load icon from file path and resize if needed."""
        try:
            image = Image.open(icon_path)
            image = image.resize(size, Image.Resampling.LANCZOS)
            return ctk.CTkImage(light_image=image, size=size)
        except Exception as e:
            print(f"Warning: Could not load icon {icon_path}: {e}")
            return None
    
    def __init__(
        self,
        master,
        *,
        item: BOMItem,
        column_widths: Optional[Dict[str, int]] = None,
        on_delete: Callable[["BOMItemRow"], None],
        on_change: Optional[Callable[[], None]] = None,
        on_drag_start: Callable[["BOMItemRow", int], None],
        on_drag_motion: Callable[["BOMItemRow", int], None],
    ):
        super().__init__(master, fg_color=COLOR_CARD_BG)

        self.item = item
        self._on_delete = on_delete
        self._on_change = on_change
        self._on_drag_start = on_drag_start
        self._on_drag_motion = on_drag_motion

        # Column widths are shared with the column-header row in the main window.
        self._col_w = dict(DEFAULT_COLUMN_WIDTHS)
        if column_widths:
            self._col_w.update(column_widths)

        # --- Drag handle ---
        grip_icon = self._load_icon("ui/icons/grip-vertical.png")
        self.handle_label = ctk.CTkLabel(
            self, 
            text="", 
            image=grip_icon, 
            width=self._col_w["handle"],
            cursor="hand2"
        )
        self.handle_label.pack(side="left", padx=(2, 4))
        self.handle_label.bind("<Button-1>", self._handle_drag_start)
        self.handle_label.bind("<B1-Motion>", self._handle_drag_motion)
        self.handle_label.bind("<ButtonRelease-1>", self._handle_drag_end)

        # --- Index label ---
        self.index_label = ctk.CTkLabel(self, text=str(item.index), text_color=COLOR_TEXT, width=self._col_w["index"])
        self.index_label.pack(side="left", padx=(8, 4))

        # --- Editable fields ---
        # Consistent height and internal padding for neatness
        self.model_entry = ctk.CTkEntry(
            self, 
            placeholder_text="Model No.", 
            width=self._col_w["model"],
            height=INPUT_HEIGHT,
            font=ctk.CTkFont(size=FONT_SIZE_INPUT),
            fg_color=COLOR_CARD_BG,
            text_color=COLOR_INPUT_TEXT,
            border_width=1,
            border_color="#333333"
        )
        self.model_entry.insert(0, item.model)
        self.model_entry.pack(side="left", padx=4, pady=PADDING_ROW)

        self.desc_entry = ctk.CTkEntry(
            self, 
            placeholder_text="Description", 
            width=self._col_w["description"],
            height=INPUT_HEIGHT,
            font=ctk.CTkFont(size=FONT_SIZE_INPUT),
            fg_color=COLOR_CARD_BG,
            text_color=COLOR_INPUT_TEXT,
            border_width=1,
            border_color="#333333"
        )
        self.desc_entry.insert(0, item.description)
        self.desc_entry.pack(side="left", padx=4, pady=PADDING_ROW)

        self.make_entry = ctk.CTkEntry(
            self, 
            placeholder_text="Make", 
            width=self._col_w["make"],
            height=INPUT_HEIGHT,
            font=ctk.CTkFont(size=FONT_SIZE_INPUT),
            fg_color=COLOR_CARD_BG,
            text_color=COLOR_INPUT_TEXT,
            border_width=1,
            border_color="#333333"
        )
        self.make_entry.insert(0, item.make)
        self.make_entry.pack(side="left", padx=4, pady=PADDING_ROW)

        self.qty_entry = ctk.CTkEntry(
            self, 
            placeholder_text="Qty", 
            width=self._col_w["qty"],
            height=INPUT_HEIGHT,
            font=ctk.CTkFont(size=FONT_SIZE_INPUT),
            fg_color=COLOR_CARD_BG,
            text_color=COLOR_INPUT_TEXT,
            border_width=1,
            border_color="#333333"
        )
        self.qty_entry.insert(0, str(item.quantity))
        self.qty_entry.pack(side="left", padx=4, pady=PADDING_ROW)

        # --- PDF status button (Pill shape) ---
        pdf_icon = self._load_icon("ui/icons/paperclip.png")
        self.pdf_button = ctk.CTkButton(
            self, 
            text="", 
            width=self._col_w["pdf"], 
            height=INPUT_HEIGHT,
            command=self._pick_pdf,
            font=ctk.CTkFont(size=FONT_SIZE_BUTTON),
            corner_radius=15,  # Pill shape
            fg_color=COLOR_CARD_BG,
            text_color=COLOR_TEXT,
            border_width=1,
            border_color="#333333",
            hover_color="#2a2a2a",
            image=pdf_icon
        )
        self.pdf_button.pack(side="left", padx=4)

        # --- Delete button (Pill shape) ---
        delete_icon = self._load_icon("ui/icons/x.png")
        self.delete_button = ctk.CTkButton(
            self, 
            text="", 
            width=self._col_w["delete"], 
            height=INPUT_HEIGHT,
            command=self._delete,
            font=ctk.CTkFont(size=FONT_SIZE_BUTTON, weight="bold"),
            corner_radius=15,  # Pill shape
            fg_color='transparent',
            text_color=COLOR_TEXT,
            hover_color=COLOR_DANGER,
            border_width=1,
            border_color="#333333",
            image=delete_icon
        )
        self.delete_button.pack(side="left", padx=(4, 10))

        # --- Reactive bindings ---
        # Any edit updates the underlying item and refreshes the main window status.
        self.model_entry.bind("<KeyRelease>", lambda _e: self._sync_to_item())
        self.desc_entry.bind("<KeyRelease>", lambda _e: self._sync_to_item())
        self.make_entry.bind("<KeyRelease>", lambda _e: self._sync_to_item())
        self.qty_entry.bind("<KeyRelease>", lambda _e: self._sync_to_item())

        self.update_pdf_visual_status()

    def update_index(self, index: int) -> None:
        """Update UI label + bound item index."""

        self.item.index = index
        self.index_label.configure(text=str(index))

    def update_pdf_visual_status(self) -> None:
        """Set PDF button color based on file existence."""

        path = (self.item.datasheet_path or "").strip()
        if not path:
            # Default state: no file chosen - grayscale
            self.pdf_button.configure(
                image=self._load_icon("ui/icons/paperclip.png"),
                fg_color=COLOR_CARD_BG,
                text_color=COLOR_TEXT,
                border_color="#333333"
            )
            return

        if Path(path).is_file():
            # File exists - success state with accent
            self.pdf_button.configure(
                image=self._load_icon("ui/icons/check.png"),
                fg_color=COLOR_ACCENT,
                text_color=COLOR_TEXT,
                border_color=COLOR_ACCENT,
                hover_color='#0a66b2'
            )
        else:
            # File referenced but not found - danger state
            self.pdf_button.configure(
                image=self._load_icon("ui/icons/paperclip.png"),
                fg_color=COLOR_DANGER,
                text_color=COLOR_TEXT,
                border_color=COLOR_DANGER
            )

    def _pick_pdf(self) -> None:
        """Attach a datasheet PDF to this item."""

        filename = filedialog.askopenfilename(
            title="Select Datasheet PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not filename:
            return

        self.item.datasheet_path = filename
        self.update_pdf_visual_status()
        if self._on_change:
            self._on_change()

    def _delete(self) -> None:
        self._on_delete(self)

    def _sync_to_item(self) -> None:
        """Pull current entry values into the bound BOMItem.

        Qty validation is intentionally forgiving:
        - Non-digits are stripped
        - Empty becomes 1
        """

        self.item.model = self.model_entry.get().strip()
        self.item.description = self.desc_entry.get().strip()
        self.item.make = self.make_entry.get().strip()

        raw_qty = self.qty_entry.get().strip()
        filtered = "".join([c for c in raw_qty if c.isdigit()])
        if filtered != raw_qty:
            # Replace entry content to match the filtered digits.
            self.qty_entry.delete(0, "end")
            self.qty_entry.insert(0, filtered)

        qty_value = int(filtered) if filtered else 1
        self.item.quantity = max(1, qty_value)

        if self._on_change:
            self._on_change()

    # --- Drag handling ---
    # We delegate list manipulation to the main window (source of truth).
    def _handle_drag_start(self, event) -> None:
        self.handle_label.configure(cursor="fleur")
        self._on_drag_start(self, event.y_root)

    def _handle_drag_motion(self, event) -> None:
        self._on_drag_motion(self, event.y_root)

    def _handle_drag_end(self, event) -> None:
        self.handle_label.configure(cursor="hand2")
