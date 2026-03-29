#!/usr/bin/env python3
"""
Add new email addresses to the volleyball bot mailing list
Sends welcome email with preview and confirmation
"""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# File paths
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
MAILING_LIST_FILE = SCRIPT_DIR / "mailing_list.txt"


def load_config():
    """Load configuration"""
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def load_mailing_list():
    """Load current mailing list"""
    try:
        with open(MAILING_LIST_FILE, 'r') as f:
            return [line.strip() for line in f if line.strip() and '@' in line]
    except FileNotFoundError:
        return []


def save_to_mailing_list(email):
    """Add email to mailing list file"""
    with open(MAILING_LIST_FILE, 'a') as f:
        f.write(f"{email}\n")


def create_welcome_email(new_email, config):
    """Create the welcome email content"""
    subject = "Welcome to joshbot"
    
    body = f"""Hi,

You've been added to joshbot!

I'm an automated monitoring system that scrapes NY Urban's volleyball open play schedule. Specifically, it checks the Beacon/Fri location every 10 minutes for availableslots.

When slots become available, you'll get an instant email notification with:
*Date and time of available slots
*Gym location
*Skill level
*Direct link to register

The bot runs continuously on my rapsberry pi using playwright.

Happy volleyballing! 

This was an automated email. Please reach out if you notice any bugs or want any features implemented. I also don't know how to implement an unsubscribe feature, so if you want to be removed from the mailing list, please let me know.
    """
    
    return subject, body


def send_email(to_email, subject, body, config, cc_email=None):
    """Send email via Gmail SMTP"""
    msg = MIMEMultipart('alternative')
    msg['From'] = config['email']['from_address']
    msg['To'] = to_email
    msg['Subject'] = subject
    
    if cc_email:
        msg['Cc'] = cc_email
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Connect to Gmail SMTP
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(
            config['email']['from_address'],
            config['email']['app_password']
        )
        
        # Send to both To and CC
        recipients = [to_email]
        if cc_email:
            recipients.append(cc_email)
        
        server.send_message(msg)


def validate_email(email):
    """Basic email validation"""
    return '@' in email and '.' in email and len(email) > 5


def main():
    print("=" * 70)
    print("JOSHBOT - ADD TO MAILING LIST")
    print("=" * 70)
    print()
    
    # Load config
    try:
        config = load_config()
    except Exception as e:
        print(f"Error loading config: {e}")
        return
    
    # Load current mailing list
    current_list = load_mailing_list()
    print(f"Current mailing list has {len(current_list)} recipients:")
    for i, email in enumerate(current_list, 1):
        print(f"  {i}. {email}")
    print()
    
    # Get new email address
    while True:
        new_email = input("Enter email address to add (or 'q' to quit): ").strip()
        
        if new_email.lower() == 'q':
            print("Cancelled.")
            return
        
        if not validate_email(new_email):
            print("Invalid email format. Please try again.")
            continue
        
        if new_email in current_list:
            print(f"{new_email} is already in the mailing list!")
            retry = input("Add a different email? (y/n): ").strip().lower()
            if retry != 'y':
                return
            continue
        
        break
    
    print()
    print(f" Email to add: {new_email}")
    print()
    
    # Create welcome email
    subject, body = create_welcome_email(new_email, config)
    
    # Show preview
    print("=" * 70)
    print("EMAIL PREVIEW")
    print("=" * 70)
    print()
    print(f"From: {config['email']['from_address']}")
    print(f"To: {new_email}")
    print(f"Cc: {config['personal_email']}")
    print(f"Subject: {subject}")
    print()
    print("-" * 70)
    print(body)
    print("-" * 70)
    print()
    
    # Confirm sending
    confirm = input("Send this email and add to mailing list? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("Cancelled. Email not sent, address not added.")
        return
    
    try:
        # Add to mailing list
        save_to_mailing_list(new_email)
        print(f" Added {new_email} to mailing_list.txt")
        
        # Send welcome email
        send_email(
            new_email,
            subject,
            body,
            config,
            cc_email=config['personal_email']
        )
        print(f"Welcome email sent to {new_email}")
        print(f"CC sent to {config['personal_email']}")
        print()
        print("🎉 Done! They're now on the mailing list and have been notified.")
        
    except Exception as e:
        print(f"Error: {e}")
        print("The email may not have been sent, but check mailing_list.txt")


if __name__ == "__main__":
    main()