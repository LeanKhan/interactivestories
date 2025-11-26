import multiprocessing

# Socket
bind = "unix:/srv/interactivestories/interactivestories.sock"

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120  # Increase if you have long-running requests
keepalive = 5

# Restart workers after handling this many requests (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "info"
accesslog = "/srv/interactivestories/logs/gunicorn_access.log"
errorlog = "/srv/interactivestories/logs/gunicorn_error.log"
capture_output = True

# Preload app for better memory efficiency
preload_app = True

# Worker lifecycle hooks
def on_starting(server):
    server.log.info("Gunicorn starting")

def worker_abort(worker):
    worker.log.error(f"Worker received SIGABRT - likely a timeout or memory issue")

def pre_request(worker, req):
    worker.log.debug(f"{req.method} {req.path}")