import sounddevice as sd
import numpy as np
import threading
import queue
import zlib
import time

class AudioHandler:
    def __init__(self, sample_rate=16000, channels=1, chunk_size=1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        
        self.input_queue = queue.Queue()
        self.output_queues = {} # username: queue.Queue
        
        self.is_running = False
        self.stream = None
        self.muted = False
        self.deafened = False
        
        self.speaking_states = {} # username: timestamp
        self.VAD_THRESHOLD = 500 # Adjust if needed
        
        self._lock = threading.Lock()

    def start(self):
        self.is_running = True
        self.stream = sd.RawStream(
            samplerate=self.sample_rate,
            blocksize=self.chunk_size,
            dtype='int16',
            channels=self.channels,
            callback=self._audio_callback
        )
        self.stream.start()

    def _audio_callback(self, indata, outdata, frames, time, status):
        if status:
            print(f"[Audio] Status: {status}")

        # Capture
        if not self.muted:
            # Compress data before putting in queue for networking
            try:
                compressed = zlib.compress(bytes(indata))
                self.input_queue.put(compressed)
            except Exception as e:
                print(f"[Audio] Capture error: {e}")
        
        # Simple VAD for local user
        try:
            audio_data = np.frombuffer(indata, dtype='int16').astype(np.float32)
            rms = np.sqrt(np.mean(audio_data**2))
            if rms > self.VAD_THRESHOLD:
                self.speaking_states["Me"] = time.time()
        except:
            pass

        # Playback
        mixed_audio = np.zeros((frames, self.channels), dtype='int16')
        
        if not self.deafened:
            with self._lock:
                for username, q in list(self.output_queues.items()):
                    try:
                        data = q.get_nowait()
                        if not data or len(data) < 2:
                            continue
                            
                        # Decompress
                        decompressed = zlib.decompress(data)
                        peer_raw = np.frombuffer(decompressed, dtype='int16').astype(np.float32)
                        
                        # VAD for peer
                        rms = np.sqrt(np.mean(peer_raw**2))
                        if rms > self.VAD_THRESHOLD:
                            self.speaking_states[username] = time.time()

                        peer_audio = peer_raw.astype(np.int16).reshape(-1, self.channels)

                        # Ensure shape matches (trim or pad if necessary)
                        if peer_audio.shape[0] != frames:
                            # print(f"[Audio] Resizing peer audio from {peer_audio.shape[0]} to {frames}")
                            if peer_audio.shape[0] > frames:
                                peer_audio = peer_audio[:frames]
                            else:
                                pad = np.zeros((frames - peer_audio.shape[0], self.channels), dtype='int16')
                                peer_audio = np.vstack((peer_audio, pad))

                        # Simple additive mixing
                        mixed_audio = np.add(mixed_audio, peer_audio // 2)
                    except queue.Empty:
                        pass
                    except Exception as e:
                        print(f"[Audio] Playback error for {username}: {e}")
        
        outdata[:] = mixed_audio.tobytes()

    def add_user(self, username):
        with self._lock:
            if username not in self.output_queues:
                self.output_queues[username] = queue.Queue()

    def remove_user(self, username):
        with self._lock:
            if username in self.output_queues:
                del self.output_queues[username]

    def receive_audio(self, username, data):
        with self._lock:
            if username not in self.output_queues:
                self.output_queues[username] = queue.Queue()
            self.output_queues[username].put(data)

    def set_mute(self, state):
        self.muted = state

    def set_deafen(self, state):
        self.deafened = state

    def stop(self):
        with self._lock:
            if not self.is_running:
                return
            self.is_running = False
            
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except:
                    pass
                self.stream = None
