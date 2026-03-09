# mule-detection-onchain

On-chain money mule detection for the **TRON network**, powered by [Bitquery](https://bitquery.io). Detects **Fan-Out** and **Fan-In** transfer patterns across a multi-hop wallet graph.

---

## How It Works

Starting from a seed wallet, the tool performs a breadth-first traversal of the TRON transfer graph up to a configurable depth. At each hop it fetches recent transfers via Bitquery's GraphQL streaming API and applies two structural detectors:

- **Fan-Out** — one wallet sends to many distinct receivers (large → split into many), the classic disbursement mule pattern.
- **Fan-In** — many distinct senders send to one wallet (aggregator pattern), used to pool funds before layering.

Any wallet appearing in both results at the same address is a **gather-scatter hub** — the canonical USDT mule pattern on TRON.

```
Seed Wallet
    │
    ├── depth 0: fetch transfers, run detection
    │       └── collect neighbor wallets
    │
    ├── depth 1: fetch transfers for each neighbor, run detection
    │       └── collect next-hop neighbors
    │
    └── depth N: ... (controlled by DEPTH in config.py)
```

---

## Project Structure

```
mule-detection-onchain/
├── main.py              # CLI entrypoint
├── detection.py         # Fan-Out, Fan-In, BFS traversal logic
├── bitquery_client.py   # Bitquery GraphQL client (TRON transfers)
├── config.py            # All configuration (wallet, depth, thresholds, API)
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
└── .env                 # Your secrets (not committed)
```

---

## Quickstart

### 1. Clone and install

```bash
git clone https://github.com/Divyn/onchain-mule-detection-system
cd onchain-mule-detection-system
pip install -r requirements.txt
```

### 2. Set your Bitquery token

```bash
cp .env.example .env
# Edit .env and set BITQUERY_OAUTH_TOKEN=your_token
```

Get a free OAuth token at [bitquery.io](https://bitquery.io).

### 3. Run

```bash
# Analyze the wallet in config.py
python main.py

# Analyze a specific wallet
python main.py TFXttAWURRrXrd9JvFPVLEh1esJK8NHxn7
```

Output is JSON printed to stdout:

```json
{
  "wallet": "TFXttAWURRrXrd9JvFPVLEh1esJK8NHxn7",
  "depth": 2,
  "total_transfers_analyzed": 312,
  "fan_out": [
    {
      "sender": "TAbc...",
      "recipient_count": 7,
      "recipients": ["TXxx...", "TYyy...", "..."],
      "total_amount": 45000.0,
      "total_amount_usd": 45003.21,
      "amounts": [...]
    }
  ],
  "fan_in": [...]
}
```

---

## Configuration

All settings live in `config.py`:

| Parameter | Default | Description |
|---|---|---|
| `SEED_WALLET` | `TFXtt...` | Default wallet to analyze (overridden by CLI arg) |
| `DEPTH` | `2` | BFS hops from seed (0 = seed only, 1 = direct neighbors, …) |
| `MAX_NEIGHBORS_PER_DEPTH` | `2` | Max neighbor wallets queried per depth level (caps API usage) |
| `FAN_OUT_MIN_RECIPIENTS` | `4` | Minimum distinct receivers to flag a Fan-Out address |
| `FAN_IN_MIN_SENDERS` | `4` | Minimum distinct senders to flag a Fan-In address |
| `BITQUERY_STREAMING_URL` | streaming endpoint | Bitquery GraphQL URL |
| `BITQUERY_OAUTH_TOKEN` | from `.env` | Bearer token — set via `BITQUERY_OAUTH_TOKEN` env var |

---

## Detection Patterns

### Fan-Out (Disbursement)

```
         ┌── Wallet B
Wallet A ─┼── Wallet C
         ├── Wallet D
         └── Wallet E  (≥ FAN_OUT_MIN_RECIPIENTS recipients)
```

Wallet A is flagged if it sends to 4 or more distinct addresses. Common in the *disbursement* stage of laundering where a loaded mule splits funds.

### Fan-In (Aggregation)

```
Wallet B ─┐
Wallet C ─┼── Wallet A
Wallet D ─┤             (≥ FAN_IN_MIN_SENDERS senders)
Wallet E ─┘
```

Wallet A is flagged if it receives from 4 or more distinct senders. Common in the *placement* or *aggregation* stage.

### Gather-Scatter (Hub) — manual identification

An address appearing in **both** `fan_in` and `fan_out` results is a gather-scatter hub: it aggregates from many sources and then disburses to many destinations — the strongest single-address mule signal.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BITQUERY_OAUTH_TOKEN` | Yes | Bitquery OAuth2 bearer token |

---

## Dependencies

- [`requests`](https://pypi.org/project/requests/) ≥ 2.28.0 — HTTP client for Bitquery API calls
- [`python-dotenv`](https://pypi.org/project/python-dotenv/) ≥ 1.0.0 — loads `.env` into environment

---

## Limitations & Roadmap

- **Rule-based only** — no ML scoring; all addresses meeting the threshold are treated equally
- **Narrow BFS** — `MAX_NEIGHBORS_PER_DEPTH=2` prevents API explosion but may miss peripheral mule rings
- **No temporal windowing** — fan-in/fan-out is measured across all-time transfers, not per time bucket
- **TRON only** — `bitquery_client.py` queries the Tron schema; other chains require a new client

Planned improvements based on recent research (see `mule_detection_research.md`):
- Gather-scatter detection (intersect fan-in + fan-out on the same address)
- Time-windowed detection using `Transaction.Time`
- Stack / peeling-chain pattern (linear A→B→C forwarding)
- Risk scoring (passthrough ratio, temporal compression, degree centrality)
- Subgraph export (NetworkX edge list) for visualization and GNN classification

---

## License

MIT
