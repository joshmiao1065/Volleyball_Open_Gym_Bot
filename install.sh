#!/bin/bash
# Volleyball Bot Installation Script for Raspberry Pi
# Run this script as: bash install.sh

set -e  # Exit on any error

echo "=================================="
echo "Volleyball Bot Installation"
echo "=================================="
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if running as regular user (not root)
if [ "$EUID" -eq 0 ]; then
    echo "Please run this script as a regular user (not sudo)"
    echo "The script will prompt for sudo when needed"
    exit 1
fi

echo "Step 1: Installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip

echo ""
echo "Step 2: Installing Python packages..."
pip3 install -r requirements.txt --break-system-packages

echo ""
echo "Step 3: Installing Playwright browsers..."
playwright install chromium

echo ""
echo "Step 4: Installing Playwright system dependencies..."
sudo playwright install-deps chromium

echo ""
echo "Step 5: Setting up config files from examples..."
for example in config_example.json state_example.json mailing_list_example.txt; do
    real="${example/_example/}"
    real="${real/_example./\.}"
    # Derive real filename: config_example.json -> config.json, mailing_list_example.txt -> mailing_list.txt
    real=$(echo "$example" | sed 's/_example//')
    if [ ! -f "$real" ]; then
        cp "$example" "$real"
        echo "  Created $real from $example"
    else
        echo "  $real already exists, skipping"
    fi
done
chmod 600 config.json
echo "  Reminder: fill in your credentials in config.json and emails in mailing_list.txt"

echo ""
echo "Step 6: Installing systemd service..."
sudo cp volleyball_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable volleyball_bot.service

echo ""
echo "=================================="
echo "Installation Complete!"
echo "=================================="
echo ""
echo "To start the bot:"
echo "  sudo systemctl start volleyball_bot.service"
echo ""
echo "To check status:"
echo "  sudo systemctl status volleyball_bot.service"
echo ""
echo "To view logs:"
echo "  tail -f volleyball_bot.log"
echo ""
echo "To edit mailing list:"
echo "  nano mailing_list.txt"
echo ""
echo "For more information, see README.md"
echo ""

read -p "Would you like to start the bot now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl start volleyball_bot.service
    echo ""
    echo "Bot started!"
    echo ""
    echo "Showing last 20 log lines..."
    sleep 2
    tail -n 20 volleyball_bot.log
    echo ""
    echo "Use 'tail -f volleyball_bot.log' to follow logs in real-time"
fi

echo ""
echo "Happy volleyballing!"