"""Process-wide lock so only one inference job runs at a time (models live in memory)."""
import threading

inference_lock = threading.Lock()
