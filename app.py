import rumps
import webbrowser
import threading
import logging
import time
import json
from flask import Flask, render_template, jsonify, request, send_from_directory, make_response
from flask_cors import CORS
from ssh_manager import SSHManager
from pathlib import Path
import os
import atexit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create a logger for this module
logger = logging.getLogger(__name__)

# Create a separate logger for YubiKey monitoring
yubikey_logger = logging.getLogger('yubikey_monitor')
yubikey_logger.setLevel(logging.WARNING)

# Global flag for controlling the monitor thread
monitor_running = True

# Tray application class definition
class YubiKeySSHManagerApp(rumps.App):
    def __init__(self):
        super(YubiKeySSHManagerApp, self).__init__("🔐")
        self.ssh_manager = ssh_manager  # Use the global ssh_manager instance
        
        # Create Connect menu with initial submenu
        connect_menu = rumps.MenuItem("Connect")
        for item in self.create_server_submenu():
            connect_menu.add(item)
        
        # Set up the menu structure
        self.menu = [
            rumps.MenuItem("Open Web Interface"),
            None,  # Add a separator
            connect_menu,
            None,  # Add another separator
            # rumps.MenuItem("Quit", callback=self.quit_app)
        ]
        
        # Start a timer to update the server list periodically
        self.timer = rumps.Timer(self.update_server_menu, 5)
        self.timer.start()

    def create_server_submenu(self):
        """Create a submenu with the list of configured servers"""
        servers = self.ssh_manager.get_servers()
        submenu = []
        
        if not servers:
            no_servers = rumps.MenuItem("No servers configured")
            no_servers.state = -1  # This makes the item disabled
            submenu.append(no_servers)
        else:
            for server in servers:
                server_name = f"{server['name']} ({server['username']}@{server['hostname']})"
                menu_item = rumps.MenuItem(
                    server_name, 
                    callback=lambda x, s=server: self.connect_to_server(s['id'])
                )
                submenu.append(menu_item)
        
        return submenu

    def update_server_menu(self, _):
        """Update the server submenu periodically"""
        try:
            # Get the Connect menu
            connect_menu = self.menu["Connect"]
            if connect_menu is None:
                return
                
            # Remove existing items
            while len(connect_menu) > 0:
                connect_menu.pop(0)
            
            # Add new items
            for item in self.create_server_submenu():
                connect_menu.add(item)
        except Exception as e:
            logger.error(f"Error updating server menu: {e}")

    def connect_to_server(self, server_id):
        """Handle server connection from menu"""
        result = self.ssh_manager.connect_to_server(server_id)
        if not result['success']:
            rumps.notification(
                title='Connection Failed',
                subtitle='',
                message=result['message']
            )

    @rumps.clicked("Open Web Interface")
    def open_web(self, _):
        webbrowser.open('http://127.0.0.1:5000')

    def quit_app(self, _):
        """Quit the application"""
        cleanup()
        rumps.quit_application()

# Flask web application
app = Flask(__name__, static_folder='static', static_url_path='/static')

# Allow CORS for all origins during testing
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

app.config['SECRET_KEY'] = os.urandom(24)
ssh_manager = SSHManager()

@app.route('/')
def index():
    """Serve the main application page"""
    logger.debug("Serving index.html")
    return render_template('index.html')

@app.route('/js/<path:filename>')
def serve_static(filename):
    """Serve static JavaScript files"""
    logger.debug(f"Serving static file: {filename}")
    return send_from_directory('static/js', filename)

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/api/yubikey-status', methods=['GET'])
def yubikey_status():
    """Get YubiKey status"""
    try:
        return jsonify(ssh_manager.get_yubikey_status())
    except Exception as e:
        logger.error(f"Error getting YubiKey status: {e}")
        error_response = jsonify({"error": str(e), "detected": False})
        return error_response, 500

@app.route('/api/yubikey-status', methods=['OPTIONS'])
def yubikey_status_options():
    """Handle OPTIONS request for YubiKey status"""
    response = make_response()
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response

@app.route('/api/servers')
def get_servers():
    """Get list of servers"""
    try:
        servers = ssh_manager.get_servers()
        return jsonify(servers)
    except Exception as e:
        logger.error(f"Error getting servers: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers', methods=['POST'])
def add_server():
    if ssh_manager.add_server(request.json):
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/api/servers/<int:server_id>', methods=['DELETE'])
def delete_server(server_id):
    try:
        if ssh_manager.delete_server(server_id):
            return jsonify({"success": True})
        return jsonify({"success": False, "message": "Failed to delete server"})
    except Exception as e:
        logger.exception("Error deleting server")
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/servers/<int:server_id>', methods=['PUT'])
def update_server(server_id):
    """Update server details"""
    try:
        if ssh_manager.update_server(server_id, request.json):
            return jsonify({"success": True})
        return jsonify({"success": False, "message": "Server not found"})
    except Exception as e:
        logger.exception("Error updating server")
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/connect/<server_id>', methods=['POST', 'OPTIONS'])
def connect_to_server(server_id):
    """Handle SSH connection request with YubiKey authentication"""
    if request.method == 'OPTIONS':
        return '', 200

    try:
        # Get server details
        server = ssh_manager.get_server(server_id)
        if not server:
            return jsonify({'success': False, 'message': 'Server not found'}), 404

        # Verify YubiKey is present
        yubikey_status = ssh_manager.get_yubikey_status()
        if not yubikey_status['connected']:
            return jsonify({'success': False, 'message': yubikey_status['message']}), 400

        # Attempt SSH connection
        result = ssh_manager.connect_to_server(server_id)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error connecting to server: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/deploy-key/<int:server_id>', methods=['POST'])
def deploy_key(server_id):
    try:
        logger.info(f"Starting key deployment for server ID: {server_id}")
        data = request.get_json()
        pin = data.get('pin') if data else None
        password = data.get('password') if data else None
        
        if not pin or not password:
            logger.error("Missing PIN or password in request")
            return jsonify({"success": False, "message": "PIN and password are required"})
            
        logger.debug("Looking up server details")
        server = ssh_manager.get_server(server_id)
        if not server:
            logger.error(f"Server not found with ID: {server_id}")
            return jsonify({"success": False, "message": "Server not found"})
            
        logger.info("Starting key deployment process")
        server_data = {
            'id': str(server_id),
            'name': server['name'],
            'hostname': server['hostname'],
            'username': server['username'],
            'port': server['port']
        }
        
        logger.debug("Calling SSHManager.deploy_key")
        result = ssh_manager.deploy_key(server_data, password, pin)
        logger.info(f"Key deployment result: {result}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.exception("Error in deploy_key endpoint")
        return jsonify({"success": False, "message": str(e)})

def yubikey_monitor():
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
    monitor_thread = threading.Thread(target=yubikey_monitor)
    monitor_thread.daemon = True  # Make thread a daemon so it exits when main thread exits
    monitor_thread.start()
    return monitor_thread

def cleanup():
    """Cleanup function to handle application shutdown"""
    global monitor_running
    logger.info("Cleaning up before shutdown...")
    monitor_running = False
    time.sleep(1)  # Give monitor thread time to exit cleanly
    logger.info("Cleanup complete")

def run_app():
    """Run the Flask application"""
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

def run_tray():
    """Run the tray application"""
    YubiKeySSHManagerApp().run()

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
        cleanup()
    except Exception as e:
        logger.exception("Error in main thread")
        cleanup()
