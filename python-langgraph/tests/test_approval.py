import unittest

from graph.agent import StaleApprovalError, SupportAgentSession
from models.types import ApprovalDecision, PendingPurchase


class ApprovalTests(unittest.IsolatedAsyncioTestCase):
    async def test_stale_approval_is_rejected_without_mutating_state(self) -> None:
        session = SupportAgentSession("sa@temporal.io")
        pending = PendingPurchase(
            approval_id="approval-current", track_ids=[1], description="One track"
        )
        session._state = {**session._state, "pending_purchase": pending}

        with self.assertRaisesRegex(StaleApprovalError, "stale"):
            await session.approve_purchase("approval-old", ApprovalDecision(approved=True))

        self.assertEqual(session.pending_approval(), pending)
