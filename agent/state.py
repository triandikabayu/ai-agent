"""
Agent State — defines the state schema for the LangGraph agent.
"""

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State that flows through the agent graph."""

    # Conversation messages (auto-accumulated by LangGraph)
    messages: Annotated[list, add_messages]

    # Current operating mode
    mode: str  # "general" or "web_dev"
