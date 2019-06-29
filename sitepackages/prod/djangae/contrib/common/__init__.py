import threading
_thread_locals = threading.local()

def get_request():
    return getattr(_thread_locals, 'request', None)