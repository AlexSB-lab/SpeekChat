import customtkinter as ctk
import threading
import time

class MainApp(ctk.CTk):
    def __init__(self, network_manager, audio_engine, comm_bridge):
        super().__init__()
        
        self.nm = network_manager
        self.ae = audio_engine
        self.cb = comm_bridge
        
        self.title(f"SpeekChat - {self.nm.username}")
        self.geometry("400x500")
        
        # Design Setup
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self._setup_ui()
        self._update_loop()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        self.header = ctk.CTkLabel(self, text="SpeekChat", font=("Outfit", 24, "bold"))
        self.header.grid(row=0, column=0, pady=20)
        
        # Peer List
        self.peer_frame = ctk.CTkScrollableFrame(self, label_text="Participants")
        self.peer_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        
        self.peer_labels = {} # id: label_widget
        
        # Controls
        self.controls = ctk.CTkFrame(self)
        self.controls.grid(row=2, column=0, sticky="ew", padx=20, pady=20)
        
        self.mute_btn = ctk.CTkButton(self.controls, text="Mute", command=self._toggle_mute)
        self.mute_btn.pack(side="left", padx=10, fill="x", expand=True)
        
        self.status_label = ctk.CTkLabel(self.controls, text="Status: Connecting...")
        self.status_label.pack(side="right", padx=10)

    def _toggle_mute(self):
        self.ae.mute = not self.ae.mute
        self.mute_btn.configure(text="Unmute" if self.ae.mute else "Mute")

    def _update_loop(self):
        # Update Host Status
        role = "Host" if self.nm.is_host else "Client Connection"
        host_name = "Self" if self.nm.is_host else (self.nm.peers.get(self.nm.host_id, {}).get('username', 'Unknown') if self.nm.host_id else "Searching...")
        self.status_label.configure(text=f"Role: {role}\nHost: {host_name}")
        
        # Refresh Peer List
        current_peers = self.nm.peers
        
        # Add new peers
        for pid, info in current_peers.items():
            if pid not in self.peer_labels:
                lbl = ctk.CTkLabel(self.peer_frame, text=f"• {info['username']}")
                lbl.pack(anchor="w", padx=10)
                self.peer_labels[pid] = lbl
                
        # Remove old peers
        to_remove = []
        for pid in self.peer_labels:
            if pid not in current_peers:
                self.peer_labels[pid].destroy()
                to_remove.append(pid)
        for pid in to_remove:
            del self.peer_labels[pid]
            
        self.after(1000, self._update_loop)

    def on_closing(self):
        self.cb.stop()
        self.ae.stop()
        self.nm.stop()
        self.destroy()
