import sys
import random
from app.core.network import NetworkManager
from app.core.audio import AudioEngine
from app.core.comm import CommunicationBridge
from app.gui.main_window import MainApp

def main():
    # In a real app, we'd have a login screen. For now, random name.
    username = f"User_{random.randint(1000, 9999)}"
    print(f"Starting SpeekChat as {username}...")
    
    # Initialize Core
    nm = NetworkManager(username)
    ae = AudioEngine()
    cb = CommunicationBridge(nm, ae)
    
    # Start Cores
    ae.start()
    nm.start()
    cb.start()
    
    # Start GUI
    app = MainApp(nm, ae, cb)
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

if __name__ == "__main__":
    main()


# install with pip venv: pip install -r requirements.txt