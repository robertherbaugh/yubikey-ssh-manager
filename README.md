# YubiKey SSH Manager

A macOS application that simplifies SSH server access using your YubiKey's self-signed certificate. The application runs in your menu bar and provides a web interface for managing SSH servers and deploying your YubiKey's public key.

## Screenshots

### Web Interface
![Web Interface](screenshots/web-interface.png)
*The web interface allows you to manage servers, check YubiKey status, and initiate SSH connections.*

### Menu Bar
![Menu Bar](screenshots/menu-bar.png)
*Quick access to your servers directly from the macOS menu bar.*

## Features

- macOS menu bar application for quick access
- Web interface for managing SSH servers
- Automatic YubiKey public key deployment to servers
- Secure SSH connections using YubiKey authentication
- Server configuration management

## Prerequisites

- macOS
- Python 3.9
- YubiKey with PIV capability
- SSH access to your servers

## Installation

### Option 1: Run from Source
1. Clone the repository:
```bash
git clone https://github.com/robertherbaugh/yubikey-ssh-manager.git
cd yubikey-ssh-manager
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Install YubiKey PIV Client:
```bash
brew install yubico-piv-tool
```

### Option 2: Run as macOS App
1. Download the latest release
2. Install Python 3.9+ if not already installed:
```bash
brew install python@3.9
```
3. Install the required packages:
```bash
pip3.9 install -r requirements.txt
```
4. Double-click the app to run it

## Usage

1. Start the application:
```bash
python app.py
```

2. The application will appear in your menu bar with a 🔐 icon.

3. Click the icon and select "Open Manager" to access the web interface.

4. In the web interface, you can:
   - Check YubiKey status
   - Add new servers
   - View and manage existing servers
   - Connect to servers using YubiKey authentication

## Adding a New Server

1. Click "Open Manager" from the menu bar icon
2. Fill in the server details:
   - Server Name (for identification)
   - Hostname (IP address or domain)
   - Username
   - Port (default: 22)
3. Click "Add Server"

The application will automatically deploy your YubiKey's public key to the server when you first connect.

## Security

- All server credentials are stored locally in `~/.yubikey-ssh-manager/servers.json`
- The application uses your YubiKey's self-signed certificate for SSH authentication
- No passwords are stored; authentication is handled through public key cryptography

## Troubleshooting

1. YubiKey not detected:
   - Ensure your YubiKey is properly inserted
   - Check if the YubiKey manager can detect your device

2. Connection issues:
   - Verify server credentials are correct
   - Ensure the server allows public key authentication
   - Check server SSH configuration

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
