#!/bin/bash

# =============================================================================
# HIVE PORTFOLIO TRACKER CONFIGURATION
# =============================================================================
# Edit the values below to customize your setup
# This is the ONLY file you need to modify!
# =============================================================================

# -----------------------------------------------------------------------------
# PATHS AND LOCATIONS
# -----------------------------------------------------------------------------
# Path to your he-tokens-snapshot.py script
SCRIPT_PATH="/home/[path-to-project]/take-snapshot.py"

# Base directory where snapshots will be stored
SNAPSHOTS_BASE_DIR="/home/[path-to-snapshots]"

# Python executable path (leave as "auto" to use our virtual environment)
PYTHON_PATH="auto"

# -----------------------------------------------------------------------------
# USER ACCOUNTS AND TOKENS
# -----------------------------------------------------------------------------
# Add users and their tokens here
# Format: USER_TOKENS["username"]="token1 token2 token3"
# 
# Examples:
# USER_TOKENS["alice"]="LEO SPS DEC SWAP.HIVE"
# USER_TOKENS["bob"]="LEO BEE PIZZA BEED"
# USER_TOKENS["charlie"]="SPS DEC VOUCHER CHAOS"
# USER_TOKENS["diana"]="LEO BEE SPS DEC SWAP.HIVE PIZZA"

declare -A USER_TOKENS
USER_TOKENS["alice"]="LEO SPS DEC SWAP.HIVE"
USER_TOKENS["bob"]="LEO BEE PIZZA BEED"
USER_TOKENS["charlie"]="SPS DEC VOUCHER CHAOS"
USER_TOKENS["diana"]="LEO BEE SPS DEC SWAP.HIVE PIZZA"

# -----------------------------------------------------------------------------
# SERVICE CONFIGURATION
# -----------------------------------------------------------------------------
# Autonatically set ups service and timer (after previously removing previous ones, if they exist)?
# True if yes, False if no
AUTO_SETUP_SERVICE=true
# Name of the systemd service (change if you want multiple instances)
SERVICE_NAME="hive-portfolio-tracker"

# Service description
SERVICE_DESCRIPTION="Hive Portfolio Tracker Service"

# What time to run daily (24-hour format: HH:MM:SS)
RUN_TIME="08:00:00"

# Random delay to avoid server load spikes (seconds, 0-600 = 0-10 minutes)
RANDOMIZED_DELAY_SEC=600

# Service timeout in seconds
TIMEOUT_START_SEC=900

# Run missed timers after system downtime (true/false)
PERSISTENT=true

# -----------------------------------------------------------------------------
# PYTHON DEPENDENCIES
# -----------------------------------------------------------------------------
# Required Python packages (space-separated)
REQUIRED_PACKAGES="hiveengine prettytable requests"

# Requirements file name (if you have one)
REQUIREMENTS_FILE="requirements.txt"

# -----------------------------------------------------------------------------
# RUNTIME SETTINGS
# -----------------------------------------------------------------------------
# Delay between processing different users (seconds)
DELAY_BETWEEN_USERS_SEC=5

# Enable quiet mode for the script (true/false)
ENABLE_QUIET_MODE=true

# Enable logging output (true/false)
ENABLE_LOGGING=true

# =============================================================================
# END OF CONFIGURATION
# =============================================================================
# Don't modify anything below this line unless you know what you're doing!
