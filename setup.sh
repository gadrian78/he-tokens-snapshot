#!/bin/bash

# Complete Systemd Timer Setup for Hive Portfolio Snapshot (Multi-User Version)
# This script sets up the service to run at startup and then daily for multiple users

echo "🔧 Setting up Multi-User Hive Portfolio Snapshot systemd service and timer..."

# Configuration - MODIFY THESE VALUES
SCRIPT_PATH="/home/shared/hive-scripts/he-tokens-snapshot.py"  # Shared script location
SNAPSHOTS_BASE_DIR="/home/shared/portfolio-snapshots"         # Base directory for all snapshots
PYTHON_PATH="/usr/bin/python3"

# List of usernames to monitor - MODIFY THIS ARRAY
USERNAMES=("alice" "bob" "charlie" "diana")

echo "📝 Configuration:"
echo "   Script path: $SCRIPT_PATH"
echo "   Base snapshots dir: $SNAPSHOTS_BASE_DIR"
echo "   Python path: $PYTHON_PATH"
echo "   Users to monitor: ${USERNAMES[*]}"
echo

# Verify script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Error: Script not found at $SCRIPT_PATH"
    echo "   Please update SCRIPT_PATH in this setup script"
    exit 1
fi

# Create and setup virtual environment if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
    echo "✅ Created virtual environment: $VENV_PATH"
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

# Create the service file for multi-user snapshots
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
WorkingDirectory=$(dirname "$SCRIPT_PATH")
Environment=PATH=/usr/bin:/usr/local/bin
ExecStart=/bin/bash -c 'for user in ${USERNAMES[*]}; do echo "Processing user: \$user"; "$PYTHON_PATH" "$SCRIPT_PATH" -u "\$user" --quiet --snapshots-dir "$SNAPSHOTS_BASE_DIR/\$user" || echo "Failed for user: \$user"; done'
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hive-portfolio-multi

# Failure handling
Restart=no
TimeoutStartSec=600
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOF

# We need to substitute the actual values in the service file
sudo sed -i "s|\${USERNAMES\[\*\]}|${USERNAMES[*]}|g" /etc/systemd/system/hive-portfolio-multi-snapshot.service
sudo sed -i "s|\$PYTHON_PATH|$PYTHON_PATH|g" /etc/systemd/system/hive-portfolio-multi-snapshot.service
sudo sed -i "s|\$SCRIPT_PATH|$SCRIPT_PATH|g" /etc/systemd/system/hive-portfolio-multi-snapshot.service
sudo sed -i "s|\$SNAPSHOTS_BASE_DIR|$SNAPSHOTS_BASE_DIR|g" /etc/systemd/system/hive-portfolio-multi-snapshot.service

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

# Create a more robust service file using a wrapper script
echo "📄 Creating wrapper script for better control..."
sudo tee /usr/local/bin/hive-portfolio-multi-runner.sh > /dev/null <<EOF
#!/bin/bash

# Hive Portfolio Multi-User Runner Script
SCRIPT_PATH="$SCRIPT_PATH"
SNAPSHOTS_BASE_DIR="$SNAPSHOTS_BASE_DIR"
PYTHON_PATH="$PYTHON_PATH"
USERNAMES=(${USERNAMES[*]})

echo "\$(date): Starting multi-user Hive portfolio snapshot"

for username in "\${USERNAMES[@]}"; do
    echo "\$(date): Processing user: \$username"
    
    # Create user directory if it doesn't exist
    mkdir -p "\$SNAPSHOTS_BASE_DIR/\$username"
    
    # Run the script for this user
    if "\$PYTHON_PATH" "\$SCRIPT_PATH" -u "\$username" --quiet --snapshots-dir "\$SNAPSHOTS_BASE_DIR/\$username"; then
        echo "\$(date): ✅ Success for user: \$username"
    else
        echo "\$(date): ❌ Failed for user: \$username"
    fi
    
    # Small delay between users to be nice to the API
    sleep 2
done

echo "\$(date): Completed multi-user Hive portfolio snapshot"
EOF

sudo chmod +x /usr/local/bin/hive-portfolio-multi-runner.sh
echo "✅ Created wrapper script: /usr/local/bin/hive-portfolio-multi-runner.sh"

# Update service to use wrapper script
echo "📄 Updating service to use wrapper script..."
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

echo "✅ Updated service file to use wrapper script"

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
echo "Edit usernames:"
echo "  sudo nano /usr/local/bin/hive-portfolio-multi-runner.sh"
echo
echo "📝 The service will now run:"
echo "   • Daily at 8:00 AM (with 0-10 minute random delay)"
echo "   • For users: ${USERNAMES[*]}"
echo "   • Catch up on missed runs if system was offline"
echo

# Test if we can run the service manually
echo "🧪 Testing service (manual run)..."
echo "⚠️  This will process all users - press Ctrl+C within 5 seconds to cancel"
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
echo "👥 Monitoring users: ${USERNAMES[*]}"
echo
echo "To add/remove users, edit: /usr/local/bin/hive-portfolio-multi-runner.sh"
