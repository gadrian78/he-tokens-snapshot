#!/bin/bash

# =========================================
# Complete Setup for Hive Portfolio Tracker
# Run after updating config.sh!
# =========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.sh"

echo "🔧 Setting up Multi-User Hive Portfolio Snapshot..."

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

echo "📝 Configuration loaded:"
echo "   Script path: $SCRIPT_PATH"
echo "   Base snapshots dir: $SNAPSHOTS_BASE_DIR"
echo "   Python path: $PYTHON_PATH"
echo "   Service name: $SERVICE_NAME"
echo "   Run time: $RUN_TIME"
echo "   Service will run as: $CURRENT_USER:$CURRENT_GROUP"
echo "   Users and their tokens:"
for username in "${USERNAMES[@]}"; do
    echo "     $username: ${USER_TOKENS[$username]}"
done
echo

# Verify script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Error: Script not found at $SCRIPT_PATH"
    echo "   Please update SCRIPT_PATH in config.sh"
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
if pip install $REQUIRED_PACKAGES; then
    echo "✅ Required packages installed"
else
    echo "❌ Failed to install required packages"
    deactivate
    exit 1
fi

# Check if there's a requirements.txt file
REQUIREMENTS_PATH="$(dirname "$SCRIPT_PATH")/$REQUIREMENTS_FILE"
if [ -f "$REQUIREMENTS_PATH" ]; then
    echo "📋 Installing from $REQUIREMENTS_FILE..."
    if pip install -r "$REQUIREMENTS_PATH"; then
        echo "✅ Requirements.txt packages installed"
    else
        echo "❌ Failed to install from $REQUIREMENTS_FILE"
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

###########################
# Loading setup_service.sh
###########################

if [[ $AUTO_SETUP_SERVICE == false ]]; then
    echo
    echo "Service and timer not automatically installed based on configuration setting."
    echo "If you want them installed, you can run setup_service.sh manually, or change AUTO_SETUP_SERVICE to true in config.sh and re-run setup.sh."
    echo
    exit 0
fi

SETUP_SERVICE_FILE="$SCRIPT_DIR/setup-service.sh"

# Check if setup_service.sh file exists
if [ ! -f "$SETUP_SERVICE_FILE" ]; then
    echo "❌ Error: Setup service file not found at $SETUP_SERVICE_FILE"
    echo "   Please make sure the setup_service.sh file is in the same directory as setup.sh."
    exit 1
fi

# Load configuration
echo "📋 Loading the setup service script from $SETUP_SERVICE_FILE..."
source "$SETUP_SERVICE_FILE"
