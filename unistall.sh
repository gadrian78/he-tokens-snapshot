#!/bin/bash

# =============================================================================
# HIVE PORTFOLIO TRACKER UNINSTALLER
# =============================================================================
# This script removes all components installed by the setup script
# It automatically reads configuration from config.sh
# =============================================================================

# Load configuration
CONFIG_FILE="config.sh"

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "❌ Error: Configuration file '$CONFIG_FILE' not found!"
    echo "   Please ensure config.sh is in the same directory as this script."
    exit 1
fi

echo "📄 Loading configuration from: $CONFIG_FILE"
source "$CONFIG_FILE"

# Validate required variables
if [[ -z "$SCRIPT_PATH" || -z "$SNAPSHOTS_BASE_DIR" || -z "$SERVICE_NAME" ]]; then
    echo "❌ Error: Configuration file is missing required variables!"
    echo "   Required: SCRIPT_PATH, SNAPSHOTS_BASE_DIR, SERVICE_NAME"
    exit 1
fi

echo "✅ Configuration loaded successfully"
echo

# Derive additional paths from configuration
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
VENV_PATH="$SCRIPT_DIR/venv"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
TIMER_FILE="/etc/systemd/system/$SERVICE_NAME.timer"
WRAPPER_SCRIPT="/usr/local/bin/${SERVICE_NAME}-runner.sh"

echo "🗑️ Hive Portfolio Snapshot Uninstaller"
echo "======================================="
echo
echo "📋 Configuration Summary:"
echo "   • Service name: $SERVICE_NAME"
echo "   • Script path: $SCRIPT_PATH"
echo "   • Snapshots directory: $SNAPSHOTS_BASE_DIR"
echo "   • Service files: /etc/systemd/system/$SERVICE_NAME.*"
echo "   • Wrapper script: $WRAPPER_SCRIPT"
echo
echo "⚠️  WARNING: This will completely remove:"
echo "   • Systemd service and timer files"
echo "   • Wrapper script"
echo "   • Python virtual environment"
echo "   • All snapshot data and directories"
echo "   • Script files and parent directories"
echo
echo "📁 Locations that will be removed:"
echo "   • Service file: $SERVICE_FILE"
echo "   • Timer file: $TIMER_FILE"
echo "   • Wrapper script: $WRAPPER_SCRIPT"
echo "   • Virtual environment: $VENV_PATH"
echo "   • Snapshots directory: $SNAPSHOTS_BASE_DIR"
echo "   • Script directory: $SCRIPT_DIR"
echo

# Check what actually exists
echo "🔍 Checking what's currently installed..."
items_found=0

# Check systemd files
if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    echo "   ✅ Found systemd service/timer"
    items_found=$((items_found + 1))
fi

if [ -f "$SERVICE_FILE" ]; then
    echo "   ✅ Found service file"
    items_found=$((items_found + 1))
fi

if [ -f "$TIMER_FILE" ]; then
    echo "   ✅ Found timer file"
    items_found=$((items_found + 1))
fi

if [ -f "$WRAPPER_SCRIPT" ]; then
    echo "   ✅ Found wrapper script"
    items_found=$((items_found + 1))
fi

if [ -d "$VENV_PATH" ]; then
    echo "   ✅ Found virtual environment"
    items_found=$((items_found + 1))
fi

if [ -d "$SNAPSHOTS_BASE_DIR" ]; then
    echo "   ✅ Found snapshots directory"
    items_found=$((items_found + 1))
fi

if [ -d "$SCRIPT_DIR" ]; then
    echo "   ✅ Found script directory"
    items_found=$((items_found + 1))
fi

if [ "$items_found" -eq 0 ]; then
    echo "   ℹ️  No Hive Portfolio components found to remove"
    echo "   Either nothing was installed or it's already been removed"
    exit 0
fi

echo
echo "📊 Found $items_found component(s) to remove"
echo

# Confirmation prompt
echo "🔥 Are you sure you want to completely remove all Hive Portfolio components?"
echo "   This action cannot be undone!"
echo
read -p "Type 'Y' to confirm removal: " -n 1 -r
echo
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Uninstall cancelled"
    echo "   No changes were made"
    exit 0
fi

echo "🚀 Starting uninstall process..."
echo

# Step 1: Stop and disable systemd services
echo "🛑 Stopping and disabling systemd services..."

if systemctl is-active --quiet "$SERVICE_NAME.timer" 2>/dev/null; then
    sudo systemctl stop "$SERVICE_NAME.timer"
    echo "   ✅ Stopped timer"
fi

if systemctl is-enabled --quiet "$SERVICE_NAME.timer" 2>/dev/null; then
    sudo systemctl disable "$SERVICE_NAME.timer"
    echo "   ✅ Disabled timer"
fi

if systemctl is-active --quiet "$SERVICE_NAME.service" 2>/dev/null; then
    sudo systemctl stop "$SERVICE_NAME.service"
    echo "   ✅ Stopped service"
fi

# Step 2: Remove systemd files
echo "🗂️ Removing systemd files..."

