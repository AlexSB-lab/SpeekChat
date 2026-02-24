import socket
import threading
import time
import uuid
import json
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser

class NetworkManager:
    """
    Handles peer discovery, host election, and heartbeat.
    """
    SERVICE_TYPE = "_speekchat._udp.local."
    
    def __init__(self, username, port=50005):
        self.id = str(uuid.uuid4())
        self.username = username
        self.port = port
        self.peers = {} # id: {username, address, last_seen}
        self.host_id = None
        self.is_running = False
        
        self.zeroconf = Zeroconf()
        self.browser = None
        
    def start(self):
        self.is_running = True
        
        # Register self
        desc = {'id': self.id, 'username': self.username}
        info = ServiceInfo(
            self.SERVICE_TYPE,
            f"{self.id}.{self.SERVICE_TYPE}",
            addresses=[socket.inet_aton("127.0.0.1")], # Simplified for now, in real use we'd get local IP
            port=self.port,
            properties=desc,
        )
        self.zeroconf.register_service(info)
        
        # Browse for others
        self.browser = ServiceBrowser(self.zeroconf, self.SERVICE_TYPE, self)
        
        # Election thread
        threading.Thread(target=self._election_loop, daemon=True).start()

    def remove_service(self, zc, type_, name):
        peer_id = name.split('.')[0]
        if peer_id in self.peers:
            del self.peers[peer_id]
            self._elect_host()

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            peer_id = info.properties.get(b'id', b'').decode()
            username = info.properties.get(b'username', b'').decode()
            if peer_id and peer_id != self.id:
                self.peers[peer_id] = {
                    'username': username,
                    'address': socket.inet_ntoa(info.addresses[0]),
                    'port': info.port,
                    'last_seen': time.time()
                }
                self._elect_host()

    def update_service(self, zc, type_, name):
        pass

    def _elect_host(self):
        # The host is the one with the lexicographically smallest ID
        all_ids = list(self.peers.keys()) + [self.id]
        all_ids.sort()
        self.host_id = all_ids[0]
        print(f"[Network] Elected host: {self.host_id} (Me: {self.id == self.host_id})")

    def _election_loop(self):
        while self.is_running:
            # Periodically re-verify peers if needed (Zeroconf usually handles this via remove_service)
            time.sleep(5)

    def stop(self):
        self.is_running = False
        self.zeroconf.unregister_all_services()
        self.zeroconf.close()

    @property
    def is_host(self):
        return self.host_id == self.id
