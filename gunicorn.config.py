import multiprocessing

# Socket
bind = "unix:/srv/interactivestories/interactivestories.sock"

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 600
keepalive = 5

# Restart workers after handling this many requests (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "warning"
accesslog = "/srv/interactivestories/logs/gunicorn_access.log"
errorlog = "/srv/interactivestories/logs/gunicorn_error.log"
capture_output = True

preload_app = True

def on_starting(server):
    server.log.info("Gunicorn starting")

def worker_abort(worker):
    worker.log.error(f"Worker received SIGABRT - likely a timeout or memory issue")

def pre_request(worker, req):
    worker.log.debug(f"{req.method} {req.path}")