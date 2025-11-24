from __future__ import annotations
import sys
import tkinter as tk
from tkinter import messagebox

from gui import ServerGeneratorApp


def main() -> None:
    """Entry point for the Minecraft Server Generator GUI."""
    try:
        root = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover
        message = (
            "Unable to initialize Tkinter. If you are running headless, "
            "forward X11 or use a desktop session.\n" f"Details: {exc}"
        )
        print(message, file=sys.stderr)
        sys.exit(1)

    app = ServerGeneratorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.quit_application)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        messagebox.showinfo("Minecraft Server Generator", "Application closed via keyboard interrupt.")


if __name__ == "__main__":
    main()
