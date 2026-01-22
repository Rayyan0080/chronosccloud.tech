"""
Run all Chronos agents concurrently in a single process.

This script starts all agent services in the background and manages them together.
Press Ctrl+C to stop all agents.

Usage:
    python agents/run_all_agents.py [--required-only]
    
    --required-only: Only run required agents (state_logger, coordinator, autonomy_router)
"""

import argparse
import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Required agents (core functionality)
REQUIRED_AGENTS = [
    "state_logger.py",
    "coordinator_agent.py",
    "autonomy_router.py",
    "fix_proposal_agent.py",  # Auto-generate fixes for Critical events
    "actuator_agent.py",  # Fix deployment actuator
    "verification_agent.py",  # Fix verification
    "defense_detector.py",  # Defense threat detection
    "defense_assessor.py",  # Defense threat AI assessment
    "defense_actuator.py",  # Defense action deployment (sandbox only)
    "defense_verifier.py",  # Defense action verification and threat resolution
]

# Optional agents (domain-specific)
OPTIONAL_AGENTS = [
    "crisis_generator.py",           # Power domain
    "transit_ingestor.py",           # Transit domain
    "transit_risk_agent.py",         # Transit domain
    "trajectory_insight_agent.py",    # Airspace domain
    "airspace_deconflict_agent.py",   # Airspace domain
    "airspace_hotspot_agent.py",      # Airspace domain
    "flight_plan_ingestor.py",        # Airspace domain (API endpoint)
    "solana_audit_logger.py",        # Optional - blockchain audit
    "stress_monitor.py",             # Optional - stress monitoring
    "ottawa_overlay_generator.py",   # Optional - map overlays
]

# Track running processes
_processes: List[subprocess.Popen] = []


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    logger.info("\nReceived interrupt signal. Stopping all agents...")
    stop_all_agents()
    sys.exit(0)


def stop_all_agents():
    """Stop all running agent processes."""
    logger.info(f"Stopping {len(_processes)} agent(s)...")
    for process in _processes:
        try:
            if process.poll() is None:  # Process is still running
                # Try graceful termination first
                process.terminate()
                
                # Wait up to 3 seconds for graceful shutdown
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Agent {process.args[-1] if process.args else 'unknown'} didn't stop gracefully, forcing...")
                    process.kill()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass  # Process killed, continue
        except Exception as e:
            logger.error(f"Error stopping agent: {e}")
    _processes.clear()
    logger.info("All agents stopped.")


def start_agent(script_name: str, project_root: str) -> Optional[subprocess.Popen]:
    """Start a single agent script."""
    script_path = os.path.join(project_root, "agents", script_name)
    
    if not os.path.exists(script_path):
        logger.warning(f"Agent script not found: {script_path}")
        return None
    
    try:
        # Start the agent process
        # Use line buffering for better real-time output on Windows
        process = subprocess.Popen(
            [sys.executable, script_path],
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered for better real-time output
            universal_newlines=True,  # Ensure text mode works correctly
        )
        
        logger.info(f"✓ Started {script_name} (PID: {process.pid})")
        return process
    except Exception as e:
        logger.error(f"✗ Failed to start {script_name}: {e}")
        return None


def monitor_process(process: subprocess.Popen, script_name: str):
    """Monitor a process and log its output."""
    def log_output():
        try:
            # Read line by line, handling both Windows and Unix line endings
            while True:
                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        # Process has ended
                        break
                    time.sleep(0.1)  # Small sleep to avoid busy waiting
                    continue
                # Prefix with agent name for clarity
                logger.info(f"[{script_name}] {line.rstrip()}")
        except Exception as e:
            if process.poll() is None:  # Only log error if process is still running
                logger.error(f"Error reading output from {script_name}: {e}")
    
    import threading
    thread = threading.Thread(target=log_output, daemon=True)
    thread.start()
    return thread


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run all Chronos agents concurrently")
    parser.add_argument(
        "--required-only",
        action="store_true",
        help="Only run required agents (state_logger, coordinator, autonomy_router)"
    )
    parser.add_argument(
        "--skip",
        nargs="+",
        help="Skip specific agents (e.g., --skip crisis_generator.py transit_ingestor.py)"
    )
    
    args = parser.parse_args()
    
    # Get project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # Determine which agents to run
    agents_to_run = REQUIRED_AGENTS.copy()
    if not args.required_only:
        agents_to_run.extend(OPTIONAL_AGENTS)
    
    # Remove skipped agents
    if args.skip:
        agents_to_run = [a for a in agents_to_run if a not in args.skip]
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 80)
    logger.info("CHRONOS AGENT MANAGER")
    logger.info("=" * 80)
    logger.info(f"Project root: {project_root}")
    logger.info(f"Agents to start: {len(agents_to_run)}")
    logger.info(f"Required only: {args.required_only}")
    logger.info("=" * 80)
    logger.info("")
    
    # Start all agents
    logger.info("Starting agents...")
    for agent in agents_to_run:
        process = start_agent(agent, project_root)
        if process:
            _processes.append(process)
            # Start monitoring output
            monitor_process(process, agent)
            time.sleep(0.5)  # Small delay between starts
    
    if not _processes:
        logger.error("No agents started. Exiting.")
        return
    
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"✓ All {len(_processes)} agent(s) started successfully!")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Agents are running. Press Ctrl+C to stop all agents.")
    logger.info("")
    
    # Monitor processes and restart if they crash
    try:
        while True:
            time.sleep(1)
            # Check if any process has died
            dead_processes = []
            for i, process in enumerate(_processes):
                if process.poll() is not None:
                    # Process has exited
                    agent_name = agents_to_run[i] if i < len(agents_to_run) else "unknown"
                    exit_code = process.returncode
                    if exit_code != 0:
                        logger.warning(f"Agent {agent_name} exited with code {exit_code}")
                    else:
                        logger.info(f"Agent {agent_name} exited normally")
                    dead_processes.append(i)
            
            # Remove dead processes from list
            for i in reversed(dead_processes):
                _processes.pop(i)
            
            if dead_processes and not _processes:
                logger.error("All agents have stopped. Exiting.")
                break
    except KeyboardInterrupt:
        pass
    finally:
        stop_all_agents()


if __name__ == "__main__":
    main()

