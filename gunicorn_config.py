"""
Gunicorn configuration for production
File: gunicorn_config.py
"""

import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
backlog = 2048

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'gevent')
worker_connections = 1000
max_requests = 1000  # Restart workers after this many requests (prevents memory leaks)
max_requests_jitter = 50  # Randomize restart to avoid all workers restarting simultaneously
timeout = 30
graceful_timeout = 30
keepalive = 5

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Server mechanics
daemon = False
pidfile = '/tmp/gunicorn.pid'
user = None  # Run as current user (appuser in container)
group = None
tmp_upload_dir = '/tmp'

# Logging
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')  # stdout
errorlog = os.environ.get('GUNICORN_ERROR_LOG', '-')  # stderr
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'prescription-validator'

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized"""
    server.log.info("Starting Gunicorn server")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP"""
    server.log.info("Reloading Gunicorn server")

def when_ready(server):
    """Called just after the server is started"""
    server.log.info("Gunicorn server is ready. Spawning workers")

def pre_fork(server, worker):
    """Called just before a worker is forked"""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked"""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def post_worker_init(worker):
    """Called just after a worker has initialized the application"""
    worker.log.info(f"Worker initialized (pid: {worker.pid})")

def worker_int(worker):
    """Called when a worker receives the INT or QUIT signal"""
    worker.log.info(f"Worker received INT or QUIT signal (pid: {worker.pid})")

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal"""
    worker.log.info(f"Worker received SIGABRT signal (pid: {worker.pid})")

def pre_exec(server):
    """Called just before a new master process is forked"""
    server.log.info("Forked child, re-executing.")

def pre_request(worker, req):
    """Called just before a worker processes the request"""
    worker.log.debug(f"{req.method} {req.path}")

def post_request(worker, req, environ, resp):
    """Called after a worker processes the request"""
    pass

def child_exit(server, worker):
    """Called when a worker exits"""
    server.log.info(f"Worker exited (pid: {worker.pid})")

def worker_exit(server, worker):
    """Called when a worker is being shut down"""
    server.log.info(f"Worker shutdown (pid: {worker.pid})")

def nworkers_changed(server, new_value, old_value):
    """Called when the number of workers changes"""
    server.log.info(f"Number of workers changed from {old_value} to {new_value}")

def on_exit(server):
    """Called just before the master process exits"""
    server.log.info("Shutting down Gunicorn server")
