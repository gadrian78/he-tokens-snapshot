# This script deactivates automated snapshots and deactivates and removes the service and timer responsible for running the tool daily

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
