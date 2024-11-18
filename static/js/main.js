// Base URL for API calls
const API_BASE_URL = 'http://127.0.0.1:5000';

// YubiKey status polling
let yubiKeyStatusInterval;

function startYubiKeyStatusPolling() {
    // Poll immediately
    updateYubiKeyStatus();
    
    // Then poll every 2 seconds
    yubiKeyStatusInterval = setInterval(updateYubiKeyStatus, 2000);
}

async function updateYubiKeyStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/yubikey-status`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const status = await response.json();
        const statusElement = document.getElementById('yubikey-status');
        if (status.connected) {
            statusElement.textContent = 'YubiKey Connected';
            statusElement.className = 'text-green-500';
        } else {
            statusElement.textContent = status.message || 'No YubiKey Detected';
            statusElement.className = 'text-red-500';
        }
    } catch (error) {
        console.error('Error updating YubiKey status:', error);
        const statusElement = document.getElementById('yubikey-status');
        statusElement.textContent = 'Error checking YubiKey status';
        statusElement.className = 'text-red-500';
    }
}

// Start polling when the page loads
document.addEventListener('DOMContentLoaded', () => {
    startYubiKeyStatusPolling();
    loadServers();
});

// Clean up when the page is unloaded
window.addEventListener('beforeunload', () => {
    if (yubiKeyStatusInterval) {
        clearInterval(yubiKeyStatusInterval);
    }
});

async function loadServers() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/servers`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const servers = await response.json();
        const serverList = document.getElementById('serverList');
        serverList.innerHTML = '';
        
        servers.forEach(server => {
            const div = document.createElement('div');
            div.className = 'bg-white p-4 rounded-lg shadow mb-4';
            div.innerHTML = `
                <div class="flex justify-between items-center">
                    <div>
                        <h3 class="text-lg font-semibold">${server.name}</h3>
                        <p class="text-gray-600">${server.username}@${server.hostname}:${server.port}</p>
                    </div>
                    <div class="space-x-2">
                        <button onclick="deployKey('${server.id}')" 
                                class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                            Deploy Key
                        </button>
                        <button id="connect-${server.id}"
                                class="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
                            Connect SSH
                        </button>
                        <button onclick="editServer('${server.id}')" 
                                class="bg-orange-500 text-white px-4 py-2 rounded hover:bg-orange-600">
                            Edit
                        </button>
                        <button onclick="deleteServer('${server.id}')"
                                class="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600">
                            Delete
                        </button>
                    </div>
                </div>
            `;
            serverList.appendChild(div);
            
            // Add click handler for connect button
            const connectButton = document.getElementById(`connect-${server.id}`);
            connectButton.addEventListener('click', () => {
                console.log('Connect button clicked for server:', server.id);
                connectToServer(server.id);
            });
        });
    } catch (error) {
        console.error('Error loading servers:', error);
        showNotification('error', 'Failed to load servers');
    }
}

function showNotification(type, message) {
    console.log(`${type}: ${message}`);
    // TODO: Implement visual notification
}

// Server connection functions
function connectToServer(serverId) {
    console.log('connectToServer called with ID:', serverId);
    
    // Send connection request
    fetch(`${API_BASE_URL}/api/connect/${serverId}`, {
        method: 'POST',
        headers: {
            'Accept': 'application/json'
        }
    })
    .then(response => {
        console.log('Response status:', response.status);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Response data:', data);
        if (data.success) {
            showNotification('success', 'Connected successfully');
        } else {
            showNotification('error', data.message || 'Failed to connect');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('error', 'Failed to connect to server');
    });
}

async function deployKey(serverId) {
    const pin = prompt('Enter YubiKey PIN:');
    const password = prompt('Enter server password:');
    
    if (!pin || !password) {
        showNotification('error', 'PIN and password are required');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/deploy-key/${serverId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ pin, password })
        });
        
        const result = await response.json();
        if (!result.success) {
            showNotification('error', result.message || 'Failed to deploy key');
        }
    } catch (error) {
        console.error('Error deploying key:', error);
        showNotification('error', 'Error deploying key');
    }
}

async function deleteServer(serverId) {
    if (!confirm('Are you sure you want to delete this server?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/servers/${serverId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        if (result.success) {
            showNotification('success', 'Server deleted successfully');
            loadServers();
        } else {
            showNotification('error', result.message || 'Failed to delete server');
        }
    } catch (error) {
        console.error('Error deleting server:', error);
        showNotification('error', 'Error deleting server');
    }
}

async function editServer(serverId) {
    try {
        // Get server details
        const response = await fetch(`${API_BASE_URL}/api/servers`);
        const servers = await response.json();
        const server = servers.find(s => s.id === serverId);
        
        if (!server) {
            showNotification('error', 'Server not found');
            return;
        }

        // Populate form with server details
        document.getElementById('editServerId').value = server.id;
        document.querySelector('#editServerForm input[name="name"]').value = server.name;
        document.querySelector('#editServerForm input[name="hostname"]').value = server.hostname;
        document.querySelector('#editServerForm input[name="username"]').value = server.username;
        document.querySelector('#editServerForm input[name="port"]').value = server.port;

        // Show modal
        document.getElementById('editServerModal').classList.add('show');
    } catch (error) {
        console.error('Error loading server details:', error);
        showNotification('error', 'Error loading server details');
    }
}

// Add server form handler
document.getElementById('addServerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const serverData = {
        name: formData.get('name'),
        hostname: formData.get('hostname'),
        username: formData.get('username'),
        port: formData.get('port')
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/servers`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(serverData)
        });
        
        if (!response.ok) {
            throw new Error('Failed to add server');
        }
        
        showNotification('success', 'Server added successfully');
        e.target.reset();
        loadServers();
    } catch (error) {
        console.error('Error adding server:', error);
        showNotification('error', 'Failed to add server');
    }
});

// Edit server form handler
document.getElementById('editServerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const serverId = document.getElementById('editServerId').value;
    const serverData = {
        name: document.querySelector('#editServerForm input[name="name"]').value,
        hostname: document.querySelector('#editServerForm input[name="hostname"]').value,
        username: document.querySelector('#editServerForm input[name="username"]').value,
        port: document.querySelector('#editServerForm input[name="port"]').value
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/servers/${serverId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(serverData)
        });
        
        const result = await response.json();
        if (result.success) {
            showNotification('success', 'Server updated successfully');
            closeModal('editServerModal');
            loadServers();  // Refresh the server list
        } else {
            showNotification('error', result.message || 'Failed to update server');
        }
    } catch (error) {
        console.error('Error updating server:', error);
        showNotification('error', 'Error updating server');
    }
});

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}
