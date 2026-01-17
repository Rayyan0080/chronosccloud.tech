"""
Quick Sentry Test Script

This script tests if Sentry is properly configured by sending a test error.
Run this to verify your Sentry setup is working.
"""

import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.shared.sentry import init_sentry, capture_startup, capture_exception

def main():
    """Test Sentry integration."""
    print("=" * 60)
    print("SENTRY TEST SCRIPT")
    print("=" * 60)
    
    # Initialize Sentry
    print("\n1. Initializing Sentry...")
    init_sentry("sentry_test", "NORMAL")
    capture_startup("sentry_test", {"test": True})
    
    print("\n2. Sending test event to Sentry...")
    print("   (This will cause a ZeroDivisionError intentionally)")
    
    # Wait a moment for startup event to be sent
    import time
    time.sleep(2)
    
    # Intentionally cause an error to test Sentry
    try:
        print("\n3. Triggering test error...")
        division_by_zero = 1 / 0
    except ZeroDivisionError as e:
        print("   Error caught! Sending to Sentry...")
        capture_exception(e, {"test": True, "purpose": "verification"})
        print("   Error sent to Sentry!")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Go to https://sentry.io")
    print("2. Open your project")
    print("3. Check 'Issues' tab - you should see a ZeroDivisionError")
    print("4. Check 'Events' tab - you should see startup and exception events")
    print("\nWait 10-30 seconds for events to appear in Sentry dashboard.")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(0)

