"""
Bitquery GraphQL client for Tron (and other chains). Token from config.
"""

import json
import requests

from config import BITQUERY_OAUTH_TOKEN, BITQUERY_STREAMING_URL


def query_tron_transfers(wallet: str, limit: int = 10) -> dict:
    """Fetch recent transfers where the wallet is sender or receiver."""
    query = """
    query TronTransfers($wallet: String!, $limit: Int!) {
      Tron {
        Transfers(
          limit: { count: $limit }
          orderBy: { descending: Block_Time }
          where: {
            any: [
              { Transfer: { Sender: { is: $wallet } } }
              { Transfer: { Receiver: { is: $wallet } } }
            ]
          }
        ) {
          Transaction {
            Hash
            Time
          }
          Transfer {
            Amount
            AmountInUSD
            Sender
            Receiver
            Currency {
              Name
              SmartContract
            }
          }
        }
      }
    }
    """
    payload = json.dumps({
        "query": query,
        "variables": {"wallet": wallet, "limit": limit},
    })
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BITQUERY_OAUTH_TOKEN}",
    }
    if not BITQUERY_OAUTH_TOKEN:
        raise ValueError("Set BITQUERY_OAUTH_TOKEN in .env or environment")
    response = requests.post(
        BITQUERY_STREAMING_URL,
        headers=headers,
        data=payload,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()
