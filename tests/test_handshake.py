import socket
import threading
import time
import json
import sys
import os

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app.core.network_engine import NetworkEngine

def test_handshake():
    print("Starting Handshake Test...")
    
    # Start Server
    server = NetworkEngine(is_server=True)
    server.start()
    print("Server started on port", server.PORT)

    connected_event = threading.Event()
    
    # Start Client
    client = NetworkEngine(is_server=False, username="TestUser")
    
    def on_connected():
        print("Client: Connection confirmed!")
        connected_event.set()

    client.on_connected = on_connected
    
    print("Client: Attempting to connect to 127.0.0.1...")
    client.start("127.0.0.1")

    # Wait for connection (should happen within a few seconds)
    if connected_event.wait(timeout=10):
        print("SUCCESS: Handshake completed.")
    else:
        print("FAILURE: Handshake timed out.")

    # Cleanup
    print("Cleaning up...")
    client.stop()
    server.stop()
    time.sleep(1)
    print("Test finished.")

if __name__ == "__main__":
    test_handshake()
