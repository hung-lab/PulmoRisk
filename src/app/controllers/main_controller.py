"""Main application controller."""

import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.views.main_window import MainWindow


class MainController:
    """Main application controller."""

    def __init__(self, root) -> None:
        """Initialize the main controller.

        Args:
            root: The root CustomTkinter window
        """
        self.root = root
        self.view = None

    def set_view(self, view: "MainWindow") -> None:
        """Set the view associated with this controller.

        Args:
            view: The view to set
        """
        self.view = view

    def on_button_click(self) -> None:
        """Handle button click event."""
        if self.view:
            self.view.update_status("Button clicked!")
            # Animate progress bar

            def animate_progress():
                for i in range(11):
                    self.view.update_progress(i / 10.0)
                    time.sleep(0.1)
                self.view.update_progress(0.5)  # Reset to default

            thread = threading.Thread(target=animate_progress)
            thread.daemon = True
            thread.start()
