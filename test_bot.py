#!/usr/bin/env python3
"""
Test script for Volleyball Bot
Runs a single check cycle without the infinite loop
"""

import sys
from volleyball_bot import VolleyballBot, logger

def main():
    print("=" * 60)
    print("VOLLEYBALL BOT TEST MODE")
    print("=" * 60)
    print()
    
    try:
        bot = VolleyballBot()
        
        print("Configuration loaded successfully")
        print(f"Page URL: {bot.config['page_url']}")
        print(f"Personal Email: {bot.config['personal_email']}")
        print(f"From Address: {bot.config['email']['from_address']}")
        print(f"Check Interval: {bot.config['check_interval_minutes']} minutes")
        print()
        
        print(f"Mailing list loaded: {len(bot.mailing_list)} recipients")
        for email in bot.mailing_list:
            print(f"   - {email}")
        print()
        
        print(f"State loaded")
        date_states = bot.state.get('date_states', {})
        print(f"   Tracked dates: {len(date_states)}")
        if date_states:
            for date, info in date_states.items():
                print(f"   - {date}: {info['status']} (notified {info.get('times_notified', 0)}x)")
        print()
        
        print("Running single check cycle...")
        print("-" * 60)
        bot.run_check_cycle()
        print("-" * 60)
        print()
        
        print("Test completed successfully!")
        print()
        print("Next steps:")
        print("1. Check volleyball_bot.log for detailed output")
        print("2. If emails were sent, verify you received them")
        print("3. Run 'sudo systemctl start volleyball_bot.service' to start the bot")
        print()
        
    except KeyboardInterrupt:
        print("\n Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        print("\nCheck volleyball_bot.log for more details")
        sys.exit(1)

if __name__ == "__main__":
    main()