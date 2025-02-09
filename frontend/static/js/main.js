// DOM Elements
const addServerBtn = document.getElementById('add-server-btn');
const serverModal = document.getElementById('server-modal');
const deployKeyModal = document.getElementById('deploy-key-modal');
const serverForm = document.getElementById('server-form');
const deployKeyForm = document.getElementById('deploy-key-form');
const notification = document.getElementById('notification');
const serverGrid = document.getElementById('servers-list');
const loadingElement = document.getElementById('loading');
const emptyState = document.getElementById('empty-state');
const yubikeyStatus = document.getElementById('yubikey-status');
const yubikeyStatusDot = document.getElementById('yubikey-status-dot');
const yubikeySelect = document.getElementById('yubikey-select');

// State
let servers = [];
let editingServerId = null;

// Event Listeners
document.addEventListener('DOMContentLoaded', initialize);
addServerBtn.addEventListener('click', () => openModal('server-modal'));
serverForm.addEventListener('submit', handleServerSubmit);
deployKeyForm.addEventListener('submit', handleDeployKey);
yubikeySelect.addEventListener('change', (e) => {
    if (e.target.value) {
        selectYubiKey(e.target.value);
    }
});

// Functions
async function initialize() {
    checkYubiKeyStatus();
    await loadServers();
    setInterval(checkYubiKeyStatus, 5000);
}

async function checkYubiKeyStatus() {
    try {
        const [statusResponse, yubikeyResponse] = await Promise.all([
            fetch('/api/yubikey-status'),
            fetch('/api/yubikeys')
        ]);

        const statusData = await statusResponse.json();
        const yubikeysData = await yubikeyResponse.json();
        
        const statusElement = document.querySelector('#yubikey-status .status-text');
        const selectElement = document.querySelector('#yubikey-select');
        
        // Update status text and indicator
        statusElement.textContent = statusData.message;
        if (statusData.connected) {
            statusElement.classList.remove('error');
            statusElement.classList.add('success');
        } else {
            statusElement.classList.remove('success');
            statusElement.classList.add('error');
        }

        // Update YubiKey selection dropdown
        if (yubikeysData.yubikeys && yubikeysData.yubikeys.length > 0) {
            selectElement.innerHTML = '<option value="">Select YubiKey</option>' +
                yubikeysData.yubikeys.map(yk => 
                    `<option value="${yk.serial}" ${yk.serial === yubikeysData.selected ? 'selected' : ''}>
                        YubiKey ${yk.serial} (v${yk.version})
                    </option>`
                ).join('');
            selectElement.classList.remove('hidden');
        } else {
            selectElement.classList.add('hidden');
        }
    } catch (error) {
        console.error('Error checking YubiKey status:', error);
        document.querySelector('#yubikey-status .status-text').textContent = 'Error checking YubiKey status';
    }
}

async function loadServers() {
    try {
        loadingElement.style.display = 'flex';
        serverGrid.style.display = 'none';
        emptyState.style.display = 'none';

        const response = await fetch('/api/servers');
        servers = await response.json();

        if (servers.length === 0) {
            emptyState.style.display = 'block';
        } else {
            renderServers();
            serverGrid.style.display = 'grid';
        }
    } catch (error) {
        showNotification('Error loading servers', 'error');
    } finally {
        loadingElement.style.display = 'none';
    }
}

