"""Replay-safe state models shared by LangGraph nodes and Temporal history."""

from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]


class ToolCall(BaseModel):
    """One model-requested tool invocation with normalized JSON arguments."""
    id: str
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    """Transcript item, including assistant calls and correlated tool output."""
    role: Role
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)  # on role="assistant"
    tool_call_id: str | None = None  # on role="tool"


class LLMRequest(BaseModel):
    """Complete conversation history supplied to a planning Activity."""
    messages: list[ChatMessage]


class LLMResponse(BaseModel):
    """Normalized assistant response returned by either model provider."""
    message: ChatMessage  # role="assistant"; tool_calls empty → final answer


class ToolRequest(BaseModel):
    """Tool call plus server-trusted customer identity from workflow state."""
    call: ToolCall
    customer_email: str


class PendingPurchase(BaseModel):
    """Purchase details exposed while the workflow waits for a human."""
    track_ids: list[int]
    description: str | None = None


class ApprovalDecision(BaseModel):
    """Human decision recorded atomically in durable workflow state."""
    approved: bool
    reason: str | None = None


class TurnResult(BaseModel):
    """Turn outcome: a final reply or a pause at an approval boundary."""
    status: Literal["reply", "awaiting_approval"]
    reply: str
