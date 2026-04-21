"""Main application window view using CustomTkinter."""

from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from app.controllers.main_controller import MainController


class MainWindow:
    """Main application window view with CustomTkinter."""

    def __init__(self, root: ctk.CTk, controller: "MainController") -> None:
        """Initialize the main window view.

        Args:
            root: The root CustomTkinter window
            controller: The main controller
        """
        self.root = root
        self.controller = controller

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface components with CustomTkinter."""
        # Main container with modern styling
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=20)

        # Header with modern styling
        header = ctk.CTkLabel(
            main_frame,
            text="CustomTkinter App",
            font=("Arial", 24, "bold"),
            text_color="#1a1a1a",
        )
        header.pack(pady=(20, 30))

        # Content frame
        content_frame = ctk.CTkFrame(main_frame)
        content_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=10)

        # Example button with modern styling
        self.example_button = ctk.CTkButton(
            content_frame,
            text="Click Me!",
            command=self.controller.on_button_click,
            width=200,
            height=40,
            corner_radius=10,
            font=("Arial", 12, "bold"),
            fg_color="#2ecc71",
            hover_color="#3498db",
            text_color="white",
        )
        self.example_button.pack(pady=20)

        # Modern segmented button for theme switching
        theme_frame = ctk.CTkFrame(main_frame)
        theme_frame.pack(fill=ctk.X, padx=20, pady=10)

        theme_label = ctk.CTkLabel(
            theme_frame, text="Theme:", font=("Arial", 11, "bold")
        )
        theme_label.pack(side=ctk.LEFT, padx=(10, 5))

        self.appearance_mode_label = ctk.CTkLabel(
            theme_frame, text="Light", font=("Arial", 11)
        )
        self.appearance_mode_label.pack(side=ctk.LEFT, padx=5)

        self.appearance_mode_option_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode_event,
        )
        self.appearance_mode_option_menu.pack(side=ctk.LEFT, padx=5)

        # Status label with modern styling
        self.status_label = ctk.CTkLabel(
            content_frame,
            text="Ready",
            font=("Arial", 12, "bold"),
            text_color="#34495e",
        )
        self.status_label.pack(pady=20)

        # Add a modern progress bar
        self.progress = ctk.CTkProgressBar(
            content_frame, width=200, height=10, corner_radius=5
        )
        self.progress.set(0.5)  # Set to 50% initially
        self.progress.pack(pady=10)

        # Add a slider for demonstration
        slider_label = ctk.CTkLabel(
            content_frame, text="Volume:", font=("Arial", 11, "bold")
        )
        slider_label.pack(pady=(10, 5))

        self.volume_slider = ctk.CTkSlider(
            content_frame,
            from_=0,
            to=100,
            width=200,
            height=20,
            corner_radius=10,
            command=self.change_volume_event,
        )
        self.volume_slider.set(75)
        self.volume_slider.pack(pady=5)

    def change_appearance_mode_event(self, new_appearance_mode: str) -> None:
        """Handle appearance mode change.

        Args:
            new_appearance_mode: The new appearance mode
        """
        ctk.set_appearance_mode(new_appearance_mode)
        self.appearance_mode_label.configure(text=new_appearance_mode)

    def change_volume_event(self, value: float) -> None:
        """Handle volume slider change.

        Args:
            value: The slider value
        """
        # You can use this value in your application

    def update_status(self, message: str) -> None:
        """Update the status label.

        Args:
            message: The status message to display
        """
        self.status_label.configure(text=message)

    def update_progress(self, value: float) -> None:
        """Update the progress bar.

        Args:
            value: Progress value (0.0 to 1.0)
        """
        self.progress.set(value)
