"""
Solana Audit Logger Service

Subscribes to audit.decision events and logs them to Solana blockchain
using the Memo program for immutable audit trail.
"""

import asyncio
import hashlib
import json
import logging
import os
import sys
from typing import Dict, Any

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared.messaging import get_broker, subscribe
from agents.shared.sentry import init_sentry, capture_startup, capture_received_event, capture_exception

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Event topic
AUDIT_DECISION_TOPIC = "chronos.events.audit.decision"


class SolanaAuditLogger:
    """Logs audit decisions to Solana blockchain."""

    def __init__(self):
        """Initialize the Solana audit logger."""
        self.solana_rpc_url = os.getenv("SOLANA_RPC_URL")
        self.solana_private_key = os.getenv("SOLANA_PRIVATE_KEY")
        self.solana_enabled = bool(self.solana_rpc_url and self.solana_private_key)

        if self.solana_enabled:
            logger.info("Solana integration enabled")
            logger.info(f"RPC URL: {self.solana_rpc_url[:50]}..." if len(self.solana_rpc_url) > 50 else f"RPC URL: {self.solana_rpc_url}")
        else:
            logger.info("Solana integration disabled (missing SOLANA_RPC_URL or SOLANA_PRIVATE_KEY)")
            logger.info("Running in demo mode - will print hash instead of writing to blockchain")

    def _compute_hash(self, payload: Dict[str, Any]) -> str:
        """
        Compute SHA-256 hash of the decision payload.

        Args:
            payload: Audit decision event payload

        Returns:
            Hexadecimal hash string
        """
        # Serialize payload to JSON (sorted keys for consistency)
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))

        # Compute SHA-256 hash
        hash_obj = hashlib.sha256(payload_json.encode("utf-8"))
        hash_hex = hash_obj.hexdigest()

        return hash_hex

    async def _log_to_solana(self, hash_hex: str, payload: Dict[str, Any]) -> None:
        """
        Log hash to Solana blockchain using Memo program.

        Args:
            hash_hex: SHA-256 hash of the decision payload
            payload: Original audit decision payload
        """
        if not self.solana_enabled:
            # Demo mode: just print
            logger.info("=" * 60)
            logger.info("[SOLANA] would log hash: " + hash_hex)
            logger.info(f"[SOLANA] Decision ID: {payload.get('details', {}).get('decision_id', 'unknown')}")
            logger.info(f"[SOLANA] Action: {payload.get('details', {}).get('action', 'unknown')}")
            logger.info("=" * 60)
            return

        try:
            # Import Solana libraries
            try:
                from solana.rpc.api import Client
                from solana.keypair import Keypair
                from solana.transaction import Transaction
                from solders.memo import MemoParams
                from base58 import b58decode
            except ImportError:
                logger.warning(
                    "Solana libraries not installed. Install with: pip install solana solders base58"
                )
                logger.info("Falling back to demo mode")
                self.solana_enabled = False
                await self._log_to_solana(hash_hex, payload)  # Retry in demo mode
                return

            # Create Solana client
            client = Client(self.solana_rpc_url)

            # Parse private key
            try:
                # Private key can be base58 string or hex
                if len(self.solana_private_key) == 64:  # Hex format
                    private_key_bytes = bytes.fromhex(self.solana_private_key)
                else:  # Base58 format
                    private_key_bytes = b58decode(self.solana_private_key)

                # Create keypair
                keypair = Keypair.from_secret_key(private_key_bytes)
            except Exception as e:
                logger.error(f"Failed to parse private key: {e}")
                logger.info("Falling back to demo mode")
                self.solana_enabled = False
                await self._log_to_solana(hash_hex, payload)  # Retry in demo mode
                return

            # Create memo instruction
            # Memo program: MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr
            memo_text = f"CHRONOS_AUDIT:{hash_hex}"
            memo_instruction = MemoParams(memo=memo_text.encode("utf-8"))

            # Build transaction
            transaction = Transaction()
            transaction.add(memo_instruction)

            # Get recent blockhash
            try:
                blockhash_resp = client.get_latest_blockhash()
                if hasattr(blockhash_resp, "value"):
                    blockhash = blockhash_resp.value.blockhash
                else:
                    blockhash = blockhash_resp.blockhash

                transaction.recent_blockhash = blockhash
            except Exception as e:
                logger.error(f"Failed to get recent blockhash: {e}")
                raise

            # Sign transaction
            transaction.sign(keypair)

            # Send transaction
            try:
                response = client.send_transaction(transaction, keypair)
                signature = response.value

                logger.info("=" * 60)
                logger.info("[SOLANA] Successfully logged to blockchain")
                logger.info(f"[SOLANA] Hash: {hash_hex}")
                logger.info(f"[SOLANA] Signature: {signature}")
                logger.info(f"[SOLANA] Decision ID: {payload.get('details', {}).get('decision_id', 'unknown')}")
                logger.info("=" * 60)

            except Exception as e:
                logger.error(f"Failed to send transaction to Solana: {e}")
                # Don't raise - allow service to continue
                logger.warning("Continuing in demo mode after transaction failure")
                self.solana_enabled = False
                await self._log_to_solana(hash_hex, payload)  # Retry in demo mode

        except Exception as e:
            logger.error(f"Error logging to Solana: {e}", exc_info=True)
            logger.warning("Transaction may have failed, but continuing...")

    async def _handle_audit_decision(self, topic: str, payload: Dict[str, Any]) -> None:
        """
        Handle audit.decision events and log to Solana.

        Args:
            topic: Event topic
            payload: Event payload
        """
        try:
            decision_id = payload.get("details", {}).get("decision_id", "unknown")
            action = payload.get("details", {}).get("action", "unknown")

            logger.info("=" * 60)
            logger.info("AUDIT DECISION RECEIVED")
            logger.info("=" * 60)
            logger.info(f"Decision ID: {decision_id}")
            logger.info(f"Action: {action}")
            logger.info(f"Decision Type: {payload.get('details', {}).get('decision_type', 'unknown')}")
            logger.info(f"Sector: {payload.get('sector_id', 'unknown')}")
            logger.info("=" * 60)

            # Compute hash of the decision payload
            hash_hex = self._compute_hash(payload)
            logger.info(f"Computed SHA-256 hash: {hash_hex}")

            # Log to Solana
            await self._log_to_solana(hash_hex, payload)

        except Exception as e:
            logger.error(f"Error handling audit decision: {e}", exc_info=True)

    async def run(self) -> None:
        """Run the Solana audit logger service."""
        logger.info("Starting Solana Audit Logger Service")
        logger.info("=" * 60)
        logger.info("Configuration:")
        logger.info(f"  Solana Enabled: {self.solana_enabled}")
        if self.solana_enabled:
            logger.info(f"  RPC URL: {self.solana_rpc_url[:50]}..." if len(self.solana_rpc_url) > 50 else f"  RPC URL: {self.solana_rpc_url}")
        else:
            logger.info("  Running in demo mode")
        logger.info(f"  Topic: {AUDIT_DECISION_TOPIC}")
        logger.info("=" * 60)

        try:
            # Connect to message broker
            logger.info("Connecting to message broker...")
            broker = await get_broker()
            logger.info("Connected to message broker")

            # Subscribe to audit.decision events
            await subscribe(AUDIT_DECISION_TOPIC, self._handle_audit_decision)
            logger.info(f"Subscribed to: {AUDIT_DECISION_TOPIC}")

            logger.info("=" * 60)
            logger.info("Solana Audit Logger is running. Waiting for audit decisions...")
            logger.info("=" * 60)

            # Keep running
            try:
                await asyncio.Event().wait()  # Wait indefinitely
            except asyncio.CancelledError:
                logger.info("Service cancelled")

            # Disconnect from broker
            await broker.disconnect()
            logger.info("Disconnected from message broker")

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            raise

        logger.info("Solana Audit Logger Service stopped")


async def main() -> None:
    """Main entry point for the Solana audit logger service."""
    logger_instance = SolanaAuditLogger()
    await logger_instance.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
        import sys

        sys.exit(0)

