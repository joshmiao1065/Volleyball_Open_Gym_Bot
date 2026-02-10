# NY Urban Volleyball Slot Monitor Bot

Automated bot that monitors NY Urban's Beacon/Fri volleyball open play slots and notifies you when Advanced Intermediate slots become available.

You easily configure the configure.json for another link or website. 

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
- Lightweight and runs on my PiHole 

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

Probably easiest if you rename the files with "_example" in the name to remove the "example". Those would be
config_example.json to config.json, mailing_list_example.txt to mailing_list.txt, and state_example.json to state.json

1. You may configure the 'config.json' to specify an alternate site url, personal email, sender email, app password and check interval(minutes).
2. Modify 'mailing_list.txt' with one email per line

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

# View last 25 logs
tail -f ~/volleyball_bot/volleyball_bot.log -n 25

# View systemd service logs
sudo journalctl -u volleyball_bot.service -f

# View last 100 systemd logs
sudo journalctl -u volleyball_bot.service -n 100

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

#TroubleShooting

No Emails Being Sent

1. Verify Gmail app password in `config.json`
2. Check logs: `tail -f ~/volleyball_bot/volleyball_bot.log`
3. Test email manually:
   ```python
   python3 -c "from volleyball_bot import VolleyballBot; bot = VolleyballBot(); bot.send_email(['your@email.com'], 'Test', 'Testing')"
   ```

Playwright Issues

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

## Compatibility

- **OS**: Raspberry Pi OS (Debian-based) but will probably work in any environment tbh
- **Python**: 3.7+
- **Tested on**: Raspberry Pi 4 Model B
- **Browser**: Chromium (headless)

## License

This is a personal automation tool. Use responsibly and in accordance with NY Urban's terms of service.

## Support

For issues or questions:
1. Check the logs: `tail -f ~/volleyball_bot/volleyball_bot.log`
2. Verify service status: `sudo systemctl status volleyball_bot.service`
3. Review this README
4. Check that all files are in place

If you still can't figure out, ask gemini or claude lol.
After all that and you still can't figure it out, email me at josh.volleyball.bot@gmail.com

## Changelog

### v1.0.0 (Initial Release)
- Beacon/Fri monitoring
- Advanced Intermediate filtering
- Mailing list notifications
- Automated checkout
- Error handling
- Systemd integration
- Pi-hole compatible


```

### Editing Configuration
```bash
# Edit mailing list
nano ~/volleyball_bot/mailing_list.txt
# Then restart: sudo systemctl restart volleyball_bot.service

# Edit configuration
nano ~/volleyball_bot/config.json

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
