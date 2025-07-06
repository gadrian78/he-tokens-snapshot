# This script deactivates automated snapshots and deactivates and removes the service and timer responsible for running the tool daily

# If config not loaded (ran independently), than load them
# Validate required configuration
if [ -z "$SCRIPT_PATH" ] || [ -z "$SNAPSHOTS_BASE_DIR" ] || [ -z "$SERVICE_NAME" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    CONFIG_FILE="$SCRIPT_DIR/config.sh"

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
