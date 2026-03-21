#!/usr/bin/env python3
"""
NY Urban Volleyball Open Play Slot Monitor Bot
Monitors the Beacon/Fri tab for Advanced and Advanced Intermediate slots and notifies via email
"""

import argparse
import json
import logging
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import List, Dict
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Configuration file paths
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
STATE_FILE = SCRIPT_DIR / "state.json"
MAILING_LIST_FILE = SCRIPT_DIR / "mailing_list.txt"
LOG_FILE = SCRIPT_DIR / "volleyball_bot.log"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class VolleyballBot:
    """Main bot class for monitoring volleyball slots"""
    
    def __init__(self):
        """Initialize the bot with configuration"""
        self.config = self.load_config()
        self.validate_config()
        self.state = self.load_state()
        self.mailing_list = self.load_mailing_list()
        
    def load_config(self) -> dict:
        """Load configuration from config.json"""
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {CONFIG_FILE}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            raise

    def validate_config(self):
        """Fail fast if config still contains placeholder values (all-caps strings)"""
        checks = {
            'personal_email': self.config.get('personal_email', ''),
            'email.from_address': self.config['email'].get('from_address', ''),
            'email.app_password': self.config['email'].get('app_password', ''),
        }
        errors = [
            f"  - {field}: '{value}'"
            for field, value in checks.items()
            if not value or value == value.upper()  # unfilled placeholders are ALL_CAPS
        ]
        if errors:
            raise ValueError("config.json has unfilled placeholder values:\n" + "\n".join(errors))
    
    def load_state(self) -> dict:
        """Load state from state.json or create new state"""
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)

            # Migration 1: notified_dates list → date_states dict (plain date keys)
            if 'notified_dates' in state and 'date_states' not in state:
                logger.info("Migrating state: notified_dates → date_states")
                state['date_states'] = {
                    date: {"status": "available", "notified": True, "last_notified": None, "times_notified": 1}
                    for date in state.pop('notified_dates')
                }
                with open(STATE_FILE, 'w') as f:
                    json.dump(state, f, indent=2)

            # Migration 2: plain date keys → date|level composite keys
            # Old bot only tracked Advanced Intermediate, so that's the safe assumption
            if 'date_states' in state:
                plain_keys = [k for k in state['date_states'] if '|' not in k]
                if plain_keys:
                    logger.info(f"Migrating {len(plain_keys)} plain date key(s) to date|level format")
                    for key in plain_keys:
                        state['date_states'][f"{key}|Advanced Intermediate"] = state['date_states'].pop(key)
                    with open(STATE_FILE, 'w') as f:
                        json.dump(state, f, indent=2)

            return state
        except FileNotFoundError:
            return {
                "date_states": {},
                "last_error_notification": None,
                "last_successful_check": None
            }
    
    def save_state(self):
        """Save current state to state.json"""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def load_mailing_list(self) -> List[str]:
        """Load email addresses from mailing_list.txt"""
        try:
            with open(MAILING_LIST_FILE, 'r') as f:
                emails = [line.strip() for line in f if line.strip() and '@' in line]
                logger.info(f"Loaded {len(emails)} email addresses from mailing list")
                return emails
        except FileNotFoundError:
            logger.error(f"Mailing list file not found: {MAILING_LIST_FILE}")
            return []
    
    def send_email(self, to_emails: List[str], subject: str, body: str, bcc_emails: List[str] = None):
        """Send email via Gmail SMTP. bcc_emails recipients are hidden from all other recipients."""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config['email']['from_address']
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            # Pass BCC addresses to the SMTP envelope but not the message headers
            # so BCC recipients are invisible to each other and to To recipients
            all_recipients = to_emails + (bcc_emails or [])

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(
                    self.config['email']['from_address'],
                    self.config['email']['app_password']
                )
                server.sendmail(
                    self.config['email']['from_address'],
                    all_recipients,
                    msg.as_string()
                )

            logger.info(f"Email sent to {len(to_emails)} recipient(s), {len(bcc_emails or [])} BCC'd")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_error_notification(self, error_message: str):
        """Send error notification to personal email (throttled to once per 24 hours)"""
        now = datetime.now().isoformat()
        last_error = self.state.get('last_error_notification')
        
        # Check if we've sent an error email in the last 24 hours
        if last_error:
            last_error_time = datetime.fromisoformat(last_error)
            if datetime.now() - last_error_time < timedelta(hours=24):
                logger.info("Error notification throttled (sent within last 24 hours)")
                return
        
        subject = "Volleyball Bot Error Alert"
        body = f"""
Hi Josh,

The volleyball bot encountered an error:

Error: {error_message}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The bot will continue attempting to run every 10 minutes.

- Your Volleyball Bot
        """
        
        if self.send_email([self.config['personal_email']], subject, body):
            self.state['last_error_notification'] = now
            self.save_state()
    
    def send_mailing_list_notification(self, slots: List[Dict]):
        """Send notification to mailing list about available slots"""
        if not slots:
            return
        
        # Build email body
        slot_info = []
        for slot in slots:
            slot_info.append(f"• {slot['date']} at {slot['gym']} ({slot['level']})")
        
        subject = f"Volleyball Slots Available - {len(slots)} found!"
        
        # Load custom message template or use default
        body = f"""
{self.config.get('mailing_list_message', 'Great news! Advanced volleyball slots are now available:')}

{chr(10).join(slot_info)}

View and register here: {self.config['page_url']}

Happy volleyballing!
        """
        
        self.send_email(
            to_emails=[self.config['personal_email']],
            subject=subject,
            body=body,
            bcc_emails=self.mailing_list
        )
    
    def send_announcement(self, changes: List[str]):
        """Send an announcement email to the mailing list with a list of changes"""
        today = datetime.now().strftime('%d/%m/%Y')
        subject = f"joshbot update {today}"

        bullet_points = '\n'.join(f"* {change}" for change in changes)

        body = f"""joshbot is excited to announce the following changes:
{bullet_points}

This was an automatically generated email. Please reply-all to this email if you notice any bugs or want to suggest any features/changes to joshbot or if you wish to update your email preferences (autonomous unsubscribe coming soon).
"""
        success = self.send_email(
            to_emails=[self.config['personal_email']],
            subject=subject,
            body=body,
            bcc_emails=self.mailing_list
        )
        if success:
            logger.info(f"Announcement sent with {len(changes)} change(s)")
        else:
            logger.error("Failed to send announcement")
        """Check for available Advanced and Advanced Intermediate slots using Playwright"""
        logger.info("Starting slot check...")
        
        try:
            with sync_playwright() as p:
                # Launch browser in headless mode
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                # Navigate to the page
                logger.info(f"Navigating to {self.config['page_url']}")
                page.goto(self.config['page_url'], wait_until='networkidle')
                
                # Click the Beacon/Fri tab and wait for AJAX response
                logger.info("Switching to Beacon/Fri tab...")
                page.evaluate("""
                    SwitchMenu('2','1','34','https://www.nyurban.com/wp-admin/admin-ajax.php','active')
                """)
                
                # Wait for the AJAX response and table to update
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(2000)  # Additional wait for table to populate
                
                # Parse ALL Advanced/Advanced Intermediate rows regardless of availability
                all_slots = []

                rows = page.query_selector_all('table tbody tr')
                logger.info(f"Found {len(rows)} rows in table")

                for row in rows:
                    try:
                        cells = row.query_selector_all('td')
                        if len(cells) < 7:
                            continue

                        # Structure: Select | Date | Gym | Level | Time | Fee | Available
                        date = cells[1].inner_text().strip()
                        gym = cells[2].inner_text().strip()
                        level = cells[3].inner_text().strip()
                        time = cells[4].inner_text().strip()
                        fee = cells[5].inner_text().strip()
                        availability = cells[6].inner_text().strip()

                        if "Advanced Intermediate" not in level and level.strip() != "Advanced":
                            continue

                        avail_lower = availability.lower()
                        is_sold_out = "sold out" in avail_lower
                        is_available = not is_sold_out and (avail_lower == "yes" or "space" in avail_lower)

                        all_slots.append({
                            'date': date,
                            'gym': gym,
                            'level': level,
                            'time': time,
                            'fee': fee,
                            'availability': availability,
                            'status': 'sold_out' if is_sold_out else ('available' if is_available else 'unknown')
                        })
                        logger.info(f"Scraped slot: {date} - {gym} - status: {'sold_out' if is_sold_out else 'available'}")

                    except Exception as e:
                        logger.warning(f"Error parsing row: {e}")
                        continue

                browser.close()

                logger.info(f"Scraped {len(all_slots)} Advanced/Advanced Intermediate slots total")
                return all_slots
                
        except Exception as e:
            logger.error(f"Error during slot check: {e}")
            raise
    
    def purge_past_dates(self):
        """Remove state entries whose session date has already passed"""
        today = datetime.now().date()
        to_remove = []

        for key in self.state['date_states']:
            try:
                # Key format: "Fri 03/06|Advanced Intermediate"
                date_str = key.split('|')[0].split(' ', 1)[1]  # "03/06"
                # No year in the scraped date — assume current year
                session_date = datetime.strptime(f"{date_str}/{today.year}", '%m/%d/%Y').date()
                if session_date < today:
                    to_remove.append(key)
            except (IndexError, ValueError):
                logger.warning(f"Could not parse date from state key: '{key}', skipping")

        if to_remove:
            for key in to_remove:
                del self.state['date_states'][key]
            logger.info(f"Purged {len(to_remove)} past date(s) from state")

    def run_check_cycle(self):
        """Run a single check cycle"""
        try:
            self.purge_past_dates()
            all_slots = self.check_slots()

            slots_to_notify = []
            now = datetime.now().isoformat()

            for slot in all_slots:
                date_key = f"{slot['date']}|{slot['level']}"
                existing = self.state['date_states'].get(date_key)

                if slot['status'] == 'available':
                    if existing is None:
                        # First time seeing this slot — notify
                        slots_to_notify.append(slot)
                        self.state['date_states'][date_key] = {
                            "status": "available",
                            "notified": True,
                            "last_notified": now,
                            "times_notified": 1
                        }
                    elif existing['status'] == 'sold_out':
                        # Was sold out, now has a cancellation — re-notify
                        logger.info(f"Slot re-opened after selling out: {slot['date']} ({slot['level']})")
                        slots_to_notify.append(slot)
                        existing['status'] = 'available'
                        existing['notified'] = True
                        existing['last_notified'] = now
                        existing['times_notified'] = existing.get('times_notified', 1) + 1
                    # else: still open from before, no spam

                elif slot['status'] == 'sold_out':
                    if existing is None:
                        # First time seeing this slot but already sold out — record it
                        self.state['date_states'][date_key] = {
                            "status": "sold_out",
                            "notified": False,
                            "last_notified": None,
                            "times_notified": 0
                        }
                    elif existing['status'] == 'available':
                        # Was open, now sold out — update silently
                        logger.info(f"Slot sold out: {slot['date']} ({slot['level']})")
                        existing['status'] = 'sold_out'

            if slots_to_notify:
                logger.info(f"Notifying about {len(slots_to_notify)} slot(s)")
                self.send_mailing_list_notification(slots_to_notify)
            else:
                logger.info("No new or re-opened slots found")

            self.state['last_successful_check'] = now
            self.save_state()

        except Exception as e:
            logger.error(f"Error in check cycle: {e}")
            self.send_error_notification(str(e))
            raise
    
    def run(self):
        """Main run loop - checks every 10 minutes"""
        logger.info("Volleyball bot started!")
        logger.info(f"Monitoring Beacon/Fri tab for Advanced and Advanced Intermediate slots")
        logger.info(f"Check interval: {self.config['check_interval_minutes']} minutes")
        logger.info(f"Mailing list size: {len(self.mailing_list)} recipients")
        
        while True:
            try:
                self.run_check_cycle()
            except Exception as e:
                logger.error(f"Check cycle failed: {e}")
            
            # Wait for next check
            sleep_seconds = self.config['check_interval_minutes'] * 60
            logger.info(f"Waiting {self.config['check_interval_minutes']} minutes until next check...")
            time.sleep(sleep_seconds)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='NY Urban Volleyball Slot Monitor Bot')
    parser.add_argument(
        '--announce',
        nargs='+',
        metavar='CHANGE',
        help='Send an announcement email to the mailing list. Each argument is a bullet point.'
    )
    args = parser.parse_args()

    try:
        bot = VolleyballBot()
        if args.announce:
            bot.send_announcement(args.announce)
        else:
            bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()