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
SCRIPT_PATH="/home/[path-to-project]/he-tokens-snapshot.py"  # Script location
SNAPSHOTS_BASE_DIR="/home/[path-to-snapshots]"         # Base directory for all snapshots (a subdirectory of the project main directory?)
PYTHON_PATH="$(dirname "$SCRIPT_PATH")/venv/bin/python3"

# User configuration with custom tokens - MODIFY THIS ASSOCIATIVE ARRAY
# Format: USER_TOKENS["USERNAME"]="token1 token2 token3 ..."
declare -A USER_TOKENS
USER_TOKENS["alice"]="LEO SPS DEC SWAP.HIVE"
USER_TOKENS["bob"]="LEO BEE PIZZA BEED"
USER_TOKENS["charlie"]="SPS DEC VOUCHER CHAOS"
USER_TOKENS["diana"]="LEO BEE SPS DEC SWAP.HIVE PIZZA"

# Extract usernames for easy iteration
USERNAMES=($(echo "${!USER_TOKENS[@]}" | tr ' ' '\n' | sort))

# Get the current user (the one running this script)
CURRENT_USER=$(whoami)
CURRENT_GROUP=$(id -gn)

echo "📝 Configuration:"
echo "   Script path: $SCRIPT_PATH"
echo "   Base snapshots dir: $SNAPSHOTS_BASE_DIR"
echo "   Python path: $PYTHON_PATH"
echo "   Service will run as: $CURRENT_USER:$CURRENT_GROUP"
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

echo "🐍 Setting up virtual environment..."

