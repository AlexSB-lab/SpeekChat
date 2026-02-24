import socket
import threading
import time
from .audio import AudioEngine
from .network import NetworkManager

class CommunicationBridge:
    """
    Connects NetworkManager and AudioEngine.
    Handles the actual UDP audio data transfer between peers.
    """
    def __init__(self, network_manager, audio_engine):
        self.nm = network_manager
        self.ae = audio_engine
        self.is_running = False
        
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Allow multiple instances on the same machine to bind to the same port for local testing
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_sock.bind(('', self.nm.port))
        
    def start(self):
        self.is_running = True
        threading.Thread(target=self._send_loop, daemon=True).start()
        threading.Thread(target=self._receive_loop, daemon=True).start()

    def _send_loop(self):
        while self.is_running:
            try:
                # Get audio data from engine
                data = self.ae.input_queue.get(timeout=1)
                
                # Send to all known peers
                # In a more optimized version, we might only send to the host 
                # or use multicast, but for small groups P2P is fine.
                for peer_id, info in self.nm.peers.items():
                    try:
                        # Prepend ID so receiver knows who spoke
                        payload = self.nm.id.encode() + b'|' + data.tobytes()
                        self.udp_sock.sendto(payload, (info['address'], info['port']))
                    except Exception as e:
                        print(f"[Comm] Send error to {peer_id}: {e}")
            except Exception:
                continue

    def _receive_loop(self):
        while self.is_running:
            try:
                data, addr = self.udp_sock.recvfrom(4096)
                if b'|' in data:
                    peer_id_bytes, audio_data = data.split(b'|', 1)
                    peer_id = peer_id_bytes.decode()
                    
                    # If we don't know this peer stream yet, add it
                    if peer_id not in self.ae.output_queues:
                        self.ae.add_peer_stream(peer_id)
                        
                    self.ae.receive_audio(peer_id, audio_data)
            except Exception as e:
                if self.is_running:
                    print(f"[Comm] Receive error: {e}")

    def stop(self):
        self.is_running = False
        self.udp_sock.close()