if [ -f "$SERVICE_FILE" ]; then
    sudo rm -f "$SERVICE_FILE"
    echo "   ✅ Removed service file"
fi

if [ -f "$TIMER_FILE" ]; then
    sudo rm -f "$TIMER_FILE"
    echo "   ✅ Removed timer file"
fi

# Step 3: Remove wrapper script
echo "📜 Removing wrapper script..."

if [ -f "$WRAPPER_SCRIPT" ]; then
    sudo rm -f "$WRAPPER_SCRIPT"
    echo "   ✅ Removed wrapper script"
fi

# Step 4: Reload systemd
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "   ✅ Systemd daemon reloaded"

# Step 5: Remove virtual environment
echo "🐍 Removing Python virtual environment..."

if [ -d "$VENV_PATH" ]; then
    rm -rf "$VENV_PATH"
    echo "   ✅ Removed virtual environment: $VENV_PATH"
fi

# Step 6: Remove snapshots directory and all data
echo "📊 Removing snapshots directory and all data..."

if [ -d "$SNAPSHOTS_BASE_DIR" ]; then
    # Show what we're about to delete
    if [ "$(ls -A "$SNAPSHOTS_BASE_DIR" 2>/dev/null)" ]; then
        echo "   📋 Snapshot data found:"
        ls -la "$SNAPSHOTS_BASE_DIR" | head -10
        if [ "$(ls -A "$SNAPSHOTS_BASE_DIR" | wc -l)" -gt 8 ]; then
            echo "   ... (and more files)"
        fi
    fi
    
    rm -rf "$SNAPSHOTS_BASE_DIR"
    echo "   ✅ Removed snapshots directory: $SNAPSHOTS_BASE_DIR"
fi

# Step 7: Remove script directory (if it exists and is not empty of other important files)
echo "📁 Removing script directory..."

if [ -d "$SCRIPT_DIR" ]; then
    # Be careful - only remove if it looks like our directory
    if [ -f "$SCRIPT_PATH" ] || [ -d "$SCRIPT_DIR/venv" ]; then
        echo "   📋 Script directory contents:"
        ls -la "$SCRIPT_DIR" 2>/dev/null || echo "   (empty or inaccessible)"
        
        # Extra confirmation for script directory
        echo
        echo "   ⚠️  About to remove entire script directory: $SCRIPT_DIR"
        read -p "   Confirm removal of script directory? (Y/n): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            rm -rf "$SCRIPT_DIR"
            echo "   ✅ Removed script directory: $SCRIPT_DIR"
        else
            echo "   ⏭️  Skipped script directory removal"
        fi
    else
        echo "   ⚠️  Script directory doesn't look like a Hive Portfolio directory"
        echo "   🛡️  Skipping removal for safety: $SCRIPT_DIR"
    fi
fi

# Step 8: Clean up any remaining systemd references
echo "🧹 Final cleanup..."

# Reset failed units
sudo systemctl reset-failed "$SERVICE_NAME.service" 2>/dev/null || true
sudo systemctl reset-failed "$SERVICE_NAME.timer" 2>/dev/null || true

echo "   ✅ Cleaned up systemd references"

# Step 9: Verify removal
echo "🔍 Verifying removal..."

remaining_items=0

if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    echo "   ⚠️  Systemd units still found"
    remaining_items=$((remaining_items + 1))
fi

if [ -f "$SERVICE_FILE" ]; then
    echo "   ⚠️  Service file still exists"
    remaining_items=$((remaining_items + 1))
fi

if [ -f "$TIMER_FILE" ]; then
    echo "   ⚠️  Timer file still exists"
    remaining_items=$((remaining_items + 1))
fi

if [ -f "$WRAPPER_SCRIPT" ]; then
    echo "   ⚠️  Wrapper script still exists"
    remaining_items=$((remaining_items + 1))
fi

if [ -d "$VENV_PATH" ]; then
    echo "   ⚠️  Virtual environment still exists"
    remaining_items=$((remaining_items + 1))
fi

if [ -d "$SNAPSHOTS_BASE_DIR" ]; then
    echo "   ⚠️  Snapshots directory still exists"
    remaining_items=$((remaining_items + 1))
fi

if [ "$remaining_items" -eq 0 ]; then
    echo "   ✅ All components successfully removed"
else
    echo "   ⚠️  $remaining_items component(s) may still exist"
fi

echo
echo "🎉 Uninstall completed!"
echo
echo "📋 Summary:"
echo "   • Stopped and disabled systemd timer and service"
echo "   • Removed systemd service and timer files"
echo "   • Removed wrapper script"
echo "   • Removed Python virtual environment"
echo "   • Removed all snapshot data"
echo "   • Removed script directory (if confirmed)"
echo
echo "🧹 Your system has been cleaned up!"
echo

# Optional: Show what systemd timers are still active
echo "⏰ Remaining active timers on your system:"
sudo systemctl list-timers --no-pager | head -5
echo

echo "✅ Uninstall process complete!"
