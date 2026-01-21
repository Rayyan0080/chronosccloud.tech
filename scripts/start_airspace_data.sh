#!/bin/bash
# Shell script to start generating airspace test data
# This will make the Airspace Status gauge show congestion

echo "Starting Airspace Test Data Generator..."
echo ""
echo "This will generate aircraft position events to populate the airspace gauge."
echo "Press Ctrl+C to stop."
echo ""

cd "$(dirname "$0")/.."
python scripts/generate_airspace_test_data.py --count 18 --interval 10 --continuous

