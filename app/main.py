import customtkinter as ctk
from server_app import ServerApp
from client_app import ClientApp
import sys
import os

class SpeekLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SpeekChat Launcher")
        self.geometry("300x250")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.label = ctk.CTkLabel(self, text="SpeekChat", font=("Roboto", 24, "bold"))
        self.label.pack(pady=20)

        self.btn_client = ctk.CTkButton(self, text="Start Client", command=self.start_client)
        self.btn_client.pack(pady=10)

        self.btn_server = ctk.CTkButton(self, text="Start Server", command=self.start_server)
        self.btn_server.pack(pady=10)

    def start_client(self):
        self.destroy()
        app = ClientApp()
        app.mainloop()

    def start_server(self):
        self.destroy()
        app = ServerApp()
        app.mainloop()

if __name__ == "__main__":
    app = SpeekLauncher()
    app.mainloop()