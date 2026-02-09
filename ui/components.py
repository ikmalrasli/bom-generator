"""ui/components.py

Shared UI building blocks.

This module exists to:
- Keep consistent colors/fonts
- Avoid duplicating style constants across widgets

We keep it intentionally light-weight to preserve fast startup.
"""

from __future__ import annotations

import customtkinter as ctk

from config import COLOR_ACCENT, COLOR_BG, COLOR_CARD_BG, COLOR_TEXT, COLOR_TEXT_MUTED, FONT_SIZE_SECTION_HEADER, FONT_SIZE_BUTTON


def init_ui_theme() -> None:
    """Initialize CustomTkinter global theme settings."""

    # Dark mode is a core requirement of the spec.
    ctk.set_appearance_mode("dark")

    # We rely on explicit widget colors rather than shipping a .json theme.
    # This keeps packaging simpler.


def make_primary_button(master, text: str, command):
    """Factory for primary action buttons."""

    return ctk.CTkButton(
        master,
        text=text,
        command=command,
        fg_color=COLOR_ACCENT,
        text_color=COLOR_TEXT,
        hover_color="#0a66b2",
        font=ctk.CTkFont(size=FONT_SIZE_BUTTON, weight="bold"),
        corner_radius=8,
        height=35
    )


def make_icon_button(master, text: str, command, *, width: int = 44, height: int = 34, icon_path: str = None):
    """Factory for compact icon buttons with optional PNG icons."""

    button_kwargs = {
        "master": master,
        "text": text,
        "command": command,
        "width": width,
        "height": height,
        "fg_color": COLOR_CARD_BG,
        "text_color": COLOR_TEXT,
        "hover_color": "#2a2a2a",
        "font": ctk.CTkFont(size=FONT_SIZE_BUTTON),
        "corner_radius": 6,
        "border_width": 1,
        "border_color": "#333333"
    }
    
    if icon_path:
        try:
            from PIL import Image
            image = Image.open(icon_path)
            image = image.resize((16, 16), Image.Resampling.LANCZOS)
            button_kwargs["image"] = ctk.CTkImage(light_image=image, size=(16, 16))
        except Exception as e:
            print(f"Warning: Could not load icon {icon_path}: {e}")
    
    return ctk.CTkButton(**button_kwargs)


def make_section_title(master, text: str):
    """Factory for a consistent section header label."""

    return ctk.CTkLabel(
        master, 
        text=text, 
        text_color=COLOR_TEXT_MUTED, 
        font=ctk.CTkFont(size=FONT_SIZE_SECTION_HEADER, weight="bold")
    )


def make_app_frame(master):
    """Root frame color helper."""

    return ctk.CTkFrame(master, fg_color=COLOR_BG)


def make_row_frame(master):
    """Row background helper."""

    return ctk.CTkFrame(master, fg_color=COLOR_CARD_BG)


def make_divider(master):
    """A thin horizontal divider line."""

    return ctk.CTkFrame(master, height=2, fg_color="#444444")
