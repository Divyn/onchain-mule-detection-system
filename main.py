"""
Run mule detection. Wallet from CLI or config.py.
  python main.py <wallet_address>   # use this wallet
  python main.py                    # use SEED_WALLET from config
"""

import json
import sys

from config import DEPTH, SEED_WALLET
from detection import analyze_wallet


def main() -> None:
    wallet = sys.argv[1].strip() if len(sys.argv) > 1 else SEED_WALLET
    print(f"Analyzing wallet {wallet} (depth={DEPTH})...")
    result = analyze_wallet(wallet)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
