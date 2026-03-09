"""
Mule detection patterns: Fan-Out (Large → Split Into Many) and Fan-In.
Uses config.DEPTH for graph traversal from the seed wallet.
"""

from collections import defaultdict
from typing import Any

from config import (
    DEPTH,
    FAN_IN_MIN_SENDERS,
    FAN_OUT_MIN_RECIPIENTS,
    MAX_NEIGHBORS_PER_DEPTH,
)
from bitquery_client import query_tron_transfers


def _transfers_from_response(data: dict) -> list[dict]:
    """Extract transfer list from Bitquery Tron response."""
    try:
        return (
            data.get("data", {})
            .get("Tron", {})
            .get("Transfers", [])
            or []
        )
    except (AttributeError, TypeError):
        return []


def _aggregate_by_sender(transfers: list[dict]) -> dict[str, list[dict]]:
    """Group transfers by sender address."""
    by_sender: dict[str, list[dict]] = defaultdict(list)
    for t in transfers:
        sender = (t.get("Transfer") or {}).get("Sender") or ""
        if sender:
            by_sender[sender].append(t)
    return dict(by_sender)


def _aggregate_by_receiver(transfers: list[dict]) -> dict[str, list[dict]]:
    """Group transfers by receiver address."""
    by_receiver: dict[str, list[dict]] = defaultdict(list)
    for t in transfers:
        receiver = (t.get("Transfer") or {}).get("Receiver") or ""
        if receiver:
            by_receiver[receiver].append(t)
    return dict(by_receiver)


def _amounts_from_transfer(t: dict) -> dict[str, Any]:
    """Extract amount info from a transfer item."""
    tr = t.get("Transfer") or {}
    currency = (tr.get("Currency") or {}).get("Name") or ""
    amount = tr.get("Amount")
    amount_usd = tr.get("AmountInUSD")
    if amount is not None and not isinstance(amount, (int, float)):
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            amount = None
    if amount_usd is not None and not isinstance(amount_usd, (int, float)):
        try:
            amount_usd = float(amount_usd)
        except (TypeError, ValueError):
            amount_usd = None
    return {"amount": amount, "amount_usd": amount_usd, "currency": currency}


def detect_fan_out(transfers: list[dict]) -> list[dict]:
    """
    Fan-Out: one wallet sends to many (large → split into many).
    Returns list of { sender, recipient_count, recipients, total_amount, total_amount_usd, amounts }.
    """
    by_sender = _aggregate_by_sender(transfers)
    results = []
    for sender, list_t in by_sender.items():
        recipients = set(
            (t.get("Transfer") or {}).get("Receiver")
            for t in list_t
            if (t.get("Transfer") or {}).get("Receiver")
        )
        if len(recipients) >= FAN_OUT_MIN_RECIPIENTS:
            total_amount = 0.0
            total_usd = 0.0
            amounts = []
            for t in list_t:
                tr = t.get("Transfer") or {}
                info = _amounts_from_transfer(t)
                receiver = tr.get("Receiver")
                if receiver:
                    amounts.append({
                        "receiver": receiver,
                        "amount": info["amount"],
                        "amount_usd": info["amount_usd"],
                        "currency": info["currency"],
                    })
                    if info["amount"] is not None:
                        total_amount += info["amount"]
                    if info["amount_usd"] is not None:
                        total_usd += info["amount_usd"]
            results.append({
                "sender": sender,
                "recipient_count": len(recipients),
                "recipients": list(recipients),
                "total_amount": total_amount,
                "total_amount_usd": total_usd,
                "amounts": amounts,
            })
    return results


def detect_fan_in(transfers: list[dict]) -> list[dict]:
    """
    Fan-In: many wallets send to one.
    Returns list of { receiver, sender_count, senders, total_amount, total_amount_usd, amounts }.
    """
    by_receiver = _aggregate_by_receiver(transfers)
    results = []
    for receiver, list_t in by_receiver.items():
        senders = set(
            (t.get("Transfer") or {}).get("Sender")
            for t in list_t
            if (t.get("Transfer") or {}).get("Sender")
        )
        if len(senders) >= FAN_IN_MIN_SENDERS:
            total_amount = 0.0
            total_usd = 0.0
            amounts = []
            for t in list_t:
                tr = t.get("Transfer") or {}
                info = _amounts_from_transfer(t)
                sender_addr = tr.get("Sender")
                if sender_addr:
                    amounts.append({
                        "sender": sender_addr,
                        "amount": info["amount"],
                        "amount_usd": info["amount_usd"],
                        "currency": info["currency"],
                    })
                    if info["amount"] is not None:
                        total_amount += info["amount"]
                    if info["amount_usd"] is not None:
                        total_usd += info["amount_usd"]
            results.append({
                "receiver": receiver,
                "sender_count": len(senders),
                "senders": list(senders),
                "total_amount": total_amount,
                "total_amount_usd": total_usd,
                "amounts": amounts,
            })
    return results


def get_neighbor_wallets(transfers: list[dict], seed: str) -> set[str]:
    """From transfers involving seed, return set of neighbor addresses."""
    neighbors = set()
    for t in transfers:
        tr = t.get("Transfer") or {}
        s, r = tr.get("Sender"), tr.get("Receiver")
        if s == seed and r:
            neighbors.add(r)
        elif r == seed and s:
            neighbors.add(s)
    return neighbors


def analyze_wallet(
    wallet: str,
    limit_per_query: int = 100,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Analyze a seed wallet up to DEPTH hops. Runs Fan-Out and Fan-In
    detection on transfers fetched for the wallet and (up to DEPTH) its neighbors.
    """
    all_transfers: list[dict] = []
    visited: set[str] = {wallet}
    frontier: set[str] = {wallet}
    depth_remaining = DEPTH

    while depth_remaining >= 0 and frontier:
        next_frontier: set[str] = set()
        addrs = list(frontier)
        for i, addr in enumerate(addrs):
            if verbose:
                print(f"  depth={DEPTH - depth_remaining} querying {i + 1}/{len(addrs)}: {addr[:12]}...", flush=True)
            try:
                data = query_tron_transfers(addr, limit=limit_per_query)
                transfers = _transfers_from_response(data)
                all_transfers.extend(transfers)
                if depth_remaining > 0:
                    next_frontier |= get_neighbor_wallets(transfers, addr)
            except Exception as e:
                if verbose:
                    print(f"    skip ({e})", flush=True)
                continue
        next_frontier -= visited
        visited |= next_frontier
        # Cap neighbors to avoid hundreds of API calls
        frontier = set(list(next_frontier)[: MAX_NEIGHBORS_PER_DEPTH])
        depth_remaining -= 1

    fan_out = detect_fan_out(all_transfers)
    fan_in = detect_fan_in(all_transfers)

    return {
        "wallet": wallet,
        "depth": DEPTH,
        "total_transfers_analyzed": len(all_transfers),
        "fan_out": fan_out,
        "fan_in": fan_in,
    }
