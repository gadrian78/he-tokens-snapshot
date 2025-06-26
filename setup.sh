#!/bin/bash

# Complete Systemd Timer Setup for Hive Portfolio Snapshot (Multi-User Version with Custom Tokens)
# This script sets up the service to run at startup and then daily for multiple users

echo "🔧 Setting up Multi-User Hive Portfolio Snapshot systemd service and timer..."

# First, let's deactivate and remove any existing service and timer
echo "🛑 Deactivating and removing existing service and timer..."

# Stop and disable timer if it exists
if systemctl is-active --quiet hive-portfolio-multi-snapshot.timer 2>/dev/null; then
    sudo systemctl stop hive-portfolio-multi-snapshot.timer
    echo "✅ Stopped existing timer"
fi

if systemctl is-enabled --quiet hive-portfolio-multi-snapshot.timer 2>/dev/null; then
    sudo systemctl disable hive-portfolio-multi-snapshot.timer
    echo "✅ Disabled existing timer"
fi

# Stop service if it exists
if systemctl is-active --quiet hive-portfolio-multi-snapshot.service 2>/dev/null; then
    sudo systemctl stop hive-portfolio-multi-snapshot.service
    echo "✅ Stopped existing service"
fi

# Remove old service files if they exist
if [ -f "/etc/systemd/system/hive-portfolio-multi-snapshot.service" ]; then
    sudo rm /etc/systemd/system/hive-portfolio-multi-snapshot.service
    echo "✅ Removed old service file"
fi

if [ -f "/etc/systemd/system/hive-portfolio-multi-snapshot.timer" ]; then
    sudo rm /etc/systemd/system/hive-portfolio-multi-snapshot.timer
    echo "✅ Removed old timer file"
fi

# Remove old wrapper script if it exists
if [ -f "/usr/local/bin/hive-portfolio-multi-runner.sh" ]; then
    sudo rm /usr/local/bin/hive-portfolio-multi-runner.sh
    echo "✅ Removed old wrapper script"
fi

# Reload systemd to recognize the removed files
sudo systemctl daemon-reload
echo "✅ Reloaded systemd daemon (cleanup)"

echo "✅ Existing services completely removed"
echo

# Configuration - MODIFY THESE VALUES
SCRIPT_PATH="/home/shared/hive-scripts/he-tokens-snapshot.py"  # Shared script location
SNAPSHOTS_BASE_DIR="/home/shared/portfolio-snapshots"         # Base directory for all snapshots
PYTHON_PATH="/usr/bin/python3"

# User configuration with custom tokens - MODIFY THIS ASSOCIATIVE ARRAY
# Format: USER_TOKENS["USERNAME"]="token1 token2 token3 ..."
declare -A USER_TOKENS
USER_TOKENS["alice"]="LEO SPS DEC SWAP.HIVE"
USER_TOKENS["bob"]="LEO BEE PIZZA BEED"
USER_TOKENS["charlie"]="SPS DEC VOUCHER CHAOS"
USER_TOKENS["diana"]="LEO BEE SPS DEC SWAP.HIVE PIZZA"

# Extract usernames for easy iteration
USERNAMES=($(echo "${!USER_TOKENS[@]}" | tr ' ' '\n' | sort))

echo "📝 Configuration:"
echo "   Script path: $SCRIPT_PATH"
echo "   Base snapshots dir: $SNAPSHOTS_BASE_DIR"
echo "   Python path: $PYTHON_PATH"
echo "   Users and their tokens:"
for username in "${USERNAMES[@]}"; do
    echo "     $username: ${USER_TOKENS[$username]}"
done
echo

# Verify script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Error: Script not found at $SCRIPT_PATH"
    echo "   Please update SCRIPT_PATH in this setup script"
    exit 1
fi

# Create and setup virtual environment if it doesn't exist
VENV_PATH="$(dirname "$SCRIPT_PATH")/venv"

if [ ! -d "$VENV_PATH" ]; then
    echo "🐍 Creating virtual environment at: $VENV_PATH"
    if python3 -m venv "$VENV_PATH"; then
        echo "✅ Created virtual environment: $VENV_PATH"
    else
        echo "❌ Failed to create virtual environment"
        echo "   Please ensure python3-venv is installed: sudo apt install python3-venv"
        exit 1
    fi
fi

# Activate virtual environment and install requirements
echo "📦 Installing/updating Python dependencies..."
source "$VENV_PATH/bin/activate"

