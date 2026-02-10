#!/usr/bin/env python3
"""
NY Urban Volleyball Open Play Slot Monitor Bot
Monitors the Beacon/Fri tab for Advanced Intermediate slots and notifies via email
"""

import json
import logging
import os
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import List, Dict, Optional
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
    
    def load_state(self) -> dict:
        """Load state from state.json or create new state"""
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Initialize new state
            return {
                "notified_dates": [],
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
    
    def send_email(self, to_emails: List[str], subject: str, body: str, is_html: bool = False):
        """Send email via Gmail SMTP"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config['email']['from_address']
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Connect to Gmail SMTP
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(
                    self.config['email']['from_address'],
                    self.config['email']['app_password']
                )
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {len(to_emails)} recipient(s)")
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
{self.config.get('mailing_list_message', 'Great news! Advanced Intermediate volleyball slots are now available:')}

{chr(10).join(slot_info)}

View and register here: {self.config['page_url']}

Happy volleyballing!
        """
        
        self.send_email(self.mailing_list, subject, body)
    
    def send_personal_notification(self, checkout_url: Optional[str], success: bool, slots: List[Dict]):
        """Send personal notification with checkout link"""
        subject = "Volleyball Bot - Checkout Ready!" if success else "🏐 Volleyball Bot - Slots Found (Checkout Failed)"
        
        slot_info = []
        for slot in slots:
            slot_info.append(f"• {slot['date']} at {slot['gym']} ({slot['level']})")
        
        if success and checkout_url:
            body = f"""
Hi Josh,

Successfully found and selected volleyball slots!

Selected Slots:
{chr(10).join(slot_info)}

Checkout Status: Successfully reached checkout page

Checkout Link: {checkout_url}

Please complete payment at your earliest convenience.

- Your Volleyball Bot
            """
        else:
            body = f"""
Hi Josh,

Found available volleyball slots but encountered an issue during checkout.

Available Slots:
{chr(10).join(slot_info)}

Checkout Status: Failed to complete checkout process

Please check the page manually: {self.config['page_url']}

- Your Volleyball Bot
            """
        
        self.send_email([self.config['personal_email']], subject, body)
    
    def check_slots(self) -> List[Dict]:
        """Check for available Advanced Intermediate slots using Playwright"""
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
                
                # Parse the table for available slots
                available_slots = []
                
                # Find all table rows
                rows = page.query_selector_all('table tbody tr')
                logger.info(f"Found {len(rows)} rows in table")
                
                for row in rows:
                    try:
                        # Get all cells in the row
                        cells = row.query_selector_all('td')
                        if len(cells) < 7:
                            continue
                        
                        # Extract data from cells
                        # Structure: Select | Date | Gym | Level | Time | Fee | Available
                        date = cells[1].inner_text().strip()
                        gym = cells[2].inner_text().strip()
                        level = cells[3].inner_text().strip()
                        time = cells[4].inner_text().strip()
                        fee = cells[5].inner_text().strip()
                        availability = cells[6].inner_text().strip()
                        
                        # Check if it matches our criteria
                        is_advanced_intermediate = "Advanced Intermediate" in level
                        is_available = availability.lower() == "yes" or ("space" in availability.lower() and availability.lower() != "sold out")
                        
                        if is_advanced_intermediate and is_available:
                            # Check if we've already notified about this date
                            if date not in self.state['notified_dates']:
                                slot_data = {
                                    'date': date,
                                    'gym': gym,
                                    'level': level,
                                    'time': time,
                                    'fee': fee,
                                    'availability': availability
                                }
                                available_slots.append(slot_data)
                                logger.info(f"Found available slot: {date} - {gym} - {level}")
                    
                    except Exception as e:
                        logger.warning(f"Error parsing row: {e}")
                        continue
                
                browser.close()
                
                logger.info(f"Found {len(available_slots)} new available slots")
                return available_slots
                
        except Exception as e:
            logger.error(f"Error during slot check: {e}")
            raise
    
    def select_slots_and_checkout(self, slots: List[Dict]) -> Optional[str]:
        """Select up to 4 available slots and attempt checkout"""
        logger.info(f"Attempting to select {min(len(slots), 4)} slots and checkout...")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                # Navigate to the page
                page.goto(self.config['page_url'], wait_until='networkidle')
                
                # Switch to Beacon/Fri tab
                page.evaluate("""
                    SwitchMenu('2','1','34','https://www.nyurban.com/wp-admin/admin-ajax.php','active')
                """)
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(2000)
                
                # Select up to 4 slots
                slots_to_select = slots[:4]
                selected_count = 0
                
                for i, slot in enumerate(slots_to_select):
                    try:
                        # The radio button ID increments - we need to find the correct row
                        # We'll use the date to match the row
                        rows = page.query_selector_all('table tbody tr')
                        
                        for row in rows:
                            cells = row.query_selector_all('td')
                            if len(cells) < 2:
                                continue
                            
                            row_date = cells[1].inner_text().strip()
                            if row_date == slot['date']:
                                # Find the radio button in this row
                                radio = row.query_selector('input[type="radio"]')
                                if radio:
                                    radio.click()
                                    selected_count += 1
                                    logger.info(f"Selected slot: {slot['date']}")
                                break
                    except Exception as e:
                        logger.warning(f"Failed to select slot {slot['date']}: {e}")
                
                if selected_count == 0:
                    logger.error("Failed to select any slots")
                    browser.close()
                    return None
                
                logger.info(f"Successfully selected {selected_count} slots")
                
                # Fill out the checkout form
                page.fill('input[name="f_first_name"]', self.config['checkout']['first_name'])
                page.fill('input[name="f_last_name"]', self.config['checkout']['last_name'])
                page.fill('input[name="f_email"]', self.config['checkout']['email'])
                page.fill('input[name="f_cemail"]', self.config['checkout']['email'])
                
                # Check the waiver checkbox
                waiver_checkbox = page.query_selector('label[for="check-4"]')
                if waiver_checkbox:
                    waiver_checkbox.click()
                else:
                    # Try alternative selector
                    page.check('input#check-4')
                
                logger.info("Filled out checkout form")
                
                # Click checkout button and wait for navigation
                page.click('input[type="submit"].btn_green')
                
                # Wait for navigation to payment page
                page.wait_for_load_state('networkidle', timeout=10000)
                
                # Get the checkout URL
                checkout_url = page.url
                
                browser.close()
                
                # Check if we reached the authorize.net payment page
                if 'authorize.net' in checkout_url:
                    logger.info(f"Successfully reached checkout page: {checkout_url}")
                    return checkout_url
                else:
                    logger.warning(f"Unexpected URL after checkout: {checkout_url}")
                    return checkout_url
                    
        except Exception as e:
            logger.error(f"Error during checkout process: {e}")
            return None
    
    def run_check_cycle(self):
        """Run a single check cycle"""
        try:
            # Check for available slots
            available_slots = self.check_slots()
            
            if available_slots:
                logger.info(f"Found {len(available_slots)} available slots!")
                
                # Send notification to mailing list
                self.send_mailing_list_notification(available_slots)
                
                # Attempt to select slots and checkout
                checkout_url = self.select_slots_and_checkout(available_slots)
                
                # Send personal notification
                self.send_personal_notification(
                    checkout_url,
                    checkout_url is not None,
                    available_slots
                )
                
                # Mark these dates as notified
                for slot in available_slots:
                    if slot['date'] not in self.state['notified_dates']:
                        self.state['notified_dates'].append(slot['date'])
                
                self.state['last_successful_check'] = datetime.now().isoformat()
                self.save_state()
            else:
                logger.info("No new available slots found")
                self.state['last_successful_check'] = datetime.now().isoformat()
                self.save_state()
                
        except Exception as e:
            logger.error(f"Error in check cycle: {e}")
            self.send_error_notification(str(e))
            raise
    
    def run(self):
        """Main run loop - checks every 10 minutes"""
        logger.info("Volleyball bot started!")
        logger.info(f"Monitoring Beacon/Fri tab for Advanced Intermediate slots")
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
    try:
        bot = VolleyballBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
