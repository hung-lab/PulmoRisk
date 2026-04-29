import datetime

from app.utils.ui_config import SPACE_MD, SPACE_SM, SPACE_XS
import customtkinter as ctk

from app.config.settings import LEVEL_COLOURS, LEVEL_PREFIX
from app.utils.event_bus import AppEvent


class LogPanel:
    def __init__(self, parent: ctk.CTkFrame) -> None:
        self.parent = parent

        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self.parent, fg_color="transparent", border_width=0)
        header.grid(
            row=0, column=0, sticky="ew", padx=SPACE_SM, pady=(SPACE_MD, SPACE_XS)
        )
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Activity Log",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header,
            text="Clear",
            width=56,
            height=24,
            command=self.clear,
        ).grid(row=0, column=1)

        # Log box
        self.box = ctk.CTkTextbox(
            self.parent,
            state="disabled",
            wrap="word",
            font=ctk.CTkFont(size=16),
        )
        self.box.grid(row=1, column=0, sticky="nsew", padx=SPACE_SM, pady=(0, SPACE_SM))

        # Tags
        # Configure per-level colour tags
        for level, colour in LEVEL_COLOURS.items():
            self.box.tag_config(level.lower(), foreground=colour)
        self.box.tag_config("ts", foreground="#888888")

    def log(self, message: str, level: str = "INFO") -> None:
        prefix, tag = LEVEL_PREFIX.get(level.upper(), ("•", "info"))
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        self.box.configure(state="normal")
        self.box.insert("end", f"[{timestamp}] ", "ts")
        self.box.insert("end", f"{prefix} {message}\n", tag)
        self.box.see("end")
        self.box.configure(state="disabled")

    def clear(self) -> None:
        self.box.configure(state="normal")
        self.box.delete("1.0", "end")
        self.box.configure(state="disabled")

    def handle_event(self, event: AppEvent) -> None:
        if event.type == "log":
            self.log(event.message or "", event.level)
