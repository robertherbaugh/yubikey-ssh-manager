import os
import json
from pathlib import Path
import paramiko
import logging
from ykman.device import list_all_devices
from yubikit.piv import PivSession, SLOT
from yubikit.management import ManagementSession
from typing import Dict, List, Optional, Tuple
import subprocess
import tempfile
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)

class SSHManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        self.app_dir = Path.home() / ".yubikey-ssh-manager"
        self.servers_file = self.app_dir / "servers.json"
        self.selected_yubikey_file = self.app_dir / "selected_yubikey.json"
        self.keys_dir = self.app_dir / "keys"
        
        # Create the application directories if they don't exist
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        
        # Create the servers file if it doesn't exist
        self.servers_file.touch(exist_ok=True)
        if not self.servers_file.read_text():
            self.servers_file.write_text('[]')
            
        # Create the selected YubiKey file if it doesn't exist
        self.selected_yubikey_file.touch(exist_ok=True)
        if not self.selected_yubikey_file.read_text():
            self.selected_yubikey_file.write_text('{}')

    def get_yubikey_status(self) -> Dict:
        """Check if YubiKey is present and get its status."""
        try:
            # Try to list all YubiKeys
            device_list = list_all_devices()
            if not device_list:
                return {"connected": False, "message": "No YubiKey detected"}
            
            #self.logger.debug("Found %d YubiKey(s)", len(device_list))
            return {"connected": True, "message": f"Found {len(device_list)} YubiKey(s)"}
                
        except Exception as e:
            self.logger.warning("Error checking YubiKey status: %s", str(e))
            return {"connected": False, "message": f"Error detecting YubiKey: {str(e)}"}

    def get_or_generate_key(self, device_info, pin: str) -> Optional[str]:
        """Get or generate SSH key for the YubiKey."""
        try:
            device, info = device_info
            key_file = self.keys_dir / f"yubikey_{info.serial}_pub.txt"
            self.logger.debug(f"Attempting to get/generate key for YubiKey {info.serial}")
            
            # If we already have a key for this YubiKey, return it
            if key_file.exists():
                self.logger.debug(f"Found existing key at {key_file}")
                return key_file.read_text().strip()
            
            self.logger.debug("No existing key found, generating new key...")
            # Create temporary files for key generation
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.pub', delete=False) as pub_key:
                self.logger.debug(f"Created temporary file for public key: {pub_key.name}")
                
                # Generate RSA key in slot 9a
                cmd = ['ykman', '--device', str(info.serial), 'piv', 'keys', 'generate', 
                      '--pin-policy', 'ONCE', 
                      '--pin', pin,
                      '--algorithm', 'RSA2048',
                      '9a', pub_key.name]
                self.logger.debug(f"Running command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    self.logger.error(f"Error generating key: {result.stderr}")
                    self.logger.error(f"Command output: {result.stdout}")
                    return None
                
                self.logger.debug("Key generated successfully, converting to SSH format...")
                # Convert the public key to SSH format
                cmd = ['ssh-keygen', '-i', '-m', 'PKCS8', '-f', pub_key.name]
                self.logger.debug(f"Running command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    ssh_key = result.stdout.strip()
                    self.logger.debug("Successfully converted key to SSH format")
                    # Save the key
                    key_file.write_text(ssh_key)
                    self.logger.debug(f"Saved SSH key to {key_file}")
                    return ssh_key
                else:
                    self.logger.error(f"Error converting key to SSH format: {result.stderr}")
                    self.logger.error(f"Command output: {result.stdout}")
                    return None
                    
        except Exception as e:
            self.logger.exception("Error generating SSH key")
            return None

    def get_yubikeys(self) -> List[Dict]:
        """Get list of connected YubiKeys."""
        try:
            devices = list_all_devices()
            yubikeys = []
            for _, device in devices:
                try:
                    yubikey = {
                        'serial': str(device.serial),
                        'name': device.name,
                        'type': device.type,
                        'version': device.version
                    }
                    yubikeys.append(yubikey)
                except Exception as e:
                    self.logger.error(f"Error getting YubiKey info: {e}")
            return yubikeys
        except Exception as e:
            self.logger.exception("Error listing YubiKeys")
            return []

    def get_selected_yubikey(self) -> Optional[str]:
        """Get the serial number of the selected YubiKey."""
        try:
            data = json.loads(self.selected_yubikey_file.read_text())
            return data.get('serial')
        except Exception:
            return None

    def set_selected_yubikey(self, serial: str) -> bool:
        """Set the selected YubiKey by serial number."""
        try:
            self.selected_yubikey_file.write_text(json.dumps({'serial': serial}))
            return True
        except Exception:
            return False

    def select_yubikey(self, serial: str) -> bool:
        """Select a YubiKey to use."""
        try:
            # Verify the YubiKey exists
            yubikeys = self.get_yubikeys()
            if not any(yk['serial'] == serial for yk in yubikeys):
                self.logger.error(f"YubiKey with serial {serial} not found")
                return False

            # Save the selection
            self.selected_yubikey_file.write_text(json.dumps({'serial': serial}))
            self.logger.info(f"Selected YubiKey with serial {serial}")
            return True
            
        except Exception as e:
            self.logger.exception("Error selecting YubiKey")
            return False

    def deploy_key(self, server_data: Dict, password: str, pin: str) -> Dict:
        """Deploy SSH key to remote server"""
        self.logger.info(f"Starting key deployment for server: {server_data['name']}")
        
        try:
            # Get the public key using ykman
            self.logger.debug("Exporting public key from YubiKey")
            result = subprocess.run(
                ['ykman', 'piv', 'keys', 'export', '9a', '-'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.error("Failed to export public key")
                return {"success": False, "message": "Failed to export public key"}
            
            # Convert to SSH format
            self.logger.debug("Converting to SSH format")
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.pem') as temp_key:
                temp_key.write(result.stdout)
                temp_key.flush()
                
                ssh_key_result = subprocess.run(
                    ['ssh-keygen', '-i', '-m', 'PKCS8', '-f', temp_key.name],
                    capture_output=True,
                    text=True
                )
                
                if ssh_key_result.returncode != 0:
                    self.logger.error("Failed to convert key to SSH format")
                    return {"success": False, "message": "Failed to convert key to SSH format"}
                
                public_key = ssh_key_result.stdout.strip()
            
            # Connect to server and verify SSH setup
            self.logger.debug(f"Connecting to {server_data['hostname']}")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                ssh.connect(
                    server_data['hostname'],
                    port=int(server_data['port']),
                    username=server_data['username'],
                    password=password,
                    timeout=10
                )
                
                # Check if .ssh directory exists
                stdin, stdout, stderr = ssh.exec_command('test -d ~/.ssh && echo "EXISTS"')
                if stdout.channel.recv_exit_status() != 0:
                    self.logger.error("SSH directory not found on server")
                    return {"success": False, "message": "SSH is not properly configured on the server. The .ssh directory is missing."}
                
                # Check if authorized_keys exists and is writable
                stdin, stdout, stderr = ssh.exec_command('test -w ~/.ssh/authorized_keys || test -w ~/.ssh')
                if stdout.channel.recv_exit_status() != 0:
                    self.logger.error("Cannot write to authorized_keys")
                    return {"success": False, "message": "Cannot write to authorized_keys file. Please check SSH configuration on the server."}
                
                # Append the key
                cmd = f'echo "{public_key}" >> ~/.ssh/authorized_keys'
                stdin, stdout, stderr = ssh.exec_command(cmd)
                if stdout.channel.recv_exit_status() != 0:
                    error = stderr.read().decode().strip()
                    self.logger.error(f"Failed to append key: {error}")
                    return {"success": False, "message": f"Failed to add key: {error}"}
                
                self.logger.info("Key deployed successfully")
                return {"success": True, "message": "Key deployed successfully"}
                
            except Exception as e:
                self.logger.error(f"Connection failed: {str(e)}")
                return {"success": False, "message": f"Connection failed: {str(e)}"}
            finally:
                ssh.close()
                
        except Exception as e:
            self.logger.error(f"Deployment failed: {str(e)}")
            return {"success": False, "message": f"Deployment failed: {str(e)}"}

    def connect_to_server(self, server_id: str, pin: str = None) -> Dict:
        """Connect to a server using the YubiKey."""
        try:
            servers = json.loads(self.servers_file.read_text())
            server = next((s for s in servers if s['id'] == server_id), None)
            
            if not server:
                return {"success": False, "message": "Server not found"}
            
            # Get the current YubiKey
            device_list = list_all_devices()
            selected_serial = self.get_selected_yubikey()
            
            if not selected_serial:
                return {"success": False, "message": "No YubiKey selected"}
            
            self.logger.debug(f"Using YubiKey with serial: {selected_serial}")
            device_info = next((d for d in device_list if d[1].serial == int(selected_serial)), None)
            if not device_info:
                return {"success": False, "message": "Selected YubiKey not found"}

            # Open Terminal and start SSH connection
            # The system's SSH client will handle the YubiKey authentication
            ssh_command = [
                'ssh',
                '-o', 'PKCS11Provider=/opt/homebrew/lib/libykcs11.dylib',  # YubiKey PKCS11 provider
                f"{server['username']}@{server['hostname']}",
                '-p', str(server['port'])
            ]
            
            applescript_command = [
                'osascript',
                '-e', 'tell application "Terminal"',
                '-e', 'activate',
                '-e', f'do script "{" ".join(ssh_command)}"',
                '-e', 'end tell'
            ]
            
            subprocess.run(applescript_command)
            return {"success": True, "message": "SSH connection initiated in Terminal. The YubiKey will be used for authentication."}
            
        except Exception as e:
            self.logger.exception("Error connecting to server")
            return {"success": False, "message": f"Error connecting to server: {str(e)}"}

    def get_servers(self) -> List[Dict]:
        """Get list of configured servers."""
        try:
            if not self.servers_file.exists():
                return []
            
            servers = json.loads(self.servers_file.read_text())
            # Ensure each server has an ID
            for i, server in enumerate(servers):
                if 'id' not in server:
                    server['id'] = i + 1
            
            # Save back with IDs if needed
            self.servers_file.write_text(json.dumps(servers, indent=2))
            return servers
            
        except Exception as e:
            self.logger.exception("Error loading servers")
            return []

    def add_server(self, server_data: Dict) -> bool:
        """Add a new server configuration."""
        try:
            servers = self.get_servers()
            
            # Generate new ID
            max_id = max((s.get('id', 0) for s in servers), default=0)
            server_data['id'] = max_id + 1
            
            servers.append(server_data)
            self.servers_file.write_text(json.dumps(servers, indent=2))
            return True
            
        except Exception as e:
            self.logger.exception("Error adding server")
            return False

    def delete_server(self, server_id: str) -> bool:
        """Delete a server configuration."""
        try:
            servers = self.get_servers()
            servers = [s for s in servers if s['id'] != server_id]
            self.servers_file.write_text(json.dumps(servers, indent=2))
            return True
            
        except Exception as e:
            self.logger.exception("Error deleting server")
            return False

    def deploy_key_to_server(self, server_data: Dict) -> bool:
        """Deploy the YubiKey's public key to a server."""
        try:
            public_key = self.get_public_key()
            if not public_key:
                return False

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to the server
            ssh.connect(
                hostname=server_data['hostname'],
                username=server_data['username'],
                port=int(server_data['port'])
            )

            # Create .ssh directory if it doesn't exist
            commands = [
                'mkdir -p ~/.ssh',
                'chmod 700 ~/.ssh',
                f'echo "{public_key}" >> ~/.ssh/authorized_keys',
                'chmod 600 ~/.ssh/authorized_keys'
            ]

            for cmd in commands:
                ssh.exec_command(cmd)

            ssh.close()
            return True
            
        except Exception as e:
            self.logger.exception("Error deploying key to server")
            return False

    def get_public_key(self) -> Optional[str]:
        """Get the SSH public key from YubiKey."""
        try:
            # Get selected YubiKey
            selected_serial = self.get_selected_yubikey()
            if not selected_serial:
                self.logger.error("No YubiKey selected")
                return None

            # Try to get the public key directly
            result = subprocess.run(
                [
                    'ykman', 'piv', 'keys', 'export', '9a', '-',
                    '--format', 'PEM'
                ],
                capture_output=True,
                text=True
            )

            if result.returncode == 0 and result.stdout:
                # Write the key to a temporary file
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.pem') as temp_key:
                    temp_key.write(result.stdout)
                    temp_key.flush()
                    
                    # Convert to SSH public key format
                    ssh_key_result = subprocess.run(
                        ['ssh-keygen', '-y', '-f', temp_key.name],
                        capture_output=True,
                        text=True
                    )
                    
                    if ssh_key_result.returncode == 0 and ssh_key_result.stdout:
                        return ssh_key_result.stdout.strip()
            
            self.logger.error(f"Failed to get public key: {result.stderr}")
            return None
            
        except Exception as e:
            self.logger.exception("Error getting public key")
            return None

    def get_server(self, server_id: int) -> Optional[Dict]:
        """Get a server by ID."""
        try:
            if not self.servers_file.exists():
                self.logger.error("Servers file does not exist")
                return None

            servers = json.loads(self.servers_file.read_text())
            server_id = int(server_id)  # Ensure server_id is an integer
            
            # Debug logging
            self.logger.debug(f"Looking for server with ID: {server_id}")
            self.logger.debug(f"Available servers: {servers}")
            
            for server in servers:
                if int(server.get('id', -1)) == server_id:  # Convert stored ID to int for comparison
                    self.logger.debug(f"Found server: {server}")
                    return server
                    
            self.logger.error(f"No server found with ID {server_id}")
            return None
            
        except Exception as e:
            self.logger.exception(f"Error getting server with ID {server_id}")
            return None

    def update_server(self, server_id, server_data):
        """Update server details"""
        try:
            servers = self.get_servers()
            for server in servers:
                if server['id'] == server_id:
                    # Update server details while preserving the ID
                    server.update({
                        'name': server_data['name'],
                        'hostname': server_data['hostname'],
                        'username': server_data['username'],
                        'port': server_data['port']
                    })
                    self.servers_file.write_text(json.dumps(servers, indent=2))
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error updating server: {e}")
            return False