# Install prettytable and other common dependencies
pip3 install --upgrade pip
pip3 install hiveengine prettytable requests

# Check if there's a requirements.txt file
REQUIREMENTS_FILE="$(dirname "$SCRIPT_PATH")/requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "📋 Installing from requirements.txt..."
    pip install -r "$REQUIREMENTS_FILE"
fi

deactivate
echo "✅ Python dependencies installed"

# Update Python path to use virtual environment
PYTHON_PATH="$VENV_PATH/bin/python"

# Verify the Python path exists
if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ Error: Python not found at $PYTHON_PATH"
    echo "   Virtual environment creation may have failed"
    exit 1
fi

# Create base snapshots directory if it doesn't exist
mkdir -p "$SNAPSHOTS_BASE_DIR"
echo "✅ Created base snapshots directory: $SNAPSHOTS_BASE_DIR"

# Create individual user snapshot directories
for username in "${USERNAMES[@]}"; do
    mkdir -p "$SNAPSHOTS_BASE_DIR/$username"
    echo "✅ Created user snapshots directory: $SNAPSHOTS_BASE_DIR/$username"
done

# Create a robust wrapper script with per-user token support
echo "📄 Creating wrapper script with per-user token support..."
sudo tee /usr/local/bin/hive-portfolio-multi-runner.sh > /dev/null <<'EOF'
#!/bin/bash

# Hive Portfolio Multi-User Runner Script with Custom Tokens
SCRIPT_PATH="SCRIPT_PATH_PLACEHOLDER"
SNAPSHOTS_BASE_DIR="SNAPSHOTS_BASE_DIR_PLACEHOLDER"
PYTHON_PATH="PYTHON_PATH_PLACEHOLDER"

# User tokens configuration - MODIFY THIS SECTION TO ADD/REMOVE USERS
declare -A USER_TOKENS
USER_TOKENS_PLACEHOLDER

echo "$(date): Starting multi-user Hive portfolio snapshot"

for username in "${!USER_TOKENS[@]}"; do
    tokens="${USER_TOKENS[$username]}"
    echo "$(date): Processing user: $username with tokens: $tokens"
    
    # Create user directory if it doesn't exist
    mkdir -p "$SNAPSHOTS_BASE_DIR/$username"
    
    # Run the script for this user with their specific tokens
    if "$PYTHON_PATH" "$SCRIPT_PATH" -u "$username" -t $tokens --quiet --snapshots-dir "$SNAPSHOTS_BASE_DIR/$username"; then
        echo "$(date): ✅ Success for user: $username"
    else
        echo "$(date): ❌ Failed for user: $username"
    fi
    
    # Small delay between users to be nice to the API
    sleep 2
done

echo "$(date): Completed multi-user Hive portfolio snapshot"
EOF

# Replace placeholders in the wrapper script
sudo sed -i "s|SCRIPT_PATH_PLACEHOLDER|$SCRIPT_PATH|g" /usr/local/bin/hive-portfolio-multi-runner.sh
sudo sed -i "s|SNAPSHOTS_BASE_DIR_PLACEHOLDER|$SNAPSHOTS_BASE_DIR|g" /usr/local/bin/hive-portfolio-multi-runner.sh
sudo sed -i "s|PYTHON_PATH_PLACEHOLDER|$PYTHON_PATH|g" /usr/local/bin/hive-portfolio-multi-runner.sh

# Create the user tokens array in the wrapper script
USER_TOKENS_STR=""
for username in "${USERNAMES[@]}"; do
    USER_TOKENS_STR="${USER_TOKENS_STR}USER_TOKENS[\"$username\"]=\"${USER_TOKENS[$username]}\"\n"
done

sudo sed -i "s|USER_TOKENS_PLACEHOLDER|$USER_TOKENS_STR|g" /usr/local/bin/hive-portfolio-multi-runner.sh

sudo chmod +x /usr/local/bin/hive-portfolio-multi-runner.sh
echo "✅ Created wrapper script: /usr/local/bin/hive-portfolio-multi-runner.sh"

# Create the service file
echo "📄 Creating multi-user service file..."
sudo tee /etc/systemd/system/hive-portfolio-multi-snapshot.service > /dev/null <<EOF
[Unit]
Description=Hive Portfolio Multi-User Snapshot Service
Documentation=man:systemd.service(5)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=root
Group=root
WorkingDirectory=/tmp
ExecStart=/usr/local/bin/hive-portfolio-multi-runner.sh
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hive-portfolio-multi

