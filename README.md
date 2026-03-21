# NY Urban Volleyball Slot Monitor Bot

Automated bot that monitors NY Urban's Beacon/Fri volleyball open play slots and notifies a mailing list when Advanced or Advanced Intermediate slots become available — including when a sold-out slot reopens due to a cancellation.

You can easily configure `config.json` for a different page URL or check interval.

## Features

- Monitors Beacon/Fri tab on a configurable interval (default: 10 minutes)
- Filters for **Advanced** and **Advanced Intermediate** levels
- Notifies mailing list when slots open **or reopen after selling out**
- Tracks per-slot status (`available` / `sold_out`) to prevent spam and catch cancellations
- Mailing list always BCC'd — recipients cannot see each other's addresses
- Startup validation — fails immediately if `config.json` still has placeholder values
- Manual announcement emails via `--announce` flag
- Error notifications with 24-hour throttling
- Auto-restart on failure via systemd
- Lightweight, runs on a Pi-hole

## File Structure

```
volleyball_bot/
├── volleyball_bot.py          # Main bot script
├── config.json                # Your configuration (gitignored)
├── config_example.json        # Template — fill in and rename
├── state.json                 # Persistent slot state (gitignored)
├── state_example.json         # Template for fresh installs
├── mailing_list.txt           # Email recipients (gitignored)
├── mailing_list_example.txt   # Template
├── test_bot.py                # Single-cycle test runner
├── requirements.txt           # Python dependencies
├── volleyball_bot.service     # Systemd service file
├── volleyball_bot.log         # Log file (created automatically)
└── README.md                  # This file
```

## Installation on Raspberry Pi

### Step 1: Clone the repo and install dependencies

```bash
mkdir -p ~/volleyball_bot
cd ~/volleyball_bot
git clone https://github.com/joshmiao1065/Volleyball_Open_Gym_Bot.git .

sudo apt update
sudo apt install python3 python3-pip -y

pip3 install -r requirements.txt --break-system-packages

playwright install chromium
sudo playwright install-deps chromium
```

### Step 2: Run the install script

The install script handles the rest — it copies example files, sets permissions, and registers the systemd service:

```bash
bash install.sh
```

