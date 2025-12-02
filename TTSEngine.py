"""
Text-to-Speech Engine for NaviGlass
Wrapper around Piper for offline text-to-speech with queue management.
"""

import threading
import queue
import os
import subprocess
import time


PIPER_BINARY = "./piper/piper"
VOICE_MODEL = "./piper/en_US-amy-low.onnx"


class TTSEngine:
    
    def __init__(self, rate: float = 0.82, volume: float = 0.5, sample_rate: int = 16200): # Initialize TTS engine with default rate (wpm) and volume (0.0 to 1.0)

        self.speech_queue = queue.Queue()
        self.is_running = False
        self.worker_thread = None
        self.pipeline_process = None

        self.rate = rate
        self.sample_rate = sample_rate
        self.set_volume(volume)
        
        if not os.path.exists(PIPER_BINARY) or not os.path.exists(VOICE_MODEL):
            print("ERROR: Piper TTS files not found! Falling back to silent mode.")
            self.piper_ready = False
        else:
            self.piper_ready = True
            print("Piper Neural TTS Initialized (Voice: Amy).")


    def set_volume(self, volume: float): # From 0.0 - 1.0 to %
        self.volume = max(0.0, min(1.0, volume))
        vol_pct = int(self.volume * 100)
        
        try:
            subprocess.run(f"amixer -q set Master {vol_pct}%", shell=True)
            print(f"System volume set to {vol_pct}%")
        except:
            print("Warning: Failed to set system volume via amixer.")
            pass


    def start_pipeline(self):
        if not self.piper_ready: return
        
        self.kill_pipeline()

        # THE PIPELINE COMMAND
        # We run this as one persistent shell command.
        # Piper reads from stdin, pipes audio to aplay's stdin.
        # 2>/dev/null hides all the "Loaded voice" logs.
        cmd = (
            f"{PIPER_BINARY} --model {VOICE_MODEL} --output_raw "
            f"--length_scale {self.rate} --sentence_silence 0 "
            f"| aplay -r {self.sample_rate} -f S16_LE -t raw - --buffer-size=1024 2>/dev/null"
        )
        
        try:
            self.pipeline_process = subprocess.Popen( # shell=True allows the '|' pipe to work naturally
                cmd,
                shell=True,
                stdin=subprocess.PIPE,   # We write text here
                stderr=subprocess.DEVNULL # Silence logs
            )
            print("TTS Pipeline Started.")
        except Exception as e:
            print(f"Failed to start TTS pipeline: {e}")


    def kill_pipeline(self):
        if self.pipeline_process:
            try:
                self.pipeline_process.terminate()
                self.pipeline_process.wait(timeout=0.5)
            except:
                pass # Force kill happens on exit usually
        self.pipeline_process = None
        

    def start(self): # Start the worker thread
        if not self.is_running:
            self.is_running = True
            self.start_pipeline()
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
    

    def stop(self): # Stop the thread
        self.is_running = False
        self.speech_queue.put(None)
        if self.worker_thread:
            self.worker_thread.join()
        self.kill_pipeline()
    

    def speak(self, text: str, interrupt: bool = False):
        if not text: return
        if interrupt:
            self.clear_queue()
            self.kill_pipeline() # Hard stop the current audio
        self.speech_queue.put(text)


    def _speak_persistent(self, text: str):
        if not self.pipeline_process or self.pipeline_process.poll() is not None:
            self.start_pipeline()
            time.sleep(0.2) # Give it a moment to load the model

        try:
            print(f"[Amy]: {text}")
            clean_text = text.replace('\n', ' ').strip() + '\n'
            
            if self.pipeline_process and self.pipeline_process.stdin:
                self.pipeline_process.stdin.write(clean_text.encode('utf-8'))
                self.pipeline_process.stdin.flush()
                
        except Exception as e:
            print(f"Pipe Write Error: {e}")
            self.kill_pipeline() # If write fails, the pipe is likely broken. Restart next time.


    def _worker(self):
        while self.is_running:
            try:
                text = self.speech_queue.get(timeout=1)
                if text is None: 
                    self.speech_queue.task_done() 
                    break 
                self._speak_persistent(text)
                self.speech_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"TTS Worker Error: {e}")
    

    def clear_queue(self):
        with self.speech_queue.mutex:
            self.speech_queue.queue.clear()