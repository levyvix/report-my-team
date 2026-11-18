import asyncio
import logging

from report_my_team.lcu import LcuClient
from report_my_team.models import (
    REPORT_CATEGORIES,
    EogStatsBlock,
    Player,
    ReportPayload,
)
from report_my_team.state import AppState

logger = logging.getLogger(__name__)


async def handle_end_game(client: LcuClient, state: AppState) -> None:
    status, body = await client.request("GET", "lol-end-of-game/v1/eog-stats-block")
    if status != 200:
        logger.debug("eog-stats-block returned %d, skipping.", status)
        return

    stats = EogStatsBlock.model_validate_json(body)

    if stats.gameId == state.last_game_id:
        return

    if state.reporting_game_id != stats.gameId:
        state.reporting_game_id = stats.gameId
        state.completed_report_player_ids.clear()

    logger.info("End of game reached. Fetching stats...")

    if state.current_player_id == 0:
        state.current_player_id = stats.localPlayer.summonerId
        logger.info("Identified as summoner ID %d.", state.current_player_id)

    player_count = sum(len(team.players) for team in stats.teams)
    logger.info("Game %d ended. Processing %d players...", stats.gameId, player_count)

    players_to_report = []
    for team in stats.teams:
        for player in team.players:
            if player.botPlayer:
                logger.info(
                    "Skipping %s (%s) — bot player",
                    player.riotIdGameName or player.championName,
                    player.championName,
                )
            else:
                players_to_report.append(player)

    results = await asyncio.gather(
        *(_report_player(client, state, stats.gameId, player) for player in players_to_report),
        return_exceptions=True,
    )
    incomplete = False
    for player, result in zip(players_to_report, results):
        if isinstance(result, BaseException):
            logger.error(
                "Reporting %s (%s, ID %d) raised an error: %s",
                player.riotIdGameName,
                player.championName or "Unknown",
                player.summonerId,
                result,
            )
            incomplete = True
        elif not result:
            incomplete = True

    if incomplete:
        logger.warning("Reporting is incomplete; failed players will be retried.")
    else:
        state.last_game_id = stats.gameId
        state.reporting_game_id = 0
        state.completed_report_player_ids.clear()
    logger.info("------------------")


async def _report_player(client: LcuClient, state: AppState, game_id: int, player: Player) -> bool:
    name = player.riotIdGameName
    champ = player.championName or "Unknown"

    if player.summonerId in state.completed_report_player_ids:
        return True

    if player.summonerId == state.current_player_id:
        logger.info("Skipping %s (%s) — current account", name, champ)
        state.completed_report_player_ids.add(player.summonerId)
        return True

    if player.summonerId in state.friends_ids:
        logger.info("Skipping %s (%s) — friend detected (ID %d)", name, champ, player.summonerId)
        state.completed_report_player_ids.add(player.summonerId)
        return True

    logger.info("Reporting %s (%s, ID %d)...", name, champ, player.summonerId)
    status, _ = await client.request(
        "POST",
        "lol-player-report-sender/v1/end-of-game-reports",
        json_body=ReportPayload(
            gameId=game_id,
            categories=REPORT_CATEGORIES,
            offenderSummonerId=player.summonerId,
            offenderPuuid=player.puuid,
        ).model_dump(),
    )
    if status == 204:
        logger.info("%s (%s) reported successfully", name, champ)
        state.completed_report_player_ids.add(player.summonerId)
        return True
    else:
        logger.warning("Failed to report %s (%s) — HTTP %d", name, champ, status)
        return False