function renderServers() {
    const serversList = document.getElementById('servers-list');
    const emptyState = document.getElementById('empty-state');
    const loading = document.getElementById('loading');

    // Hide loading state
    loading.classList.add('hidden');

    // Show empty state if no servers
    if (!servers || servers.length === 0) {
        emptyState.classList.remove('hidden');
        serversList.classList.add('hidden');
        return;
    }

    // Show servers grid
    emptyState.classList.add('hidden');
    serversList.classList.remove('hidden');

    // Render servers
    serversList.innerHTML = servers.map(server => `
        <div class="server-card">
            <div class="server-card-header">
                <h3 class="server-card-title">${server.name}</h3>
                <div class="server-card-actions">
                    <button onclick="editServer('${server.id}')" class="btn btn-secondary">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button onclick="deleteServer('${server.id}')" class="btn btn-danger">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="server-info">
                <p><strong>Host:</strong> ${server.hostname}</p>
                <p><strong>Username:</strong> ${server.username}</p>
                <p><strong>Port:</strong> ${server.port}</p>
            </div>
            <div class="server-card-actions" style="margin-top: auto;">
                <button onclick="deployKey('${server.id}')" class="btn btn-success">
                    <i class="fas fa-key"></i> Deploy Key
                </button>
                <button onclick="connectToServer('${server.id}')" class="btn btn-primary">
                    <i class="fas fa-terminal"></i> Connect
                </button>
            </div>
        </div>
    `).join('');
}

function openModal(modalId) {
    document.getElementById(modalId).classList.add('show');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
    if (modalId === 'server-modal') {
        serverForm.reset();
        editingServerId = null;
        document.getElementById('modal-title').textContent = 'Add New Server';
    }
}

async function handleServerSubmit(event) {
    event.preventDefault();
    
    const serverData = {
        name: document.getElementById('name').value,
        hostname: document.getElementById('hostname').value,
        username: document.getElementById('username').value,
        port: parseInt(document.getElementById('port').value)
    };

    try {
        const url = editingServerId ? `/api/servers/${editingServerId}` : '/api/servers';
        const method = editingServerId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(serverData)
        });

        if (!response.ok) throw new Error('Failed to save server');

        showNotification(
            `Server ${editingServerId ? 'updated' : 'added'} successfully`, 
            'success'
        );
        closeModal('server-modal');
        await loadServers();
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

function editServer(serverId) {
    const server = servers.find(s => s.id === serverId);
    if (!server) return;

    editingServerId = serverId;
    document.getElementById('modal-title').textContent = 'Edit Server';
    document.getElementById('name').value = server.name;
    document.getElementById('hostname').value = server.hostname;
    document.getElementById('username').value = server.username;
    document.getElementById('port').value = server.port;
    
    openModal('server-modal');
}

async function deleteServer(serverId) {
    if (!confirm('Are you sure you want to delete this server?')) return;

    try {
        const response = await fetch(`/api/servers/${serverId}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Failed to delete server');

        showNotification('Server deleted successfully', 'success');
        await loadServers();
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

function deployKey(serverId) {
    document.getElementById('deploy-server-id').value = serverId;
    openModal('deploy-key-modal');
}

async function handleDeployKey(event) {
    event.preventDefault();

    const serverId = document.getElementById('deploy-server-id').value;
    const yubiKeyPin = document.getElementById('yubikey-pin').value;
    const serverPassword = document.getElementById('server-password').value;

    try {
        const response = await fetch(`/api/deploy-key/${serverId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin: yubiKeyPin, password: serverPassword })
        });

        if (!response.ok) throw new Error('Failed to deploy key');

        showNotification('SSH key deployed successfully', 'success');
        closeModal('deploy-key-modal');
        deployKeyForm.reset();
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function connectToServer(serverId) {
    try {
        const response = await fetch(`/api/servers/${serverId}/connect`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();
        if (!result.success) {
            throw new Error(result.message || 'Failed to connect to server');
        }

        showNotification(result.message || 'SSH connection initiated in Terminal', 'success');
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function selectYubiKey(serial) {
    try {
        const response = await fetch(`/api/yubikeys/select/${serial}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();
        if (!result.success) {
            throw new Error(result.message || 'Failed to select YubiKey');
        }

        showNotification('YubiKey selected successfully', 'success');
        checkYubiKeyStatus(); // Refresh the status
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

function showNotification(message, type = 'success') {
    const notificationElement = document.getElementById('notification');
    const messageElement = document.getElementById('notification-message');
    
    messageElement.textContent = message;
    notificationElement.className = `notification ${type} show`;
    
    setTimeout(() => {
        notificationElement.classList.remove('show');
    }, 3000);
}
