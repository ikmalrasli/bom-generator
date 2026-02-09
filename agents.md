This `AGENTS.MD` file is designed to serve as the master technical blueprint. If you provide this to an AI agent (like a coding assistant), it will have all the context needed to generate the specific logic for your app without further explanation.

---

# AGENTS.MD: BOM Generator Project Blueprint

## 1. Project Overview

* **Name:** BOM Generator
* **Platform:** Windows (Stand-alone Executable)
* **Target:** Engineering users requiring zero-prerequisite installation.
* **Goal:** Automate the creation of a technical Bill of Materials (BOM) package by merging user inputs with multiple PDF datasheets into a single, professional document.

## 2. Tech Stack & Dependencies

* **Language:** Python 3.10+
* **UI Framework:** `customtkinter` (Modern UI wrapper for Tkinter).
* **PDF Creation:** `reportlab` (For generating the Summary Table and Item Header pages).
* **PDF Manipulation:** `PyMuPDF` (imported as `fitz`) (For high-speed merging and preservation of vector quality).
* **Data Storage:** `json` (For Project Save/Load functionality).
* **Packaging:** `PyInstaller` (Backend) + `Inno Setup` (Frontend installer for fast startup).

## 3. UI/UX Specifications (Option 1: Engineering Pro)

* **Layout:** Alternative A (Minimalist Single Column).
* **Color Palette:**
* Main Background: `#1A1A1A`
* Row Background: `#242424`
* Accent (Primary Action): `#0078D4`
* Success (Attached): `#2EA043`
* Danger (Delete/Missing): `#D73A49`
* Text: `#FFFFFF`


* **Key Components:**
* `ScrollableFrame` for the main item list.
* `BOMItemRow` (Custom Widget): Contains grip icon, Model, Description, Make, Qty, PDF status, and Delete button.
* Fixed `Footer` for global actions (+Add Item, ⚡ Generate).



## 4. Data Architecture

### Project File Structure (.json)

```json
{
  "project_metadata": {
    "cover_page_path": "string or null",
    "export_date": "ISO-8601"
  },
  "items": [
    {
      "index": 1,
      "model": "string",
      "description": "string",
      "make": "string",
      "quantity": "integer",
      "datasheet_path": "string"
    }
  ]
}

```

## 5. Functional Logic

### A. Drag & Drop Reordering

* **Mechanism:** Bind `<Button-1>` and `<B1-Motion>` to the `⠿` label.
* **Logic:** On drag, calculate the vertical offset. If the mouse crosses the midpoint of the neighboring row, swap indices in the `items` list and refresh the `pack()` order of the UI frames.

### B. PDF Generation Pipeline

1. **Summary Table:** Use `reportlab.platypus.Table` to create a grid matching the user's list.
2. **Item Headers:** Generate a simple page for each item displaying: `Item {No}: {Description} | Make: {Make} | Model: {Model}`.
3. **Merging Sequence:**
* Page 1: User Cover PDF (if exists).
* Page 2: Summary Table PDF.
* Recurring: [Item Header PDF] + [Item Datasheet PDF].


4. **Final Output:** Save via `fitz.Document.save()` with garbage collection enabled to keep file size optimized.

## 6. Constraints & Requirements

* **Performance:** App must launch in < 2 seconds. Use `PyInstaller --onedir` to avoid extraction lag.
* **Robustness:** Handle "File Not Found" errors if a project is loaded but a datasheet has been moved. Use visual "Red" status on the PDF button.
* **Portability:** Use absolute paths for the session but relative paths for project saving where possible.

## 7. Implementation Checklist for Agents

* [ ] Initialize `customtkinter` window with Option 1 theme.
* [ ] Create `BOMItemRow` class with internal validation for Qty (numbers only).
* [ ] Implement `add_item` and `delete_item` methods with automatic index refreshing.
* [ ] Implement `save_project` and `load_project` using `filedialog`.
* [ ] Create `PDFEngine` class using `ReportLab` and `PyMuPDF`.
* [ ] Add the Drag-and-Drop binding logic to the handles.

## 8. Documentation

### Tech Stack & Documentation

