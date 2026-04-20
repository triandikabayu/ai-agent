"""
Agent Graph — LangGraph agent with tool-calling loop.
Connects to LM Studio via OpenAI-compatible API.
"""

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.prompts import get_system_prompt
from config.settings import LM_STUDIO_BASE_URL, LM_STUDIO_MODEL, LM_STUDIO_TEMPERATURE

# Import all tools
from tools.web_search import search_web, search_news
from tools.web_scraper import scrape_url
from tools.knowledge import (
    store_knowledge, search_knowledge, list_knowledge_topics,
    index_project, clear_knowledge,
)
from tools.file_tools import read_file, write_file, list_directory, create_file, edit_file, append_to_file
from tools.code_runner import run_command, get_current_datetime

# All available tools
ALL_TOOLS = [
    search_web,
    search_news,
    scrape_url,
    store_knowledge,
    index_project,
    search_knowledge,
    list_knowledge_topics,
    clear_knowledge,
    read_file,
    write_file,
    create_file,
    edit_file,
    append_to_file,
    list_directory,
    run_command,
    get_current_datetime,
]


def create_llm() -> ChatOpenAI:
    """Create the LM Studio-backed LLM instance."""
    return ChatOpenAI(
        base_url=LM_STUDIO_BASE_URL,
        api_key="lm-studio",
        model=LM_STUDIO_MODEL,
        temperature=LM_STUDIO_TEMPERATURE,
    )

# 🚀 PERFORMANCE OPTIMIZATION: Cache LLM and Tool schemas globally
# This prevents rebuilding and re-parsing 15 tool JSON schemas on every agent reasoning loop.
GLOBAL_LLM = create_llm()
GLOBAL_LLM_WITH_TOOLS = GLOBAL_LLM.bind_tools(ALL_TOOLS)


def agent_node(state: AgentState) -> dict:
    """The main agent reasoning node — calls LM Studio with tools bound."""
    from langchain_core.messages import SystemMessage, trim_messages

    # Build system message based on current mode
    mode = state.get("mode", "general")
    system_prompt = get_system_prompt(mode)

    messages = state["messages"]

    # 🚀 PERFORMANCE OPTIMIZATION: Context Memory Protection
    # Trim the conversation to the most recent 30 messages to avoid crashing the local LM Studio
    # context window limits when scraping massive web pages or indexing large repositories.
    # It safely guarantees the conversation starts on a human or AI block.
    trimmed_messages = trim_messages(
        messages,
        max_tokens=30,
        token_counter=len,
        strategy="last",
        start_on="human", 
        include_system=False,
        allow_partial=False
    )

    full_messages = [SystemMessage(content=system_prompt)] + trimmed_messages

    # Use the cached global LLM instead of rebuilding it
    response = GLOBAL_LLM_WITH_TOOLS.invoke(full_messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """Decide whether to call tools or end the turn."""
    last_message = state["messages"][-1]

    # If the LLM made tool calls, route to the tools node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    # Otherwise, we're done
    return END


def build_agent_graph() -> StateGraph:
    """Build and compile the LangGraph agent."""
    # Create the tool node
    tool_node = ToolNode(ALL_TOOLS)

    # Build the graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    # Set entry point
    graph.set_entry_point("agent")

    # Add conditional edge from agent
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})

    # After tools execute, go back to agent for next reasoning step
    graph.add_edge("tools", "agent")

    # Compile
    return graph.compile()
