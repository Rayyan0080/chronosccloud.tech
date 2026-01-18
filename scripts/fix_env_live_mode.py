#!/usr/bin/env python3
"""
Fix .env file to set LIVE_MODE=on and clean up duplicate LIVE_ADAPTERS entries.
"""

import os
import re
from pathlib import Path

# Get project root
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

if not env_file.exists():
    print(f"❌ .env file not found at {env_file}")
    exit(1)

# Read current .env file
with open(env_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Process lines
new_lines = []
live_mode_set = False
live_adapters_set = False

for line in lines:
    stripped = line.strip()
    
    # Handle LIVE_MODE
    if re.match(r'^LIVE_MODE=', stripped):
        if not live_mode_set:
            new_lines.append('LIVE_MODE=on\n')
            live_mode_set = True
        # Skip duplicate entries
    
    # Handle LIVE_ADAPTERS
    elif re.match(r'^LIVE_ADAPTERS=', stripped):
        if not live_adapters_set:
            # Use the most complete adapter list
            new_lines.append('LIVE_ADAPTERS=oc_transpo_gtfsrt,opensky_airspace,ottawa_traffic,ontario511\n')
            live_adapters_set = True
        # Skip duplicate entries
    
    # Keep all other lines
    else:
        new_lines.append(line)

# Add missing entries if they weren't found
if not live_mode_set:
    new_lines.append('LIVE_MODE=on\n')
    print("✅ Added LIVE_MODE=on")

if not live_adapters_set:
    new_lines.append('LIVE_ADAPTERS=oc_transpo_gtfsrt,opensky_airspace,ottawa_traffic,ontario511\n')
    print("✅ Added LIVE_ADAPTERS")

# Write back to file
with open(env_file, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("\n[OK] Updated .env file:")
print("  LIVE_MODE=on")
print("  LIVE_ADAPTERS=oc_transpo_gtfsrt,opensky_airspace,ottawa_traffic,ontario511")
print("\n[INFO] Note: Removed duplicate entries")

