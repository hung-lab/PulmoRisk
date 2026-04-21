import customtkinter as ctk

from app.controllers.main_controller import MainController
from app.views.main_window import MainWindow


def main() -> None:
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("CustomTkinter App")
    root.geometry("800x600")
    root.minsize(400, 300)

    controller = MainController(root)
    view = MainWindow(root, controller)

    controller.set_view(view)

    root.mainloop()


if __name__ == "__main__":
    main()
