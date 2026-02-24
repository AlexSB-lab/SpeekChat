import customtkinter as ctk
import threading
from app.core.network_engine import NetworkEngine
import sys

class ServerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SpeekChat Server")
        self.geometry("400x300")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.network = NetworkEngine(is_server=True)
        
        self.setup_ui()
        self.start_server()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        
        self.label_title = ctk.CTkLabel(self, text="SpeekChat Voice Server", font=("Roboto", 24, "bold"))
        self.label_title.grid(row=0, column=0, padx=20, pady=20)

        self.info_frame = ctk.CTkFrame(self)
        self.info_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.info_frame.grid_columnconfigure(0, weight=1)

        self.label_local_ip = ctk.CTkLabel(self.info_frame, text="Local IP: Loading...")
        self.label_local_ip.grid(row=0, column=0, padx=10, pady=5)

        self.label_public_ip = ctk.CTkLabel(self.info_frame, text="Public IP: Loading...")
        self.label_public_ip.grid(row=1, column=0, padx=10, pady=5)

        self.label_port = ctk.CTkLabel(self.info_frame, text=f"Port: {self.network.PORT}")
        self.label_port.grid(row=2, column=0, padx=10, pady=5)

        self.label_sidebar = ctk.CTkLabel(self, text="ACTIVE PARTICIPANTS", font=("Roboto", 12, "bold"), text_color="gray")
        self.label_sidebar.grid(row=2, column=0, padx=20, pady=(20, 5), sticky="w")

        self.scroll_participants = ctk.CTkScrollableFrame(self, height=100)
        self.scroll_participants.grid(row=3, column=0, padx=20, pady=5, sticky="nsew")

        self.label_clients = ctk.CTkLabel(self, text="Total: 0 / 30", font=("Roboto", 14))
        self.label_clients.grid(row=4, column=0, padx=20, pady=5)

        self.btn_stop = ctk.CTkButton(self, text="Stop Server", command=self.on_closing, fg_color="red", hover_color="#AA0000")
        self.btn_stop.grid(row=5, column=0, padx=20, pady=20)

    def start_server(self):
        try:
            self.network.start()
            
            # Update IP info in background
            threading.Thread(target=self.update_ips, daemon=True).start()
            # Update client count periodically
            self.update_stats()
            
        except Exception as e:
            print(f"Failed to start server: {e}")
            self.on_closing()

    def update_ips(self):
        local_ip = self.network.get_local_ip()
        public_ip = self.network.get_public_ip()
        
        self.after(0, lambda: self.label_local_ip.configure(text=f"Local IP: {local_ip}"))
        self.after(0, lambda: self.label_public_ip.configure(text=f"Public IP: {public_ip}"))

    def update_stats(self):
        if self.network.is_running:
            participants = list(self.network.clients.values())
            count = len(participants)
            
            self.label_clients.configure(text=f"Total: {count} / 30")
            
            # Update names list
            for widget in self.scroll_participants.winfo_children():
                widget.destroy()
            for name in participants:
                lbl = ctk.CTkLabel(self.scroll_participants, text=f"• {name}", font=("Roboto", 12))
                lbl.pack(fill="x", padx=10, pady=1)
                
            self.after(2000, self.update_stats)

    def on_closing(self):
        self.network.stop()
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    app = ServerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
