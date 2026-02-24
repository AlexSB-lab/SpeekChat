import customtkinter as ctk
import threading
import queue
from app.core.network_engine import NetworkEngine
from app.core.audio_handler import AudioHandler
import sys
import random

class ClientApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SpeekChat")
        self.geometry("900x600")
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.username = f"User_{random.randint(1000, 9999)}"
        self.network = None
        self.audio = AudioHandler()
        
        self.is_connected = False
        
        self.setup_login_ui()

    def setup_login_ui(self):
        self.clear_window()
        
        self.login_frame = ctk.CTkFrame(self, width=400, height=300)
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        self.label_title = ctk.CTkLabel(self.login_frame, text="SpeekChat", font=("Roboto", 32, "bold"))
        self.label_title.pack(pady=20)
        
        self.entry_username = ctk.CTkEntry(self.login_frame, placeholder_text="Username", width=250)
        self.entry_username.insert(0, self.username)
        self.entry_username.pack(pady=10)
        
        self.entry_ip = ctk.CTkEntry(self.login_frame, placeholder_text="Server IP (e.g. 127.0.0.1)", width=250)
        self.entry_ip.pack(pady=10)
        
        self.btn_connect = ctk.CTkButton(self.login_frame, text="Connect", command=self.connect_to_server, width=250)
        self.btn_connect.pack(pady=20)

    def setup_main_ui(self):
        self.clear_window()
        
        # Sidebar (Discord-style)
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        self.label_sidebar = ctk.CTkLabel(self.sidebar, text="PARTICIPANTS", font=("Roboto", 12, "bold"), text_color="gray")
        self.label_sidebar.pack(pady=(20, 10), padx=20, anchor="w")
        
        self.scroll_participants = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_participants.pack(fill="both", expand=True, padx=5, pady=5)
        
        # User Info at bottom of sidebar
        self.user_panel = ctk.CTkFrame(self.sidebar, height=60, corner_radius=0, fg_color="#2c2f33")
        self.user_panel.pack(side="bottom", fill="x")
        
        self.label_my_name = ctk.CTkLabel(self.user_panel, text=self.username, font=("Roboto", 14, "bold"))
        self.label_my_name.pack(side="left", padx=10, pady=10)
        
        self.btn_mute = ctk.CTkButton(self.user_panel, text="🎤", width=30, height=30, command=self.toggle_mute)
        self.btn_mute.pack(side="right", padx=5)
        
        self.btn_deafen = ctk.CTkButton(self.user_panel, text="🎧", width=30, height=30, command=self.toggle_deafen)
        self.btn_deafen.pack(side="right", padx=5)
        
        # Main area
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="#36393f")
        self.main_area.pack(side="right", fill="both", expand=True)
        
        self.label_status = ctk.CTkLabel(self.main_area, text="Connected to voice", font=("Roboto", 18))
        self.label_status.place(relx=0.5, rely=0.4, anchor="center")
        
        self.btn_disconnect = ctk.CTkButton(self.main_area, text="Disconnect", fg_color="red", hover_color="#AA0000", command=self.disconnect)
        self.btn_disconnect.place(relx=0.5, rely=0.5, anchor="center")

    def clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()

    def connect_to_server(self):
        ip = self.entry_ip.get()
        self.username = self.entry_username.get()
        if not ip: return
        
        try:
            self.network = NetworkEngine(is_server=False, username=self.username)
            self.network.on_audio_received = self.audio.receive_audio
            self.network.on_participants_updated = self.update_participant_list
            self.network.on_error = self.show_error
            
            self.setup_main_ui()
            
            self.network.start(ip)
            self.audio.start()
            
            self.is_connected = True
            
            # Start sending audio loop
            threading.Thread(target=self.send_audio_loop, daemon=True).start()
            
        except Exception as e:
            self.show_error(str(e))

    def send_audio_loop(self):
        while self.is_connected:
            try:
                data = self.audio.input_queue.get(timeout=1)
                if self.network:
                    self.network.send_audio(data)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in send loop: {e}")
                break

    def update_participant_list(self, participants):
        # UI updates must happen on the main thread
        self.after(0, lambda: self._update_participant_list_ui(participants))

    def _update_participant_list_ui(self, participants):
        # Clear frame
        for widget in self.scroll_participants.winfo_children():
            widget.destroy()
            
        for name in participants:
            lbl = ctk.CTkLabel(self.scroll_participants, text=f"• {name}", font=("Roboto", 14), anchor="w")
            lbl.pack(fill="x", padx=10, pady=2)

    def toggle_mute(self):
        state = not self.audio.muted
        self.audio.set_mute(state)
        self.btn_mute.configure(text="🔇" if state else "🎤", fg_color="red" if state else ["#3b8ed0", "#1f538d"])

    def toggle_deafen(self):
        state = not self.audio.deafened
        self.audio.set_deafen(state)
        self.btn_deafen.configure(text="✖️" if state else "🎧", fg_color="red" if state else ["#3b8ed0", "#1f538d"])

    def show_error(self, msg):
        print(f"Error: {msg}")
        # Could show a popup here

    def disconnect(self):
        self.is_connected = False
        if self.network: self.network.stop()
        self.audio.stop()
        self.setup_login_ui()

    def on_closing(self):
        self.is_connected = False
        if self.network: self.network.stop()
        self.audio.stop()
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    app = ClientApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
