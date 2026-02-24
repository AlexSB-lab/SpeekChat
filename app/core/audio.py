import sounddevice as sd
import numpy as np
import threading
import queue

class AudioEngine:
    """
    Handles audio capture and playback.
    Supports simultaneous playback of multiple streams.
    """
    def __init__(self, sample_rate=44100, channels=1, chunk_size=1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        
        self.input_queue = queue.Queue()
        self.output_queues = {} # peer_id: queue.Queue
        
        self.is_running = False
        self.stream = None
        self.mute = False

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
            
        # Capture input
        if not self.mute:
            self.input_queue.put(indata.copy())
        
        # Mix output from all peer streams
        mixed_audio = np.zeros((frames, self.channels), dtype='int16')
        
        for peer_id, q in list(self.output_queues.items()):
            try:
                data = q.get_nowait()
                # Simple additive mixing (might need normalization later to prevent clipping)
                peer_audio = np.frombuffer(data, dtype='int16').reshape(-1, self.channels)
                mixed_audio += (peer_audio // 2) # Reduce volume to prevent overflow during mix
            except queue.Empty:
                pass
                
        outdata[:] = mixed_audio.tobytes()

    def add_peer_stream(self, peer_id):
        self.output_queues[peer_id] = queue.Queue()

    def remove_peer_stream(self, peer_id):
        if peer_id in self.output_queues:
            del self.output_queues[peer_id]

    def receive_audio(self, peer_id, data):
        if peer_id in self.output_queues:
            self.output_queues[peer_id].put(data)

    def stop(self):
        self.is_running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
