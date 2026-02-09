"""config.py

Centralized theme + UI constants.

Keeping this in a single module makes it easy to adjust styling without touching
business logic or UI layout code.
"""

APP_TITLE = "BOM Generator"

# Option 1 theme palette (Engineering Pro) - Refined for neatness
COLOR_BG = "#121212"                    # Main window background
COLOR_CARD_BG = "#1E1E1E"                 # Card/row backgrounds
COLOR_ROW_BG = "#1E1E1E"                 # BOM item rows
COLOR_ACCENT = "#0078D4"                  # Primary action blue
COLOR_SUCCESS = "#2EA043"                  # Green for success states
COLOR_DANGER = "#D73A49"                   # Red for danger/delete
COLOR_TEXT = "#FFFFFF"                     # Primary white text
COLOR_TEXT_MUTED = "#AAAAAA"               # Section headers
COLOR_TEXT_SUBTLE = "#666666"             # App branding
COLOR_INPUT_TEXT = "#DDDDDD"               # Input field text

# Typography hierarchy (in points for CTk)
FONT_SIZE_APP_BRAND = 24                  # 32px equivalent
FONT_SIZE_PROJECT_TITLE = 13               # 13px
FONT_SIZE_SECTION_HEADER = 14               # 14px  
FONT_SIZE_INPUT = 13                      # 13px
FONT_SIZE_BUTTON = 13                     # 13px

# Spacing system (8px rule)
PADDING_OUTER = 32                        # 32px from window edge
PADDING_SECTION = 24                      # 24px between sections
PADDING_ROW = 8                           # 8px between rows
PADDING_INPUT = 12                        # 12px inside input fields
INPUT_HEIGHT = 35                         # 35px uniform input height

# Layout constants
ROW_HEIGHT = 48

# Default output folder (created on-demand)
DEFAULT_OUTPUT_DIRNAME = "output"
