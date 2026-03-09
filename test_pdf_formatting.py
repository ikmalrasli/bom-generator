"""test_pdf_formatting.py

Quick test script for PDF table formatting.
Run this to generate a sample BOM PDF with dummy data.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.data_handler import BOMItem
from core.pdf_engine import PDFEngine


def create_dummy_data():
    """Create sample BOM items for testing."""
    return [
        BOMItem(
            index=1,
            model="Arduino Uno R3",
            description="Microcontroller board for prototyping",
            make="Arduino",
            quantity=5,
            datasheet_path="dummy1.pdf"  # Won't be used for table test
        ),
        BOMItem(
            index=2,
            model="Raspberry Pi 4B",
            description="Single board computer with 4GB RAM",
            make="Raspberry Pi Foundation EXTRA TEXT HERE to test wrapping",
            quantity=2,
            datasheet_path="dummy2.pdf"
        ),
        BOMItem(
            index=3,
            model="ESP32 DevKit",
            description="WiFi and Bluetooth development board",
            make="Espressif",
            quantity=10,
            datasheet_path="dummy3.pdf"
        ),
        BOMItem(
            index=4,
            model="STM32F407VGT6",
            description="ARM Cortex-M4 microcontroller with FPU",
            make="STMicroelectronics",
            quantity=3,
            datasheet_path="dummy4.pdf"
        ),
        BOMItem(
            index=5,
            model="NodeMCU ESP8266",
            description="WiFi development board with USB",
            make="NodeMCU",
            quantity=8,
            datasheet_path="dummy5.pdf"
        ),
    ]


def test_table_formatting():
    """Generate test PDFs with different formatting options."""
    
    # Create output directory if it doesn't exist
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Generate test PDFs
    pdf_engine = PDFEngine()
    dummy_items = create_dummy_data()
    
    # Test 1: Normal case (original formatting)
    output_normal = output_dir / "test_table_normal.pdf"
    print(f"Generating normal case PDF: {output_normal}")
    pdf_engine.build_summary_table_pdf(dummy_items, str(output_normal), uppercase=False)
    print("✓ Normal case PDF generated!")
    
    # Test 2: Uppercase case
    output_upper = output_dir / "test_table_uppercase.pdf"
    print(f"Generating uppercase PDF: {output_upper}")
    pdf_engine.build_summary_table_pdf(dummy_items, str(output_upper), uppercase=True)
    print("✓ Uppercase PDF generated!")
    
    print(f"\nOpen files to compare:")
    print(f"Normal: {output_normal.absolute()}")
    print(f"Uppercase: {output_upper.absolute()}")
    
    return output_normal, output_upper


if __name__ == "__main__":
    test_table_formatting()