The script will:
- Copy `config_example.json` → `config.json`, `state_example.json` → `state.json`, and `mailing_list_example.txt` → `mailing_list.txt` (only if they don't already exist)
- Set secure permissions (`chmod 600`) on `config.json`
- Register and enable the systemd service

### Step 3: Fill in your configuration

```bash
nano ~/volleyball_bot/config.json
```

All fields must be filled — the bot will refuse to start if any placeholder values (ALL_CAPS) remain. See [Configuration Options](#configuration-options) below.

```bash
nano ~/volleyball_bot/mailing_list.txt
```

Add one email address per line.

### Step 4: Start and verify

```bash
sudo systemctl start volleyball_bot.service
sudo systemctl status volleyball_bot.service
tail -f ~/volleyball_bot/volleyball_bot.log
```

---

## How It Works

**Every 10 minutes**, the bot:
1. Purges past session dates from `state.json`
2. Navigates to the NY Urban open play page
3. Switches to the Beacon/Fri tab and waits for the AJAX table to load
4. Scrapes **all** Advanced and Advanced Intermediate rows, regardless of availability

**For each slot found**, it checks the slot's current status against `state.json`:

| Situation | Action |
|-----------|--------|
| New slot, available | Notify mailing list |
| Known slot, was `sold_out`, now available | Re-notify — someone cancelled |
| Known slot, still `available` | No action — no spam |
| Any slot now `sold_out` | Update state silently, watch for cancellations |

**State is tracked per `date + level`** so Advanced and Advanced Intermediate sessions on the same date are handled independently.

**On notification**:
- Sends email to entire mailing list with slot details and registration link

**Error handling**:
- Logs all errors to `volleyball_bot.log`
- Sends error notification to personal email, throttled to once per 24 hours
- Auto-restarts after crashes via systemd

---

## State Schema

`state.json` tracks every slot the bot has seen that hasn't passed yet. Past dates are automatically purged at the start of each check cycle.

```json
{
  "date_states": {
    "Fri 07/18|Advanced": {
      "status": "available",
      "notified": true,
      "last_notified": "2026-07-10T08:15:00",
      "times_notified": 1
    },
    "Fri 07/18|Advanced Intermediate": {
      "status": "sold_out",
      "notified": true,
      "last_notified": "2026-07-09T14:22:00",
      "times_notified": 1
    },
    "Fri 07/25|Advanced Intermediate": {
      "status": "available",
      "notified": true,
      "last_notified": "2026-07-11T09:00:00",
      "times_notified": 2
    }
  },
  "last_error_notification": null,
  "last_successful_check": "2026-07-11T09:00:00"
}
```

**Automatic migration**: if your existing `state.json` uses the old `notified_dates` array format, or plain date keys without a level suffix, the bot will migrate it automatically on first run. No manual changes needed.

### Resetting Notification History

To make the bot re-notify about all slots from scratch:

```bash
sudo systemctl stop volleyball_bot.service
echo '{"date_states": {}, "last_error_notification": null, "last_successful_check": null}' > ~/volleyball_bot/state.json
sudo systemctl start volleyball_bot.service
```

---

## Configuration Options

### config.json

| Field | Description |
|-------|-------------|
| `page_url` | NY Urban registration page URL |
| `check_interval_minutes` | How often to check (default: `10`) |
| `personal_email` | Your email for error notifications |
| `email.from_address` | Gmail address the bot sends from |
| `email.app_password` | [Gmail App Password](https://myaccount.google.com/apppasswords) for the sender account |
| `mailing_list_message` | Custom intro line in group notification emails |

### mailing_list.txt
- One email address per line
- Changes take effect on the next check cycle — no restart needed

---

## Email Types

### 1. Slot Notification
- **Trigger**: New or reopened slots found
- **To**: `joshuamiao03@gmail.com`
- **BCC**: Everyone in `mailing_list.txt`
- **Subject**: `Volleyball Slots Available - [X] found!`
- **Contains**: Date, gym, level, registration link

### 2. Announcement
- **Trigger**: Manually sent via `--announce` flag
- **To**: `joshuamiao03@gmail.com`
- **BCC**: Everyone in `mailing_list.txt`
- **Subject**: `joshbot update DD/MM/YYYY`
- **Contains**: Bullet-pointed list of changes

### 3. Error Notification
- **Trigger**: Unhandled exception during a check cycle
- **To**: `joshuamiao03@gmail.com` only
- **Subject**: `Volleyball Bot Error Alert`
- **Throttle**: Max once per 24 hours

> All emails use BCC for the mailing list so recipients cannot see each other's addresses.

---

## Usage Reference

### Service Management

```bash
sudo systemctl start volleyball_bot.service
sudo systemctl stop volleyball_bot.service
sudo systemctl restart volleyball_bot.service
sudo systemctl status volleyball_bot.service
```

### Logs

```bash
# Live log
tail -f ~/volleyball_bot/volleyball_bot.log

# Last 25 lines
tail -n 25 ~/volleyball_bot/volleyball_bot.log

# Errors only
grep -i error ~/volleyball_bot/volleyball_bot.log

# Systemd journal
sudo journalctl -u volleyball_bot.service -f
sudo journalctl -u volleyball_bot.service -n 100
```

### Testing

```bash
# Run a single check cycle (no infinite loop)
cd ~/volleyball_bot
python3 test_bot.py

# Test email sending directly
python3 -c "from volleyball_bot import VolleyballBot; bot = VolleyballBot(); bot.send_email(['your@email.com'], 'Test', 'Testing')"
```

### Sending Announcements

```bash
python3 volleyball_bot.py --announce "Fixed cancellation detection" "Added Advanced level monitoring"
```

Each argument after `--announce` becomes a bullet point in the email. The subject is automatically set to `joshbot update DD/MM/YYYY` using today's date. The mailing list is BCC'd.

### Maintenance

```bash
# Backup config and state
tar -czf volleyball_bot_backup_$(date +%Y%m%d).tar.gz ~/volleyball_bot/*.json ~/volleyball_bot/*.txt

# Pull latest code from GitHub
sudo systemctl stop volleyball_bot.service
cd ~/volleyball_bot
git pull origin main
sudo systemctl start volleyball_bot.service
```

---

## File Locations

| File | Path | Purpose |
|------|------|---------|
| Main Script | `~/volleyball_bot/volleyball_bot.py` | Bot code |
| Config | `~/volleyball_bot/config.json` | Credentials and settings |
| State | `~/volleyball_bot/state.json` | Per-slot tracking |
| Mailing List | `~/volleyball_bot/mailing_list.txt` | Notification recipients |
| Logs | `~/volleyball_bot/volleyball_bot.log` | Activity and error log |
| Service | `/etc/systemd/system/volleyball_bot.service` | Systemd unit file |

---

## Troubleshooting

**Bot won't start / "unfilled placeholder values" error**
Fill in all fields in `config.json`. The bot validates on startup and will exit immediately if any ALL_CAPS placeholder values remain.

**No emails being sent**
1. Verify your Gmail App Password in `config.json` (not your regular Gmail password)
2. Check logs: `tail -f ~/volleyball_bot/volleyball_bot.log`
3. Test manually: `python3 -c "from volleyball_bot import VolleyballBot; bot = VolleyballBot(); bot.send_email(['your@email.com'], 'Test', 'Testing')"`

**Playwright / browser issues**
```bash
playwright install chromium
sudo playwright install-deps chromium
```

**Bot notified about a date but slot was already sold out**
This is expected on the very first run after upgrading from v1.0. The bot will now track that slot as sold out and re-notify if it reopens.

---

## Security Notes

`config.json` contains your Gmail App Password. Keep it secure:
```bash
chmod 600 ~/volleyball_bot/config.json
```

The file is gitignored and will never be committed. Only `config_example.json` (with placeholder values) is tracked by git.

---

## Compatibility

- **OS**: Raspberry Pi OS (Debian-based), should work on any Linux
- **Python**: 3.7+
- **Tested on**: Raspberry Pi 4 Model B
- **Browser**: Chromium (headless)

---

## Changelog

### v2.1.0
- Mailing list now always BCC'd — recipients cannot see each other's addresses
- `joshuamiao03@gmail.com` is the explicit direct recipient on all emails
- Added `--announce` flag for sending update emails to the mailing list
- Removed automated checkout and personal checkout notifications

### v2.0.0
- Added **cancellation detection** — bot re-notifies when a sold-out slot reopens
- Replaced `notified_dates` list with `date_states` dict for full per-slot status tracking (`available` / `sold_out`)
- Extended monitoring to include **Advanced** level in addition to Advanced Intermediate
- State key is now `date|level` composite to handle multiple levels on the same date
- Automatic state migration from v1.0 format — no manual changes needed
- `install.sh` now auto-copies example files on fresh installs
- Startup config validation — bot fails fast with a clear error if placeholders aren't filled
- Automatic purge of past session dates from `state.json` on each cycle
- Removed unused `import os`

### v1.0.0
- Beacon/Fri monitoring
- Advanced Intermediate filtering
- Mailing list notifications
- Automated checkout
- Error handling with 24-hour throttle
- Systemd integration
- Pi-hole compatible

---

## Support

1. Check the logs: `tail -f ~/volleyball_bot/volleyball_bot.log`
2. Verify service status: `sudo systemctl status volleyball_bot.service`
3. Review this README

If you still can't figure it out, ask Gemini or Claude lol.
After all that, email: josh.volleyball.bot@gmail.com