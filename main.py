"""
AI Agent CLI — Rich terminal interface for interacting with the agent.
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from langchain_core.messages import HumanMessage

from agent.graph import build_agent_graph
from cli.commands import COMMAND_REGISTRY

console = Console()

# CLI banner
BANNER = """
╔══════════════════════════════════════════════════════════╗
║            🤖  LOCAL AI AGENT  (LM Studio)               ║
║                                                          ║
║  Capabilities:                                           ║
║  🔍 Web Search    🕷️ Web Scraping    🧠 RAG Knowledge   ║
║  📁 File Tools    💻 Code Runner     📂 Project Index   ║
║                                                          ║
║  Commands:                                               ║
║  /search <query>     — Force a web search                ║
║  /scrape <url>       — Scrape a web page                 ║
║  /learn <url> [topic]— Scrape + store in knowledge       ║
║  /index <dir> [topic]— Index entire project into RAG     ║
║  /docs <url> [topic] — Learn docs from a URL             ║
║  /knowledge <query>  — Search stored knowledge           ║
║  /topics             — List all indexed topics           ║
║  /clear-kb [topic]   — Clear knowledge (all or by topic) ║
║  /mode <mode>        — Switch mode (general|web_dev|coder)║
║  /code [prompt]      — Switch to coder mode & set prompt ║
║  /clear              — Clear conversation history        ║
║  /help               — Show this help                    ║
║  /exit               — Quit the agent                    ║
╚══════════════════════════════════════════════════════════╝
"""


def print_help():
    """Print the help banner."""
    console.print(Panel(BANNER.strip(), border_style="cyan", title="Help"))


def handle_slash_command(command: str, state: dict) -> tuple[bool, dict]:
    """
    Handle slash commands. Returns (handled, updated_state).
    If handled is True, the command was processed and shouldn't be sent to the agent.
    """
    parts = command.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    handler = COMMAND_REGISTRY.get(cmd)
    if handler:
        return handler(arg, state)

    return False, state


def run_agent_turn(graph, state: dict) -> dict:
    """Run one full agent turn (may involve multiple tool calls)."""
    try:
        # Prevent infinite loops if the local model continually fails to correctly resolve a tool call
        config = {"recursion_limit": 5}
        result = graph.invoke(state, config=config)
        return result
    except Exception as e:
        error_msg = str(e)
        if "recursion" in error_msg.lower() or "RecursionError" in error_msg:
            console.print(
                "\n⚠️ [bold yellow]Agent stopped to prevent an infinite loop.[/]\n"
                "The model you are using might be struggling to use the tools correctly or complete the task. "
                "Try using a model with better function-calling support (like Qwen 2.5 Coder) or rephrase your request.",
                style="yellow",
            )
        elif "Connection" in error_msg or "refused" in error_msg:
            console.print(
                "\n❌ [bold red]Cannot connect to LM Studio![/]\n"
                "Make sure LM Studio is running with a model loaded.\n"
                "Expected server at: http://localhost:1234/v1\n",
                style="red",
            )
        else:
            console.print(f"\n❌ Agent error: {error_msg}", style="red")
        return state


def main():
    """Main CLI loop."""
    console.print(BANNER, style="cyan")

    # Check LM Studio connection
    console.print("⏳ Connecting to LM Studio...", style="dim")
    try:
        from agent.graph import create_llm
        llm = create_llm()
        llm.invoke("Hello")
        console.print("✅ Connected to LM Studio!\n", style="bold green")
    except Exception as e:
        console.print(
            f"\n⚠️  [bold yellow]Warning:[/] Could not connect to LM Studio.\n"
            f"   Error: {e}\n"
            f"   Make sure LM Studio is running at http://localhost:1234\n"
            f"   The agent will still start, but may fail on queries.\n",
            style="yellow",
        )

    # Build the agent
    console.print("🔧 Building agent graph...", style="dim")
    graph = build_agent_graph()
    console.print("✅ Agent ready!\n", style="bold green")

    # Initialize state
    state = {
        "messages": [],
        "mode": "general",
    }

    # Main loop
    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/]")

            if not user_input.strip():
                continue

            # Handle slash commands
            if user_input.startswith("/"):
                handled, state = handle_slash_command(user_input, state)
                if handled:
                    continue

            # Add user message if not already added by a slash command
            if not state["messages"] or not isinstance(state["messages"][-1], HumanMessage):
                state["messages"].append(HumanMessage(content=user_input))

            # Show thinking indicator
            with console.status("[bold cyan]Thinking...", spinner="dots"):
                state = run_agent_turn(graph, state)

            # Display the agent's response
            if state["messages"]:
                last_msg = state["messages"][-1]
                if hasattr(last_msg, "content") and last_msg.content:
                    response_content = last_msg.content
                    console.print()
                    console.print(
                        Panel(
                            Markdown(response_content),
                            title="🤖 Agent",
                            border_style="green",
                            padding=(1, 2),
                        )
                    )

                    # Show mode indicator
                    mode_label = "General"
                    if state.get("mode") == "web_dev":
                        mode_label = "Web Dev"
                    elif state.get("mode") == "coder":
                        mode_label = "Coder"
                        
                    console.print(
                        f"  [dim]Mode: {mode_label} | "
                        f"Messages: {len(state['messages'])}[/]"
                    )

        except KeyboardInterrupt:
            console.print("\n\n👋 Goodbye!", style="bold cyan")
            sys.exit(0)
        except EOFError:
            console.print("\n\n👋 Goodbye!", style="bold cyan")
            sys.exit(0)


if __name__ == "__main__":
    main()
