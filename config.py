"""
Configuration for mule detection on-chain analysis. Edit values below.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# --- Wallet & traversal ---
# Default wallet when no CLI arg: python main.py <address> overrides this.
SEED_WALLET: str = "TFXttAWURRrXrd9JvFPVLEh1esJK8NHxn7"
# Depth of graph traversal from the seed wallet (1 = direct neighbors only).
DEPTH: int = 2
# Max number of neighbor wallets to query per depth (avoids explosion of API calls).
MAX_NEIGHBORS_PER_DEPTH: int = 2

# --- Bitquery ---
BITQUERY_STREAMING_URL: str = "https://streaming.bitquery.io/graphql"
# OAuth token: set in .env as BITQUERY_OAUTH_TOKEN=your_token
BITQUERY_OAUTH_TOKEN: str = os.environ.get("BITQUERY_OAUTH_TOKEN", "")

# --- Detection patterns ---
# Fan-Out: one wallet sends to many (large → split into many).
FAN_OUT_MIN_RECIPIENTS: int = 4
# Fan-In: many wallets send to one.
FAN_IN_MIN_SENDERS: int = 4