# Failure handling
Restart=no
TimeoutStartSec=900
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Created service file: /etc/systemd/system/hive-portfolio-multi-snapshot.service"

# Create the timer file
echo "📄 Creating timer file..."
sudo tee /etc/systemd/system/hive-portfolio-multi-snapshot.timer > /dev/null <<EOF
[Unit]
Description=Hive Portfolio Multi-User Snapshot Timer
Documentation=man:systemd.timer(5)
Requires=hive-portfolio-multi-snapshot.service

[Timer]
# Run daily at 8:00 AM
OnCalendar=*-*-* 08:00:00

# Add randomized delay to avoid server load spikes (0-10 minutes for multiple users)
RandomizedDelaySec=600

# Run missed timers after system downtime
Persistent=true

# Prevent multiple instances
RefuseManualStart=false
RefuseManualStop=false

[Install]
WantedBy=timers.target
EOF

echo "✅ Created timer file: /etc/systemd/system/hive-portfolio-multi-snapshot.timer"

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable and start the timer (not the service directly)
echo "🚀 Enabling and starting timer..."
sudo systemctl enable hive-portfolio-multi-snapshot.timer
sudo systemctl start hive-portfolio-multi-snapshot.timer

echo
echo "✅ Setup complete!"
echo
echo "📊 Status:"
sudo systemctl status hive-portfolio-multi-snapshot.timer --no-pager -l

echo
echo "⏰ Timer details:"
sudo systemctl list-timers hive-portfolio-multi-snapshot.timer --no-pager

echo
echo "🔧 Useful commands:"
echo
echo "Check timer status:"
echo "  sudo systemctl status hive-portfolio-multi-snapshot.timer"
echo
echo "Check service logs:"
echo "  sudo journalctl -u hive-portfolio-multi-snapshot.service -f"
echo
echo "Check recent logs:"
echo "  sudo journalctl -u hive-portfolio-multi-snapshot.service --since today"
echo
echo "Manually trigger service:"
echo "  sudo systemctl start hive-portfolio-multi-snapshot.service"
echo
echo "Stop/disable timer:"
echo "  sudo systemctl stop hive-portfolio-multi-snapshot.timer"
echo "  sudo systemctl disable hive-portfolio-multi-snapshot.timer"
echo
echo "View all timers:"
echo "  sudo systemctl list-timers"
echo
echo "Edit user tokens:"
echo "  sudo nano /usr/local/bin/hive-portfolio-multi-runner.sh"
echo
echo "📝 The service will now run:"
echo "   • Daily at 8:00 AM (with 0-10 minute random delay)"
echo "   • For users and their tokens:"
for username in "${USERNAMES[@]}"; do
    echo "     - $username: ${USER_TOKENS[$username]}"
done
echo "   • Catch up on missed runs if system was offline"
echo

# Test if we can run the service manually
echo "🧪 Testing service (manual run)..."
echo "⚠️  This will process all users with their custom tokens - press Ctrl+C within 5 seconds to cancel"
sleep 5

if sudo systemctl start hive-portfolio-multi-snapshot.service; then
    echo "✅ Service test successful!"
    echo "📋 Last few log lines:"
    sudo journalctl -u hive-portfolio-multi-snapshot.service -n 10 --no-pager
else
    echo "❌ Service test failed. Check logs:"
    echo "   sudo journalctl -u hive-portfolio-multi-snapshot.service -n 20"
fi

echo
echo "🎉 Setup completed successfully!"
echo "📁 Snapshots will be saved to: $SNAPSHOTS_BASE_DIR/[username]/"
echo "👥 Users and their monitored tokens:"
for username in "${USERNAMES[@]}"; do
    echo "   $username: ${USER_TOKENS[$username]}"
done
echo
echo "To add/remove users or change tokens, edit the USER_TOKENS section in:"
echo "   /usr/local/bin/hive-portfolio-multi-runner.sh"
echo
echo "📖 How to modify user tokens:"
echo "   1. Edit: sudo nano /usr/local/bin/hive-portfolio-multi-runner.sh"
echo "   2. Find the 'declare -A USER_TOKENS' section"
echo "   3. Add/modify lines like: USER_TOKENS[\"username\"]=\"TOKEN1 TOKEN2 TOKEN3\""
echo "   4. Save and restart timer: sudo systemctl restart hive-portfolio-multi-snapshot.timer"
