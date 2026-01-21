# PowerShell script to start generating airspace test data
# This will make the Airspace Status gauge show congestion

Write-Host "Starting Airspace Test Data Generator..." -ForegroundColor Green
Write-Host ""
Write-Host "This will generate aircraft position events to populate the airspace gauge." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host ""

cd $PSScriptRoot\..
python scripts/generate_airspace_test_data.py --count 18 --interval 10 --continuous

