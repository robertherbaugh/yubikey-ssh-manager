from flask import render_template, jsonify, request, send_from_directory, make_response
from application.ssh_manager import SSHManager
from application.logger import setup_logger
import os
import logging
import uuid

logger = logging.getLogger(__name__)

def setup_routes(app):
    # Allow CORS for all origins during testing
    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin')
        if origin in ['http://localhost:5000', 'http://127.0.0.1:5000']:
            response.headers.add('Access-Control-Allow-Origin', origin)
        else:
            response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    app.config['SECRET_KEY'] = os.urandom(24)
    ssh_manager = SSHManager()

    @app.route('/')
    def index():
        """Serve the main application page"""
        logger.debug("Serving index.html")
        return render_template('index.html')

    @app.route('/static/<path:filename>')
    def serve_static(filename):
        """Serve static files"""
        logger.debug(f"Serving static file: {filename}")
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
        return send_from_directory(os.path.join(frontend_dir, 'static'), filename)

    @app.route('/js/<path:filename>')
    def serve_js(filename):
        """Serve static JavaScript files"""
        logger.debug(f"Serving static file: {filename}")
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
        return send_from_directory(os.path.join(frontend_dir, 'js'), filename)

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

    @app.route('/api/yubikeys', methods=['GET'])
    def get_yubikeys():
        """Get list of connected YubiKeys"""
        try:
            yubikeys = ssh_manager.get_yubikeys()
            selected = ssh_manager.get_selected_yubikey()
            return jsonify({
                "yubikeys": yubikeys,
                "selected": selected
            })
        except Exception as e:
            logger.exception("Error getting YubiKeys")
            return jsonify({"yubikeys": [], "selected": None})

    @app.route('/api/yubikeys/select/<string:serial>', methods=['POST'])
    def select_yubikey(serial):
        """Select a YubiKey to use"""
        try:
            if ssh_manager.select_yubikey(serial):
                return jsonify({"success": True})
            return jsonify({"success": False, "message": "Failed to select YubiKey"})
        except Exception as e:
            logger.exception("Error selecting YubiKey")
            return jsonify({"success": False, "message": str(e)})

    @app.route('/api/servers')
    def get_servers():
        """Get list of servers"""
        try:
            servers = ssh_manager.get_servers()
            if not isinstance(servers, list):
                logger.error("Invalid server data type returned")
                return jsonify([])
            return jsonify(servers)
        except Exception as e:
            logger.exception("Error getting servers")
            return jsonify([])

    @app.route('/api/servers', methods=['POST'])
    def add_server():
        if ssh_manager.add_server(request.json):
            return jsonify({"success": True})
        return jsonify({"success": False}), 400

    @app.route('/api/servers/<string:server_id>', methods=['DELETE'])
    def delete_server(server_id):
        try:
            # Validate UUID format
            try:
                uuid_obj = uuid.UUID(server_id)
                server_id = str(uuid_obj)
            except ValueError:
                return jsonify({"success": False, "message": "Invalid server ID format"})

            if ssh_manager.delete_server(server_id):
                return jsonify({"success": True})
            return jsonify({"success": False, "message": "Failed to delete server"})
        except Exception as e:
            logger.exception("Error deleting server")
            return jsonify({"success": False, "message": str(e)})

    @app.route('/api/servers/<string:server_id>', methods=['PUT'])
    def update_server(server_id):
        try:
            # Validate UUID format
            try:
                uuid_obj = uuid.UUID(server_id)
                server_id = str(uuid_obj)
            except ValueError:
                return jsonify({"success": False, "message": "Invalid server ID format"})

            data = request.get_json()
            if ssh_manager.update_server(server_id, data):
                return jsonify({"success": True})
            return jsonify({"success": False, "message": "Failed to update server"})
        except Exception as e:
            logger.exception("Error updating server")
            return jsonify({"success": False, "message": str(e)})

    @app.route('/api/servers/<string:server_id>/connect', methods=['POST'])
    def connect_to_server(server_id):
        try:
            # Validate UUID format
            try:
                uuid_obj = uuid.UUID(server_id)
                server_id = str(uuid_obj)
            except ValueError:
                return jsonify({"success": False, "message": "Invalid server ID format"})

            result = ssh_manager.connect_to_server(server_id)
            return jsonify(result)
        except Exception as e:
            logger.exception("Error connecting to server")
            return jsonify({"success": False, "message": str(e)})

    @app.route('/api/deploy-key/<string:server_id>', methods=['POST'])
    def deploy_key(server_id):
        try:
            # Validate UUID format
            try:
                uuid_obj = uuid.UUID(server_id)
                server_id = str(uuid_obj)
            except ValueError:
                return jsonify({"success": False, "message": "Invalid server ID format"})

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
            result = ssh_manager.deploy_key(server, password, pin)
            logger.info(f"Key deployment result: {result}")
            
            return jsonify(result)
            
        except Exception as e:
            logger.exception("Error in deploy_key endpoint")
            return jsonify({"success": False, "message": str(e)})