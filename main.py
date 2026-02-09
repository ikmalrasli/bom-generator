"""main.py

Entry point.

This file intentionally stays small:
- Fast startup
- Easy to debug packaging issues
- Keeps UI/business logic separated
"""

from ui.main_window import MainWindow


def main() -> None:
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
