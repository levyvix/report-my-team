"""
Fetch and print the end-of-game stats block from the LCU.
Run while on the post-game screen.

Usage:
    uv run python scripts/lcu_info.py
"""

import asyncio
import json
import sys

sys.path.insert(0, "src")

from report_my_team.lcu import LcuClient


async def main() -> None:
    client = LcuClient()
    if not client.refresh_credentials():
        print("ERROR: League client not found or not running.")
        return

    print("Connected to LCU.\n")

    # ── End-of-game stats ──────────────────────────────────────────────────────
    status, body = await client.request("GET", "lol-end-of-game/v1/eog-stats-block")
    print(f"GET eog-stats-block  ->  {status}")
    if status == 200:
        data = json.loads(body)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(body.decode(errors="replace"))

    await client.aclose()


asyncio.run(main())
