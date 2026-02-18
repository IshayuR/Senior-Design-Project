#!/usr/bin/env python3
"""
Watch schedule changes in real-time for a specific restaurant.
Usage: python watch_schedule.py [restaurant_id]
Defaults to restaurant_id=1 if not specified.
"""

from dotenv import load_dotenv
import os
import sys
import time
from pathlib import Path

# Load .env FIRST, before any other imports that need it
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Now import modules that need environment variables
from app.database.mongo import get_mongo_db

def clear_screen():
    """Clear terminal screen (works on Windows/Mac/Linux)"""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_time(hour: int, minute: int = 0) -> str:
    """Format hour and minute as HH:MM"""
    return f"{hour:02d}:{minute:02d}"

def main():
    # Get restaurant_id from command line or use default
    restaurant_id = 1
    if len(sys.argv) > 1:
        try:
            restaurant_id = int(sys.argv[1])
        except ValueError:
            print(f"Error: Invalid restaurant_id '{sys.argv[1]}'. Using default 1.")
    
    # Connect to database
    try:
        db = get_mongo_db()
    except RuntimeError as e:
        print(f"Error: {e}")
        print(f"\nLooking for .env at: {env_path}")
        print("Make sure you have a .env file in the backend directory with:")
        print("MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/SD_IoT")
        print("MONGODB_DB_NAME=SD_IoT")
        sys.exit(1)
    
    # Find the device for this restaurant
    device = db.Devices.find_one({"legacyId": restaurant_id})
    
    if not device:
        print(f"No device found with legacyId {restaurant_id}")
        print("\nAvailable restaurants:")
        for dev in db.Devices.find().sort("legacyId", 1):
            name = dev.get("restaurant", "Unknown")
            lid = dev.get("legacyId", "N/A")
            print(f"  {lid}: {name}")
        sys.exit(1)
    
    device_id = device["_id"]
    restaurant_name = device.get("restaurant", "Unknown")
    
    print(f"Watching schedule for: {restaurant_name} (legacyId: {restaurant_id})")
    print("Press Ctrl+C to stop monitoring\n")
    
    last_rule_count = 0
    last_update = None
    
    try:
        while True:
            clear_screen()
            
            # Get fresh device data
            current_device = db.Devices.find_one({"_id": device_id})
            
            # Get schedule from Schedules collection
            schedule = db.Schedules.find_one({"deviceId": device_id})
            
            # Header
            print("=" * 60)
            print(f"SCHEDULE MONITOR - {restaurant_name}")
            print("=" * 60)
            
            # Simple schedule from Devices
            print("\nSIMPLE SCHEDULE (Devices collection):")
            if current_device:
                on_time = current_device.get("scheduleOn", "not set")
                off_time = current_device.get("scheduleOff", "not set")
                print(f"  ON:  {on_time}")
                print(f"  OFF: {off_time}")
                print(f"  Last updated: {current_device.get('lastUpdated', 'unknown')}")
            else:
                print("  Device not found")
            
            # Full schedule from Schedules
            print("\nFULL SCHEDULE (Schedules collection):")
            if schedule:
                rules = schedule.get("rules", [])
                rule_count = len(rules)
                
                # Detect changes
                if rule_count != last_rule_count:
                    print("  SCHEDULE UPDATED!")
                    last_rule_count = rule_count
                
                if rule_count == 0:
                    print("  No rules defined")
                else:
                    print(f"  Total rules: {rule_count}")
                    print()
                    for i, rule in enumerate(rules, 1):
                        days = ", ".join(rule.get("days", []))
                        start = format_time(
                            rule.get("startHour", 0),
                            rule.get("startMinute", 0)
                        )
                        end = format_time(
                            rule.get("endHour", 0),
                            rule.get("endMinute", 0)
                        )
                        enabled = rule.get("enabled", True)
                        status = "enabled" if enabled else "disabled"
                        
                        print(f"  Rule {i}: {status}")
                        print(f"    Days: {days}")
                        print(f"    Time: {start} -> {end}")
                        print()
                
                # Show last update time
                updated = schedule.get("updatedAt")
                if updated and updated != last_update:
                    print(f"  Updated: {updated}")
                    last_update = updated
            else:
                print("  No schedule found in Schedules collection")
                last_rule_count = 0
            
            # Footer with timestamp
            print("\n" + "=" * 60)
            print(f"Refreshing every 2 seconds | {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped")
        sys.exit(0)

if __name__ == "__main__":
    main()
