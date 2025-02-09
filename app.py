import rumps
import webbrowser
import threading
import time
import json
from flask import Flask, render_template, jsonify, request, send_from_directory, make_response
from flask_cors import CORS
from application.logger import setup_logger
from application.ssh_manager import SSHManager
from application.mac_trayicon import TrayApplication
from backend.routes import setup_routes
from pathlib import Path
import os
import atexit
import uuid

logger, yubikey_logger = setup_logger()

# Create SSH manager instance
ssh_manager = SSHManager()

# Global flag for controlling the monitor thread
monitor_running = True

# Flask web application
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend')
app = Flask(__name__, 
           static_folder=os.path.join(frontend_dir, 'static'),
           static_url_path='/static',
           template_folder=os.path.join(frontend_dir, 'templates'))

# Allow CORS
CORS(app)

# Setup routes
setup_routes(app)

def yubikey_monitor(ssh_manager):
    """Background thread to monitor YubiKey status"""
    global monitor_running
    prev_status = None
    while monitor_running:
        try:
            current_status = ssh_manager.get_yubikey_status()
            if current_status != prev_status:
                yubikey_logger.info(f"YubiKey status changed: {current_status}")
                prev_status = current_status
        except Exception as e:
            yubikey_logger.error(f"Error in YubiKey monitor: {e}")
        time.sleep(1)
    yubikey_logger.info("YubiKey monitor thread stopping")

def run_yubikey_monitor():
    """Run the YubiKey monitor thread"""
    monitor_thread = threading.Thread(target=yubikey_monitor, args=(ssh_manager,))
    monitor_thread.daemon = True  # Make thread a daemon so it exits when main thread exits
    monitor_thread.start()
    return monitor_thread

def cleanup():
    """Cleanup function to handle application shutdown"""
    global monitor_running
    logger.info("Starting cleanup process...")
    
    # Stop the YubiKey monitor thread
    monitor_running = False
    
    # Stop Flask server
    func = request.environ.get('werkzeug.server.shutdown')
    if func is not None:
        logger.info("Shutting down Flask server...")
        func()
    
    # Clean up any remaining resources
    try:
        import multiprocessing.resource_tracker
        multiprocessing.resource_tracker._resource_tracker.clear()
    except Exception as e:
        logger.error(f"Error cleaning up resources: {e}")
    
    logger.info("Cleanup complete")

def quit_application():
    """Quit the entire application"""
    cleanup()
    # Force exit after cleanup
    os._exit(0)

def run_app():
    """Run the Flask application"""
    app = Flask(__name__,
                template_folder='frontend/templates',
                static_folder='frontend/static')
    setup_routes(app)
    
    # Add cleanup endpoint
    @app.route('/shutdown', methods=['POST'])
    def shutdown():
        quit_application()
        return 'Server shutting down...'
    
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)

def run_tray():
    """Run the tray application"""
    app = TrayApplication(quit_callback=quit_application)
    app.run()

if __name__ == "__main__":
    try:
        # Create necessary directories
        os.makedirs('keys', exist_ok=True)
        
        # Start YubiKey monitor in a separate thread
        monitor_thread = run_yubikey_monitor()
        
        # Register cleanup function to run at exit
        atexit.register(cleanup)
        
        # Start Flask in a separate thread
        flask_thread = threading.Thread(target=run_app)
        flask_thread.daemon = True
        flask_thread.start()
        logger.info("Flask server started")
        
        # Run the tray application in the main thread
        logger.info("Starting tray application")
        run_tray()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        quit_application()
    except Exception as e:
        logger.exception("Unexpected error occurred")
        quit_application()
