"""Conversation identifiers shared by every API implementation."""

import re
import secrets


def new_conversation_id(customer_email: str) -> str:
    """Create an opaque, collision-resistant workflow/conversation ID.

    The human-readable slug makes the Temporal UI easier to scan; the 128-bit
    random suffix prevents collisions even when a customer starts many chats.
    """

    slug = re.sub(r"[^a-z0-9]+", "-", customer_email.lower()).strip("-")
    return f"support-{slug or 'customer'}-{secrets.token_urlsafe(16)}"
