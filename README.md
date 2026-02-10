# NY Urban Volleyball Slot Monitor Bot

Automated bot that monitors NY Urban's Beacon/Fri volleyball open play slots and notifies you when Advanced Intermediate slots become available.

## Features

- Monitors Beacon/Fri tab every 10 minutes
- Filters for "Advanced Intermediate" level with availability
- Sends notifications to mailing list when slots open
- Automatically attempts to fill checkout form
- Sends personal notification with checkout link
- Continues monitoring for future dates after finding slots
- Smart duplicate prevention (won't spam about same dates)
- Error notifications with 24-hour throttling
- Auto-restart on failure via systemd
- Lightweight and Pi-hole compatible

## File Structure

```
volleyball_bot/
├── volleyball_bot.py      # Main bot script
├── config.json            # Configuration settings
├── state.json             # Persistent state (notified dates)
├── mailing_list.txt       # Email addresses (one per line)
├── requirements.txt       # Python dependencies
├── volleyball_bot.service # Systemd service file
├── volleyball_bot.log     # Log file (created automatically)
└── README.md             # This file
```

## Installation on Raspberry Pi

### Step 1: Install Python Dependencies

```bash
# Update package lists
sudo apt update

# Install Python 3 and pip (if not already installed)
sudo apt install python3 python3-pip -y

# Create directory for the bot
mkdir -p ~/volleyball_bot
cd ~/volleyball_bot

# Copy all files to this directory
# (volleyball_bot.py, config.json, state.json, mailing_list.txt, requirements.txt, volleyball_bot.service)

# Install Python packages
pip3 install -r requirements.txt --break-system-packages

# Install Playwright browsers
playwright install chromium

# Install Playwright system dependencies
playwright install-deps chromium
```

### Step 2: Configure the Bot

All configuration is already set in `config.json`, but you can customize:

1. **Mailing List Message**: Edit the `mailing_list_message` field in `config.json`
2. **Check Interval**: Change `check_interval_minutes` (default: 10)
3. **Add/Remove Emails**: Edit `mailing_list.txt` (one email per line)

### Step 3: Set Up Systemd Service

```bash
# Copy service file to systemd directory
sudo cp volleyball_bot.service /etc/systemd/system/

# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable volleyball_bot.service

# Start the service
sudo systemctl start volleyball_bot.service
```

### Step 4: Verify Installation

```bash
# Check service status
sudo systemctl status volleyball_bot.service

# View live logs
tail -f ~/volleyball_bot/volleyball_bot.log

# View systemd logs
sudo journalctl -u volleyball_bot.service -f
```

## Usage

### Managing the Service

```bash
# Start the bot
sudo systemctl start volleyball_bot.service

# Stop the bot
sudo systemctl stop volleyball_bot.service

# Restart the bot
sudo systemctl restart volleyball_bot.service

# Check status
sudo systemctl status volleyball_bot.service

# View logs
tail -f ~/volleyball_bot/volleyball_bot.log
```

### Managing the Mailing List

Simply edit the `mailing_list.txt` file:

```bash
nano ~/volleyball_bot/mailing_list.txt
```

Add or remove email addresses (one per line). Changes take effect on the next check cycle (no restart needed).

### Customizing Email Messages

Edit the `mailing_list_message` field in `config.json`:

```bash
nano ~/volleyball_bot/config.json
```

Then restart the service:

```bash
sudo systemctl restart volleyball_bot.service
```

### Resetting Notification History

If you want the bot to re-notify about dates it's already seen:

```bash
# Stop the service
sudo systemctl stop volleyball_bot.service

# Clear the notified dates
echo '{"notified_dates": [], "last_error_notification": null, "last_successful_check": null}' > ~/volleyball_bot/state.json

# Start the service
sudo systemctl start volleyball_bot.service
```

## How It Works

1. **Every 10 minutes**, the bot:
   - Navigates to the NY Urban open play page
   - Clicks the "Beacon / Fri." tab
   - Waits for the AJAX content to load
   - Parses the table for "Advanced Intermediate" slots with availability

2. **When slots are found**:
   - Sends email to entire mailing list with slot details
   - Attempts to select up to 4 slots
   - Fills out checkout form (name, email, waiver)
   - Captures the checkout/payment URL
   - Sends personal email with checkout link
   - Marks dates as notified to prevent spam

3. **Error handling**:
   - Logs all errors to `volleyball_bot.log`
   - Sends error notifications to your personal email
   - Throttled to one error email per 24 hours
   - Auto-restarts after crashes (via systemd)

## Email Notifications

### Mailing List Email
- **To**: Everyone in `mailing_list.txt`
- **Subject**: "Volleyball Slots Available - [X] found!"
- **Contains**: Date, gym, level, and link to registration page

### Personal Email (Success)
- **To**: joshuamiao03@gmail.com
- **Subject**: "Volleyball Bot - Checkout Ready!"
- **Contains**: Selected slots and direct checkout/payment link

### Personal Email (Error)
- **To**: joshuamiao03@gmail.com
- **Subject**: "Volleyball Bot Error Alert"
- **Contains**: Error details and timestamp
- **Frequency**: Max once per 24 hours

## Troubleshooting

### Bot Not Starting

```bash
# Check service status
sudo systemctl status volleyball_bot.service

# View detailed logs
sudo journalctl -u volleyball_bot.service -n 50

# Check if Playwright is installed
python3 -c "from playwright.sync_api import sync_playwright; print('OK')"
```

### No Emails Being Sent

1. Verify Gmail app password in `config.json`
2. Check logs: `tail -f ~/volleyball_bot/volleyball_bot.log`
3. Test email manually:
   ```python
   python3 -c "from volleyball_bot import VolleyballBot; bot = VolleyballBot(); bot.send_email(['your@email.com'], 'Test', 'Testing')"
   ```

### Bot Crashes Frequently

- Check logs for specific errors
- Ensure Raspberry Pi has stable internet
- Verify Pi-hole isn't blocking nyurban.com
- Increase system resources if needed

### Playwright Issues

```bash
# Reinstall Playwright browsers
playwright install chromium

# Reinstall dependencies
playwright install-deps chromium
```

## Monitoring

### View Real-Time Logs
```bash
tail -f ~/volleyball_bot/volleyball_bot.log
```

### Check State
```bash
cat ~/volleyball_bot/state.json
```

This shows:
- `notified_dates`: Dates already notified about
- `last_error_notification`: When last error email was sent
- `last_successful_check`: Last successful check timestamp

### Resource Usage
```bash
# Check if bot is running
ps aux | grep volleyball_bot

# Check memory usage
free -h

# Check CPU usage
top
```

## Advanced Configuration

### Change Check Interval

Edit `config.json`:
```json
{
  "check_interval_minutes": 5
}
```

Then restart: `sudo systemctl restart volleyball_bot.service`

### Run Multiple Instances

To monitor multiple locations:
1. Copy the entire directory
2. Modify `config.json` to monitor different tab
3. Create a new systemd service with different name
4. Update the JavaScript in the bot to switch to different tab

### Backup Configuration

```bash
# Backup all config files
tar -czf volleyball_bot_backup.tar.gz ~/volleyball_bot/*.json ~/volleyball_bot/*.txt
```

## Security Notes

- The `config.json` file contains your Gmail app password
- Keep this file secure with appropriate permissions:
  ```bash
  chmod 600 ~/volleyball_bot/config.json
  ```
- Never commit `config.json` to version control
- The app password is specific to this bot and can be revoked in Gmail settings

## Compatibility

- **OS**: Raspberry Pi OS (Debian-based)
- **Python**: 3.7+
- **Tested on**: Raspberry Pi 3/4 running Pi-hole
- **Browser**: Chromium (headless)

## License

This is a personal automation tool. Use responsibly and in accordance with NY Urban's terms of service.

## Support

For issues or questions:
1. Check the logs: `tail -f ~/volleyball_bot/volleyball_bot.log`
2. Verify service status: `sudo systemctl status volleyball_bot.service`
3. Review this README
4. Check that all files are in place

## Changelog

### v1.0.0 (Initial Release)
- Beacon/Fri monitoring
- Advanced Intermediate filtering
- Mailing list notifications
- Automated checkout
- Error handling
- Systemd integration
- Pi-hole compatible


# Volleyball Bot - Quick Reference

## Common Commands

### Service Management
```bash
# Start the bot
sudo systemctl start volleyball_bot.service

# Stop the bot
sudo systemctl stop volleyball_bot.service

# Restart the bot
sudo systemctl restart volleyball_bot.service

# Check if bot is running
sudo systemctl status volleyball_bot.service

# Enable auto-start on boot (already done during install)
sudo systemctl enable volleyball_bot.service

# Disable auto-start on boot
sudo systemctl disable volleyball_bot.service
```

### Viewing Logs
```bash
# View live logs (Ctrl+C to exit)
tail -f ~/volleyball_bot/volleyball_bot.log

# View last 50 lines
tail -n 50 ~/volleyball_bot/volleyball_bot.log

# View systemd service logs
sudo journalctl -u volleyball_bot.service -f

# View last 100 systemd logs
sudo journalctl -u volleyball_bot.service -n 100
```

### Editing Configuration
```bash
# Edit mailing list
nano ~/volleyball_bot/mailing_list.txt
# Then restart: sudo systemctl restart volleyball_bot.service

# Edit configuration
nano ~/volleyball_bot/config.json
# Then restart: sudo systemctl restart volleyball_bot.service

# View current state (what dates have been notified)
cat ~/volleyball_bot/state.json
```

### Testing
```bash
# Run a single test check (without infinite loop)
cd ~/volleyball_bot
python3 test_bot.py

# Test email sending
python3 -c "from volleyball_bot import VolleyballBot; bot = VolleyballBot(); bot.send_email(['your@email.com'], 'Test', 'Testing')"
```

### Troubleshooting
```bash
# Check if Python packages are installed
pip3 list | grep playwright

# Check if Playwright browsers are installed
playwright --version

# Reinstall Playwright browsers
playwright install chromium

# View detailed error logs
grep -i error ~/volleyball_bot/volleyball_bot.log

# Check service status and errors
sudo systemctl status volleyball_bot.service
```

### Maintenance
```bash
# Backup configuration
tar -czf volleyball_bot_backup_$(date +%Y%m%d).tar.gz ~/volleyball_bot/*.json ~/volleyball_bot/*.txt

# Clear notification history (will re-notify about all dates)
sudo systemctl stop volleyball_bot.service
echo '{"notified_dates": [], "last_error_notification": null, "last_successful_check": null}' > ~/volleyball_bot/state.json
sudo systemctl start volleyball_bot.service

# Update the bot code
cd ~/volleyball_bot
# Make your changes to volleyball_bot.py
sudo systemctl restart volleyball_bot.service
```

### Monitoring
```bash
# Check if bot process is running
ps aux | grep volleyball_bot

# Check system resources
htop

# Check memory usage
free -h

# Check disk space
df -h
```

## File Locations

| File | Path | Purpose |
|------|------|---------|
| Main Script | `~/volleyball_bot/volleyball_bot.py` | Bot code |
| Config | `~/volleyball_bot/config.json` | Settings |
| State | `~/volleyball_bot/state.json` | Notified dates |
| Mailing List | `~/volleyball_bot/mailing_list.txt` | Email recipients |
| Logs | `~/volleyball_bot/volleyball_bot.log` | Activity log |
| Service | `/etc/systemd/system/volleyball_bot.service` | Systemd service |

## Configuration Options

### config.json
- `page_url`: The NY Urban registration page
- `check_interval_minutes`: How often to check (default: 10)
- `personal_email`: Your email for personal notifications
- `email.from_address`: Bot's Gmail address
- `email.app_password`: Gmail app password
- `checkout.first_name`: Your first name
- `checkout.last_name`: Your last name
- `checkout.email`: Your email
- `mailing_list_message`: Custom message for group emails

### mailing_list.txt
- One email address per line
- Changes take effect on next check (no restart needed)
- Can add/remove at any time

### state.json
- `notified_dates`: Array of dates already notified
- `last_error_notification`: ISO timestamp of last error email
- `last_successful_check`: ISO timestamp of last successful check

## Email Types

### 1. Mailing List Notification
- **Trigger**: Available slots found
- **To**: Everyone in mailing_list.txt
- **Subject**: Volleyball Slots Available - [X] found!
- **Contains**: Dates, gyms, levels, link

### 2. Personal Success Notification
- **Trigger**: Successfully reached checkout
- **To**: Personal email only
- **Subject**: Volleyball Bot - Checkout Ready!
- **Contains**: Selected slots, checkout link

### 3. Personal Failure Notification
- **Trigger**: Slots found but checkout failed
- **To**: Personal email only
- **Subject**: Volleyball Bot - Slots Found (Checkout Failed)
- **Contains**: Available slots, error info

### 4. Error Notification
- **Trigger**: Bot encounters an error
- **To**: Personal email only
- **Subject**: Volleyball Bot Error Alert
- **Contains**: Error message, timestamp
- **Throttle**: Max once per 24 hours

## Quick Diagnostic Checklist

If bot isn't working:
- [ ] Service is running: `sudo systemctl status volleyball_bot.service`
- [ ] Logs show activity: `tail volleyball_bot.log`
- [ ] Config file is correct: `cat config.json`
- [ ] Mailing list has emails: `cat mailing_list.txt`
- [ ] Network is working: `ping google.com`
- [ ] Playwright is installed: `playwright --version`
- [ ] Python packages installed: `pip3 list | grep playwright`

If emails aren't sending:
- [ ] Gmail app password is correct in config.json
- [ ] Bot email is josh.volleyball.bot@gmail.com
- [ ] Test email manually: See testing section above
- [ ] Check spam folder
- [ ] Verify email addresses in mailing_list.txt

## Performance Notes

- **CPU Usage**: Low (only active during checks)
- **Memory**: ~200-300MB during checks, ~50MB idle
- **Network**: Minimal (only HTTPS to nyurban.com and Gmail)
- **Disk**: Logs rotate automatically, minimal space
- **Pi-hole**: Compatible, won't interfere

## Safety Features

- Auto-restart on crash (systemd)
- Error notifications with throttling
- Duplicate prevention (won't spam same dates)
- Graceful error handling
- Comprehensive logging
- State persistence across restarts
