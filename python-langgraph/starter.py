"""Optional CLI: start an in-process LangGraph conversation.

    uv run starter.py
"""

import asyncio

from graph.agent import SupportAgentSession
from models.types import ApprovalDecision


async def main() -> None:
    session = SupportAgentSession("sa@example.com")
    print("conversation: local-langgraph  (Ctrl-C to exit)")

    while True:
        text = input("you> ").strip()
        if not text:
            continue

        result = await session.send_message(text)
        print(f"agent> {result.reply}")

        while result.status == "awaiting_approval":
            pending = session.pending_approval()
            description = pending.description if pending else "purchase"
            answer = input(f"approve {description}? [Y/n] ").strip().lower()
            approved = answer not in {"n", "no", "reject"}
            if pending is None:
                raise RuntimeError("purchase approval disappeared")
            result = await session.approve_purchase(
                pending.approval_id, ApprovalDecision(approved=approved)
            )
            print(f"agent> {result.reply}")


if __name__ == "__main__":
    asyncio.run(main())
