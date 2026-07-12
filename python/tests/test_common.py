import unittest
from unittest.mock import patch

from support_agent_common import database
from support_agent_common.conversations import new_conversation_id


class ConversationIdTests(unittest.TestCase):
    def test_ids_are_opaque_and_collision_resistant(self) -> None:
        ids = {new_conversation_id("sa@temporal.io") for _ in range(100)}

        self.assertEqual(len(ids), 100)
        self.assertTrue(all(value.startswith("support-sa-temporal-io-") for value in ids))
        prefix = "support-sa-temporal-io-"
        self.assertTrue(all(len(value.removeprefix(prefix)) >= 22 for value in ids))


class CatalogQueryTests(unittest.TestCase):
    def test_genre_search_joins_genre_and_parameterizes_input(self) -> None:
        calls: list[tuple[str, dict[str, object]]] = []

        class Cursor:
            def fetchall(self):
                return [{"track": "Rock Song"}]

        class Connection:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def execute(self, sql, params):
                calls.append((sql, params))
                return Cursor()

        with patch("support_agent_common.database._connect", return_value=Connection()):
            result = database.search_music_by_genre("postgresql://demo", "Rock")

        self.assertEqual(result, [{"track": "Rock Song"}])
        self.assertIn("JOIN genre g", calls[0][0])
        self.assertIn("g.name ILIKE %(q)s", calls[0][0])
        self.assertEqual(calls[0][1], {"q": "%Rock%"})
