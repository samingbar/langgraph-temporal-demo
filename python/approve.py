"""Optional CLI: approve or reject a pending purchase atomically.

    uv run approve.py <conversation-id>            # approve
    uv run approve.py <conversation-id> --reject   # reject
"""

import asyncio
import sys

import config
from models.types import ApprovalDecision
from workflows.agent import SupportAgentWorkflow


async def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: uv run approve.py <conversation-id> [--reject]")
    conversation_id = sys.argv[1]
    approved = "--reject" not in sys.argv

    client = await config.temporal_client()
    handle = client.get_workflow_handle_for(SupportAgentWorkflow.run, conversation_id)
    pending = await handle.query(SupportAgentWorkflow.pending_approval)
    if pending is None:
        sys.exit("no purchase approval is pending")
    await handle.execute_update(
        SupportAgentWorkflow.approve_purchase,
        pending.approval_id,
        ApprovalDecision(approved=approved),
    )
    print(f"{'approved' if approved else 'rejected'} → recorded for {conversation_id}")


if __name__ == "__main__":
    asyncio.run(main())