| Component | Library | Documentation Link |
| --- | --- | --- |
| **GUI** | `customtkinter` | [CustomTkinter Docs](https://customtkinter.tomschimansky.com/documentation/) |
| **PDF Creation** | `reportlab` | [ReportLab User Guide](https://www.reportlab.com/docs/reportlab-userguide.pdf) |
| **PDF Merging** | `PyMuPDF` (fitz) | [PyMuPDF Docs](https://pymupdf.readthedocs.io/) |
| **Data Storage** | `json` | [Python JSON Docs](https://docs.python.org/3/library/json.html) |
| **Packaging** | `PyInstaller` | [PyInstaller Usage](https://pyinstaller.org/en/stable/usage.html) |
| **Installer** | `Inno Setup` | [Inno Setup Help](https://jrsoftware.org/ishelp/) |

## 9. UI Wireframe

This chosen layout focuses on a single-column, top-to-bottom workflow with a clean header hierarchy and professional typography system.

```text
________________________________________________________________________________
| (32px Padding)                                                               |
| BOM GENERATOR PRO                                      [ Save] [ Load]  |
|                                                                              |
| Control Panel Rev A           [📎 Add cover page (optional)]               |
| (Main Title - Large)             (Compact Action - Small/Grey)               |
|______________________________________________________________________________|
|------------------------------------------------------------------------------|
| (16px Gap)                                                                   |
| BOM ITEMS                                                                    |
| #   MODEL          DESCRIPTION                 MAKE        QTY    PDF        |
| ---------------------------------------------------------------------------  |
| 1   [ Model   ]    [ Description ........ ]    [ Make ]    [ 1 ]  [📎] [X]   |
|______________________________________________________________________________|
```

### Visual Hierarchy & Typography

**1. App Title ("BOM GENERATOR PRO")**
- **Location**: Top left, subtle grey text
- **Style**: 11pt font, color `#666666`, normal weight
- **Purpose**: Branding that recedes into background

**2. Project Title ("Untitled Project ✎")**
- **Location**: Prominent position below app title
- **Style**: 13pt font, color `#FFFFFF`, bold weight
- **Interaction**: Click to edit inline with hover effect
- **Icon**: Subtle pencil (✎) indicating editability

**3. Section Headers ("BOM ITEMS")**
- **Style**: 14pt font, color `#AAAAAA`, bold weight
- **Purpose**: Clear section separation

**4. Input Fields & Buttons**
- **Style**: 13pt font, color `#DDDDDD` for text
- **Height**: Uniform 35px for all interactive elements
- **Padding**: 12px internal padding, 8px external spacing

### Design System

**Color Palette (90% Grayscale, 10% Accent)**
- **Background**: `#121212` (Main window)
- **Cards/Rows**: `#1E1E1E` (Input fields, buttons)
- **Text**: `#FFFFFF` (Primary), `#AAAAAA` (Headers), `#666666` (Branding)
- **Accent**: `#0078D4` (Primary actions only)

**Typography Hierarchy**
- **App Brand**: 11pt, Normal, #666666
- **Project Title**: 13pt, Bold, #FFFFFF  
- **Section Headers**: 14pt, Bold, #AAAAAA
- **Input Text**: 13pt, Regular, #DDDDDD
- **Button Labels**: 13pt, Semi-Bold, #FFFFFF

**Spacing System (8px Rule)**
- **Outer Margins**: 32px from window edge
- **Section Gaps**: 24px between major sections
- **Row Spacing**: 8px between elements
- **Input Padding**: 12px internal padding

**Component Refinements**
- **Input Fields**: Subtle borders, 35px uniform height
- **Buttons**: Pill-shaped for PDF status, rounded corners for actions
- **Primary Action**: Only colored element (blue accent)
- **Alignment**: Perfect column alignment from headers to inputs

## 10. Recommended Directory Structure and Role of Each Module
 
### A. Directory Structure
```text
BOM_Generator/
├── main.py                 # Entry point (Run this to start the app)
├── config.py               # Theme, Color Palette (Option 1), and Constants
├── core/                   # PDF Logic & Data Management
│   ├── __init__.py
│   ├── pdf_engine.py       # ReportLab & PyMuPDF logic
│   ├── data_handler.py     # JSON Save/Load and CSV export
│   └── reorder_logic.py    # Math for Drag & Drop sorting
├── ui/                     # CustomTkinter Components
│   ├── __init__.py
│   ├── main_window.py      # The primary layout (Minimalist A)
│   ├── item_row.py         # The individual BOM item widget
│   └── components.py       # Custom buttons, headers, and styles
├── assets/                 # Icons and Images
│   └── handle_dots.png     # Unicode is fine, but icons can go here
└── output/                 # Default folder for generated BOMs

```

### B. Role of Each Module
#### **Root Level: `main.py**`

This file only initializes the application. It imports the `MainWindow` from the UI folder and starts the loop. Keeping this clean ensures fast startup debugging.

#### **The Core Folder (Business Logic)**

* **`pdf_engine.py`**: This is where the heavy lifting happens. It should contain a class (e.g., `BOMProcessor`) that takes the list of items and performs the three-step merge: Table Generation → Item Header Generation → Final Merging.
* **`data_handler.py`**: Contains the `save_to_json` and `load_from_json` functions. By separating this, you can easily add "Export to Excel" later without touching your UI code.

#### **The UI Folder (Visuals)**

* **`main_window.py`**: This manages the `CTkScrollableFrame`. It handles the "Add Item" button click by instantiating a new `BOMItemRow`.
* **`item_row.py`**: A clean, standalone class for a single row. It should handle its own "internal" states, like changing the PDF button color from Gray to Green when a file is selected.

---
**End of AGENTS.MD**