import json
import unittest

from report_my_team.reporter import handle_end_game
from report_my_team.state import AppState


class FakeClient:
    def __init__(self):
        self.report_requests = []

    async def request(self, method, path, json_body=None):
        if method == "GET":
            return 200, json.dumps(
                {
                    "gameId": 7,
                    "localPlayer": {"summonerId": 1},
                    "teams": [
                        {
                            "teamId": 100,
                            "players": [
                                {"summonerId": 1, "puuid": "local"},
                                {"summonerId": 2, "puuid": "opponent"},
                                {"summonerId": 3, "puuid": "friend"},
                            ],
                        }
                    ],
                }
            ).encode()

        self.report_requests.append(json_body)
        if len(self.report_requests) == 1:
            return 500, b""
        return 204, b""


class HandleEndGameTests(unittest.IsolatedAsyncioTestCase):
    async def test_retries_failed_player_without_reporting_completed_players_again(self):
        client = FakeClient()
        state = AppState(friends_ids={3})

        await handle_end_game(client, state)
        self.assertEqual(state.last_game_id, 0)
        self.assertEqual(state.reporting_game_id, 7)
        self.assertEqual(state.completed_report_player_ids, {1, 3})

        await handle_end_game(client, state)
        self.assertEqual(state.last_game_id, 7)
        self.assertEqual(state.reporting_game_id, 0)

        await handle_end_game(client, state)
        self.assertEqual(len(client.report_requests), 2)
        self.assertEqual(
            [request["offenderSummonerId"] for request in client.report_requests],
            [2, 2],
        )


if __name__ == "__main__":
    unittest.main()
