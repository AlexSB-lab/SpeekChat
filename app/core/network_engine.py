import socket
import threading
import time
import json
import requests

class NetworkEngine:
    PORT = 50005
    BUFFER_SIZE = 8192

    def __init__(self, is_server=False, username="Unknown"):
        self.is_server = is_server
        self.username = username
        self.is_running = False
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        if self.is_server:
            self.sock.bind(('', self.PORT))
            self.clients = {} # (addr, port): username
        else:
            self.server_addr = None
            self.participants = []

        self.on_audio_received = None # Callback(username, data)
        self.on_participants_updated = None # Callback(list)
        self.on_error = None # Callback(msg)

    def start(self, server_ip=None):
        self.is_running = True
        if not self.is_server:
            if not server_ip:
                raise ValueError("Server IP required for client mode")
            self.server_addr = (server_ip, self.PORT)
            # Send join request
            self._send_command("JOIN", self.username)
        
        threading.Thread(target=self._receive_loop, daemon=True).start()
        if not self.is_server:
            threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def _receive_loop(self):
        while self.is_running:
            try:
                data, addr = self.sock.recvfrom(self.BUFFER_SIZE)
                if not data: continue

                # Packet format: [TYPE (1 byte)] [DATA...]
                # TYPE 0: Command (JSON)
                # TYPE 1: Audio
                
                msg_type = data[0]
                payload = data[1:]

                if msg_type == 0: # Command
                    self._handle_command(payload, addr)
                elif msg_type == 1: # Audio
                    self._handle_audio(payload, addr)

            except Exception as e:
                if self.is_running:
                    print(f"[Network] Receive error: {e}")
                    if self.on_error: self.on_error(str(e))

    def _handle_command(self, payload, addr):
        try:
            cmd_data = json.loads(payload.decode())
            cmd = cmd_data.get("cmd")
            args = cmd_data.get("args")

            if self.is_server:
                if cmd == "JOIN":
                    username = args
                    self.clients[addr] = username
                    print(f"[Server] {username} joined from {addr}")
                    self._broadcast_participants()
                elif cmd == "LEAVE":
                    if addr in self.clients:
                        del self.clients[addr]
                        self._broadcast_participants()
                elif cmd == "PING":
                    # Just an alive Signal
                    pass
            else:
                if cmd == "PARTICIPANTS":
                    self.participants = args
                    if self.on_participants_updated:
                        self.on_participants_updated(self.participants)
        except Exception as e:
            print(f"Command error: {e}")

    def _handle_audio(self, payload, addr):
        if self.is_server:
            # Relay to everyone else
            # Inject sender name length and name into payload for clients
            sender_name = self.clients.get(addr, "Unknown")
            name_bytes = sender_name.encode()
            relay_payload = bytes([1, len(name_bytes)]) + name_bytes + payload
            
            for client_addr in list(self.clients.keys()):
                if client_addr != addr:
                    try:
                        self.sock.sendto(relay_payload, client_addr)
                    except:
                        pass
        else:
            # Client receives: [1 (Type)] [NameLen (1)] [Name] [AudioData]
            # Actually the payload passed here is already without the first 1
            name_len = payload[0]
            username = payload[1:1+name_len].decode()
            audio_data = payload[1+name_len:]
            
            if self.on_audio_received:
                self.on_audio_received(username, audio_data)

    def _broadcast_participants(self):
        if not self.is_server: return
        msg = json.dumps({"cmd": "PARTICIPANTS", "args": list(self.clients.values())}).encode()
        payload = bytes([0]) + msg
        for client_addr in self.clients:
            try:
                self.sock.sendto(payload, client_addr)
            except:
                pass

    def send_audio(self, data):
        if self.is_server: return # Server only relays
        if not self.server_addr: return
        
        # Audio packet: [1 (Type)] [AudioData]
        payload = bytes([1]) + data
        try:
            self.sock.sendto(payload, self.server_addr)
        except Exception as e:
            print(f"Send audio error: {e}")

    def _send_command(self, cmd, args):
        msg = json.dumps({"cmd": cmd, "args": args}).encode()
        payload = bytes([0]) + msg
        if self.is_server:
            # Server rarely sends commands to everyone except participants update
            pass
        else:
            if self.server_addr:
                self.sock.sendto(payload, self.server_addr)

    def _heartbeat_loop(self):
        while self.is_running:
            self._send_command("PING", None)
            time.sleep(5)

    def stop(self):
        self.is_running = False
        if not self.is_server and self.server_addr:
            self._send_command("LEAVE", self.username)
        self.sock.close()

    @staticmethod
    def get_public_ip():
        try:
            return requests.get('https://api.ipify.org').text
        except:
            return "Unknown (No Internet?)"

    @staticmethod
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