# Remove incomplete venv if it exists but is broken
if [ -d "$VENV_PATH" ] && [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "⚠️  Found incomplete virtual environment, removing..."
    rm -rf "$VENV_PATH"
fi

if [ ! -d "$VENV_PATH" ]; then
    echo "🔨 Creating virtual environment at: $VENV_PATH"
    
    # Create venv with explicit error checking
    if python3 -m venv "$VENV_PATH"; then
        echo "✅ Virtual environment created"
    else
        echo "❌ Failed to create virtual environment"
        echo "   Please ensure python3-venv is installed: sudo apt install python3-venv"
        exit 1
    fi
    
    # Wait a moment for filesystem operations to complete
    sleep 2
    
    # Verify critical files exist
    if [ ! -f "$VENV_PATH/bin/activate" ]; then
        echo "❌ Virtual environment creation incomplete - missing activate script"
        echo "   Removing incomplete venv and retrying..."
        rm -rf "$VENV_PATH"
        
        # Retry once
        if python3 -m venv "$VENV_PATH"; then
            sleep 3  # Longer wait on retry
            if [ ! -f "$VENV_PATH/bin/activate" ]; then
                echo "❌ Virtual environment creation failed on retry"
                echo "   Check disk space and permissions"
                exit 1
            fi
        else
            echo "❌ Virtual environment creation failed on retry"
            exit 1
        fi
    fi
    
    if [ ! -f "$VENV_PATH/bin/python" ] && [ ! -f "$VENV_PATH/bin/python3" ]; then
        echo "❌ Virtual environment creation incomplete - missing python executable"
        rm -rf "$VENV_PATH"
        exit 1
    fi
    
    echo "✅ Virtual environment created successfully"
else
    echo "✅ Using existing virtual environment at: $VENV_PATH"
fi

# Validate the venv exists properly
if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "❌ Virtual environment activation script not found!"
    echo "   Removing broken venv directory..."
    rm -rf "$VENV_PATH"
    echo "   Please run this script again to recreate the virtual environment."
    exit 1
fi

# Activate virtual environment with error checking
echo "📦 Installing/updating Python dependencies..."
if source "$VENV_PATH/bin/activate"; then
    echo "✅ Virtual environment activated"
else
    echo "❌ Failed to activate virtual environment"
    echo "   Removing broken venv directory..."
    rm -rf "$VENV_PATH"
    exit 1
fi

# Install dependencies with error checking
echo "⬆️  Upgrading pip..."
if pip install --upgrade pip; then
    echo "✅ Pip upgraded successfully"
else
    echo "⚠️  Pip upgrade failed, continuing with existing version"
fi

echo "📋 Installing required packages..."
if pip install hiveengine prettytable requests; then
    echo "✅ Required packages installed"
else
    echo "❌ Failed to install required packages"
    deactivate
    exit 1
fi

# Check if there's a requirements.txt file
REQUIREMENTS_FILE="$(dirname "$SCRIPT_PATH")/requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "📋 Installing from requirements.txt..."
    if pip install -r "$REQUIREMENTS_FILE"; then
        echo "✅ Requirements.txt packages installed"
    else
        echo "❌ Failed to install from requirements.txt"
        deactivate
        exit 1
    fi
fi

# Verify installation by testing imports
echo "🧪 Testing package imports..."
if python -c "import hiveengine, prettytable, requests; print('All packages imported successfully')"; then
    echo "✅ Package verification successful"
else
    echo "❌ Package verification failed"
    deactivate
    exit 1
fi

deactivate
echo "✅ Python dependencies installed and verified"

# Update Python path to use virtual environment
PYTHON_PATH="$VENV_PATH/bin/python"

# Final verification of Python path
if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ Error: Python not found at $PYTHON_PATH"
    echo "   Virtual environment may be incomplete"
    echo "   Available python executables in venv:"
    ls -la "$VENV_PATH/bin/python"* 2>/dev/null || echo "   None found"
    exit 1
fi

echo "✅ Virtual environment setup completed successfully"
echo "   Python path: $PYTHON_PATH"

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

# Verify Python and packages are available
if [ ! -f "$PYTHON_PATH" ]; then
    echo "$(date): ERROR: Python executable not found at $PYTHON_PATH"
    exit 1
fi

if ! "$PYTHON_PATH" -c "import hiveengine, prettytable, requests" 2>/dev/null; then
    echo "$(date): ERROR: Required Python packages not available in virtual environment"
    exit 1
fi

for username in "${!USER_TOKENS[@]}"; do
    tokens="${USER_TOKENS[$username]}"
    echo "$(date): Processing user: $username with tokens: $tokens"
    
    # Create user directory if it doesn't exist
    mkdir -p "$SNAPSHOTS_BASE_DIR/$username"
    
    # FIXED: Pass the base snapshots directory, not the user-specific one
    # The script will create the user subdirectory structure itself
    if "$PYTHON_PATH" "$SCRIPT_PATH" -u "$username" -t $tokens --quiet --snapshots-dir "$SNAPSHOTS_BASE_DIR"; then
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

# Update the service file creation to use current user
echo "📄 Creating multi-user service file..."
sudo tee /etc/systemd/system/hive-portfolio-multi-snapshot.service > /dev/null <<EOF
[Unit]
Description=Hive Portfolio Multi-User Snapshot Service
Documentation=man:systemd.service(5)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$CURRENT_USER
Group=$CURRENT_GROUP
WorkingDirectory=$(dirname "$SCRIPT_PATH")
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
echo "   • As user: $CURRENT_USER:$CURRENT_GROUP"
echo "   • Daily at 8:00 AM (with 0-10 minute random delay)"
echo "   • For users and their tokens:"
for username in "${USERNAMES[@]}"; do
    echo "     - $username: ${USER_TOKENS[$username]}"
done
echo "   • Snapshots saved to: $SNAPSHOTS_BASE_DIR/[username]/daily/"
echo "   • Catch up on missed runs if system was offline"

# Test if we can run the service manually
echo "🧪 Testing service (manual run)..."
echo "⚠️  This will process all users with their custom tokens - press Ctrl+C within 3 seconds to cancel"
sleep 3
echo "   Started processing..."

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
