# ==============================================================================
# This script does the following:
#   * removes existing service and timer, if they were set
#   * sets a service and timer to run according to settings in config file
#   * tests them by manually calling the service at the end
# It is loaded from setup.sh if set up from config, but can be run separately too.
# ==============================================================================

# If config not loaded (ran independently), than load them
# Validate required configuration
if [ -z "$SCRIPT_PATH" ] || [ -z "$SNAPSHOTS_BASE_DIR" ] || [ -z "$SERVICE_NAME" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    CONFIG_FILE="$SCRIPT_DIR/my-config.sh"

    # Check if config file exists
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "❌ Error: Configuration file not found at $CONFIG_FILE"
        echo "   Please create a config.sh file with your settings."
        echo "   A sample config.sh should be provided with this script."
        exit 1
    fi

    # Load configuration
    echo "📋 Loading configuration from $CONFIG_FILE..."
    source "$CONFIG_FILE"

    # Validate required configuration
    if [ -z "$SCRIPT_PATH" ] || [ -z "$SNAPSHOTS_BASE_DIR" ] || [ -z "$SERVICE_NAME" ]; then
        echo "❌ Error: Missing required configuration values"
        echo "   Please check SCRIPT_PATH, SNAPSHOTS_BASE_DIR, and SERVICE_NAME in config.sh"
        exit 1
    fi

    # Check if USER_TOKENS array has any entries
    if [ ${#USER_TOKENS[@]} -eq 0 ]; then
        echo "❌ Error: No users configured in USER_TOKENS"
        echo "   Please add at least one user in config.sh"
        exit 1
    fi

    # Extract usernames for easy iteration
    USERNAMES=($(echo "${!USER_TOKENS[@]}" | tr ' ' '\n' | sort))

    # Set Python path (auto-detect if configured as "auto")
    if [ "$PYTHON_PATH" = "auto" ]; then
        PYTHON_PATH="$(dirname "$SCRIPT_PATH")/venv/bin/python3"
    fi

    # Get the current user (the one running this script)
    CURRENT_USER=$(whoami)
    CURRENT_GROUP=$(id -gn)
fi

# First, let's deactivate and remove any existing service and timer
echo "🛑 Deactivating and removing existing service and timer..."

# Stop and disable timer if it exists
if systemctl is-active --quiet "$SERVICE_NAME.timer" 2>/dev/null; then
    sudo systemctl stop "$SERVICE_NAME.timer"
    echo "✅ Stopped existing timer"
fi

if systemctl is-enabled --quiet "$SERVICE_NAME.timer" 2>/dev/null; then
    sudo systemctl disable "$SERVICE_NAME.timer"
    echo "✅ Disabled existing timer"
fi

# Stop service if it exists
if systemctl is-active --quiet "$SERVICE_NAME.service" 2>/dev/null; then
    sudo systemctl stop "$SERVICE_NAME.service"
    echo "✅ Stopped existing service"
fi

# Remove old service files if they exist
if [ -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
    sudo rm "/etc/systemd/system/$SERVICE_NAME.service"
    echo "✅ Removed old service file"
fi

if [ -f "/etc/systemd/system/$SERVICE_NAME.timer" ]; then
    sudo rm "/etc/systemd/system/$SERVICE_NAME.timer"
    echo "✅ Removed old timer file"
fi

# Remove old wrapper script if it exists
WRAPPER_SCRIPT="/usr/local/bin/${SERVICE_NAME}-runner.sh"
if [ -f "$WRAPPER_SCRIPT" ]; then
    sudo rm "$WRAPPER_SCRIPT"
    echo "✅ Removed old wrapper script"
fi

# Reload systemd to recognize the removed files
sudo systemctl daemon-reload
echo "✅ Reloaded systemd daemon (cleanup)"

echo "✅ Existing services completely removed"
echo

# Create a robust wrapper script with per-user token support
echo "📄 Creating wrapper script with per-user token support..."

# Create wrapper script that sources the config file
cat > "/tmp/${SERVICE_NAME}-runner.sh" <<EOF
#!/bin/bash

# Hive Portfolio Multi-User Runner Script
CONFIG_FILE="$CONFIG_FILE"

# Load configuration
source "\$CONFIG_FILE"

# Set paths
SCRIPT_PATH="$SCRIPT_PATH"
SNAPSHOTS_BASE_DIR="$SNAPSHOTS_BASE_DIR"
PYTHON_PATH="$PYTHON_PATH"

echo "\$(date): Starting multi-user Hive portfolio snapshot"

# Verify Python and packages are available
if [ ! -f "\$PYTHON_PATH" ]; then
    echo "\$(date): ERROR: Python executable not found at \$PYTHON_PATH"
    exit 1
fi

if ! "\$PYTHON_PATH" -c "import hiveengine, prettytable, requests" 2>/dev/null; then
    echo "\$(date): ERROR: Required Python packages not available in virtual environment"
    exit 1
fi

for username in "\${!USER_TOKENS[@]}"; do
    tokens="\${USER_TOKENS[\$username]}"
    echo "\$(date): Processing user: \$username with tokens: \$tokens"
    
    # Create user directory if it doesn't exist
    mkdir -p "\$SNAPSHOTS_BASE_DIR/\$username"
    
    # Build command arguments
    cmd_args="-u \"\$username\" -t \$tokens --snapshots-dir \"\$SNAPSHOTS_BASE_DIR\""
    
    # Add quiet mode if enabled
    if [ "\$ENABLE_QUIET_MODE" = "true" ]; then
        cmd_args="\$cmd_args --quiet"
    fi
    
    # Execute the command
    if eval "\"\$PYTHON_PATH\" \"\$SCRIPT_PATH\" \$cmd_args"; then
        echo "\$(date): ✅ Success for user: \$username"
    else
        echo "\$(date): ❌ Failed for user: \$username"
    fi
    
    # Delay between users
    if [ \$DELAY_BETWEEN_USERS_SEC -gt 0 ]; then
        sleep \$DELAY_BETWEEN_USERS_SEC
    fi
done

echo "\$(date): Completed multi-user Hive portfolio snapshot"
EOF

# Move the wrapper script to the system location
sudo mv "/tmp/${SERVICE_NAME}-runner.sh" "$WRAPPER_SCRIPT"
sudo chmod +x "$WRAPPER_SCRIPT"
echo "✅ Created wrapper script: $WRAPPER_SCRIPT"

# Create the service file
echo "📄 Creating service file..."
sudo tee "/etc/systemd/system/$SERVICE_NAME.service" > /dev/null <<EOF
[Unit]
Description=$SERVICE_DESCRIPTION
Documentation=man:systemd.service(5)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$CURRENT_USER
Group=$CURRENT_GROUP
WorkingDirectory=$(dirname "$SCRIPT_PATH")
ExecStart=$WRAPPER_SCRIPT
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Failure handling
Restart=no
TimeoutStartSec=$TIMEOUT_START_SEC
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Created service file: /etc/systemd/system/$SERVICE_NAME.service"

# Create the timer file
echo "📄 Creating timer file..."
sudo tee "/etc/systemd/system/$SERVICE_NAME.timer" > /dev/null <<EOF
[Unit]
Description=$SERVICE_DESCRIPTION Timer
Documentation=man:systemd.timer(5)
Requires=$SERVICE_NAME.service

[Timer]
# Run daily at configured time
OnCalendar=*-*-* $RUN_TIME

# Add randomized delay to avoid server load spikes
RandomizedDelaySec=$RANDOMIZED_DELAY_SEC

# Run missed timers after system downtime
Persistent=$PERSISTENT

# Prevent multiple instances
RefuseManualStart=false
RefuseManualStop=false

[Install]
WantedBy=timers.target
EOF

echo "✅ Created timer file: /etc/systemd/system/$SERVICE_NAME.timer"

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable and start the timer (not the service directly)
echo "🚀 Enabling and starting timer..."
sudo systemctl enable "$SERVICE_NAME.timer"
sudo systemctl start "$SERVICE_NAME.timer"

echo
echo "✅ Setup complete!"
echo
echo "📊 Status:"
sudo systemctl status "$SERVICE_NAME.timer" --no-pager -l

echo
echo "⏰ Timer details:"
sudo systemctl list-timers "$SERVICE_NAME.timer" --no-pager

echo
echo "🔧 Useful commands:"
echo
echo "Check timer status:"
echo "  sudo systemctl status $SERVICE_NAME.timer"
echo
echo "Check service logs:"
echo "  sudo journalctl -u $SERVICE_NAME.service -f"
echo
echo "Check recent logs:"
echo "  sudo journalctl -u $SERVICE_NAME.service --since today"
echo
echo "Manually trigger service:"
echo "  sudo systemctl start $SERVICE_NAME.service"
echo
echo "Stop/disable timer:"
echo "  sudo systemctl stop $SERVICE_NAME.timer"
echo "  sudo systemctl disable $SERVICE_NAME.timer"
echo
echo "View all timers:"
echo "  sudo systemctl list-timers"
echo
echo "Edit configuration:"
echo "  nano $CONFIG_FILE"
echo "  (Then re-run this script to apply changes)"
echo
echo "📝 The service will now run:"
echo "   • As user: $CURRENT_USER:$CURRENT_GROUP"
echo "   • Daily at $RUN_TIME (with 0-$(($RANDOMIZED_DELAY_SEC/60)) minute random delay)"
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

if sudo systemctl start "$SERVICE_NAME.service"; then
    echo "✅ Service test successful!"
    echo "📋 Last few log lines:"
    sudo journalctl -u "$SERVICE_NAME.service" -n 10 --no-pager
else
    echo "❌ Service test failed. Check logs:"
    echo "   sudo journalctl -u $SERVICE_NAME.service -n 20"
fi

echo
echo "🎉 Setup completed successfully!"
echo "📁 Snapshots will be saved to: $SNAPSHOTS_BASE_DIR/[username]/"
echo "👥 Users and their monitored tokens:"
for username in "${USERNAMES[@]}"; do
    echo "   $username: ${USER_TOKENS[$username]}"
done
echo
echo "📖 How to modify configuration:"
echo "   1. Edit: $CONFIG_FILE"
echo "   2. Re-run this script to apply changes"
echo "   3. The service will automatically use the new configuration"
