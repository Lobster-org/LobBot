import os
import subprocess
import time
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ChangeHandler(FileSystemEventHandler):
    def __init__(self, process):
        self.process = process
        
    def on_modified(self, event):
        print(f"Change detected in {event.src_path}")
        self.process.terminate()
        time.sleep(1)
        self.process = subprocess.Popen(
            [sys.executable, "bot/main.py"],
            stdout=sys.stdout,
            stderr=sys.stderr
        )

if __name__ == "__main__":
    process = subprocess.Popen(
        [sys.executable, "bot/main.py"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    event_handler = ChangeHandler(process)
    observer = Observer()
    observer.schedule(event_handler, path="./bot", recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        process.terminate()
    observer.join()