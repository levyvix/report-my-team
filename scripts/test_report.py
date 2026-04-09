"""
Send a single end-of-game report and print the raw HTTP response.
Run while on the post-game screen.

Usage:
    uv run python scripts/test_report.py <gameId> <summonerId> <puuid> [category]

    category defaults to NEGATIVE_ATTITUDE

Example:
    uv run python scripts/test_report.py 7123456789 12345 abc-def-... LEAVING_AFK
"""

import asyncio
import json
import sys

sys.path.insert(0, "src")

from report_my_team.lcu import LcuClient


async def main(game_id: int, summoner_id: int, puuid: str, category: str) -> None:
    client = LcuClient()
    if not client.refresh_credentials():
        print("ERROR: League client not found or not running.")
        return

    print(f"Reporting  gameId={game_id}  summonerId={summoner_id}  puuid={puuid}  category={category}\n")

    payload = {
        "gameId": game_id,
        "categories": [category],
        "offenderSummonerId": summoner_id,
        "offenderPuuid": puuid,
    }
    status, body = await client.request(
        "POST",
        "lol-player-report-sender/v1/end-of-game-reports",
        json_body=payload,
    )

    print(f"Status: {status}")
    try:
        print(json.dumps(json.loads(body), indent=2, ensure_ascii=False))
    except Exception:
        print(body.decode(errors="replace"))

    await client.aclose()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    game_id = int(sys.argv[1])
    summoner_id = int(sys.argv[2])
    puuid = sys.argv[3]
    category = sys.argv[4] if len(sys.argv) > 4 else "NEGATIVE_ATTITUDE"

    asyncio.run(main(game_id, summoner_id, puuid, category))
