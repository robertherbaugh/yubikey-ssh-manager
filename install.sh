#!/bin/bash

echo "Installing Yubikey SSH Manager..."

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install Python 3.13
echo "Installing Python 3.13..."
brew install python@3.13

# Ensure pip is up to date
python3.13 -m pip install --upgrade pip

# Install requirements
echo "Installing required Python packages..."
python3.13 -m pip install -r requirements.txt

# Install Yubikey tools
echo "Installing Yubikey tools..."
brew install yubico-piv-tool

echo "Installation complete! You can now run Yubikey SSH Manager.app"
