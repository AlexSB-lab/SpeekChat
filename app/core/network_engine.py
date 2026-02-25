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
        self._stop_lock = threading.Lock()

    def start(self, server_ip=None):
        self.is_running = True
        
        # Start receiving BEFORE sending join request
        threading.Thread(target=self._receive_loop, daemon=True).start()

        if not self.is_server:
            if not server_ip:
                raise ValueError("Server IP required for client mode")
            self.server_addr = (server_ip, self.PORT)
            # Send join request
            self._send_command("JOIN", self.username)
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

            except OSError as e:
                if self.is_running:
                    # Ignore common shutdown socket errors
                    if e.errno not in [10022, 10038]:
                        print(f"[Network] Receive error: {e}")
                        if self.on_error: self.on_error(str(e))
                break
            except Exception as e:
                if self.is_running:
                    print(f"[Network] Unexpected error: {e}")
                    break

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
        # Payload here is data[1:]
        if not payload.startswith(b'SPK!'):
            return # Ignore non-audio or invalid packets

        audio_payload = payload[4:]

        if self.is_server:
            # Relay to everyone else
            sender_name = self.clients.get(addr, "Unknown")
            name_bytes = sender_name.encode()
            
            # Reconstruct: [1 (Type)] [b'SPK!'] [NameLen] [Name] [AudioData]
            # audio_payload[1:] skips the dummy NameLen (0) sent by the client
            relay_payload = bytes([1]) + b'SPK!' + bytes([len(name_bytes)]) + name_bytes + audio_payload[1:]
            
            for client_addr in list(self.clients.keys()):
                if client_addr != addr:
                    try:
                        self.sock.sendto(relay_payload, client_addr)
                    except:
                        pass
        else:
            # Client receives: [b'SPK!'] [NameLen (1)] [Name] [AudioData]
            # payload was data[1:], so it starts with b'SPK!'
            name_len = audio_payload[0]
            username = audio_payload[1:1+name_len].decode()
            audio_data = audio_payload[1+name_len:]
            
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
        
        # Audio packet: [1 (Type)] [b'SPK!'] [0 (Dummy NameLen)] [AudioData]
        payload = bytes([1]) + b'SPK!' + bytes([0]) + data
        try:
            self.sock.sendto(payload, self.server_addr)
        except Exception as e:
            print(f"Send audio error: {e}")

    def _send_command(self, cmd, args):
        try:
            msg = json.dumps({"cmd": cmd, "args": args}).encode()
            payload = bytes([0]) + msg
            if self.is_server:
                # Server rarely sends commands to everyone except participants update
                pass
            else:
                if self.server_addr and self.sock:
                    self.sock.sendto(payload, self.server_addr)
        except (OSError, AttributeError):
            pass # Socket likely closed or invalid during shutdown

    def _heartbeat_loop(self):
        while self.is_running:
            self._send_command("PING", None)
            time.sleep(5)

    def stop(self):
        with self._stop_lock:
            if not self.is_running:
                return
            self.is_running = False
            
            try:
                if not self.is_server and self.server_addr:
                    self._send_command("LEAVE", self.username)
            except:
                pass
            
            try:
                self.sock.close()
            except:
                pass

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
