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
from tools.web_scraper import scrape_url
from tools.knowledge import store_knowledge, index_project, clear_knowledge

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

    if cmd == "/exit":
        console.print("\n👋 Goodbye!", style="bold cyan")
        sys.exit(0)

    elif cmd == "/help":
        print_help()
        return True, state

    elif cmd == "/clear":
        state["messages"] = []
        console.print("🗑️  Conversation cleared.", style="yellow")
        return True, state

    elif cmd == "/mode":
        if arg in ("general", "web_dev", "coder"):
            state["mode"] = arg
            mode_name = "General" if arg == "general" else ("🌐 Web Development" if arg == "web_dev" else "💻 Autonomous Coder")
            console.print(f"Switched to {mode_name} mode.", style="bold green")
        else:
            console.print(
                "Available modes: [cyan]general[/], [cyan]web_dev[/], [cyan]coder[/]",
                style="yellow",
            )
        return True, state

    elif cmd == "/code":
        state["mode"] = "coder"
        console.print("Switched to 💻 Autonomous Coder mode.", style="bold green")
        if arg:
            # We want to process this prompt using the agent, so we add it to the message state
            # but we return handled=False so the outer loop continues running the agent
            state["messages"].append(HumanMessage(content=arg))
            return False, state
        return True, state

    elif cmd == "/search":
        if not arg:
            console.print("Usage: /search <query>", style="yellow")
            return True, state
        
        console.print(f"🔍 Searching the web for '{arg}'...", style="dim")
        from tools.web_search import search_web
        result = search_web.invoke({"query": arg})
        console.print(Panel(result, title=f"Search Results: {arg}", border_style="blue"))
        return True, state

    elif cmd == "/scrape":
        if not arg:
            console.print("Usage: /scrape <url>", style="yellow")
            return True, state
        console.print(f"🕷️  Scraping {arg}...", style="dim")
        result = scrape_url.invoke({"url": arg})
        console.print(Panel(result[:2000], title="Scraped Content", border_style="green"))
        return True, state

    elif cmd == "/learn":
        if not arg:
            console.print("Usage: /learn <url> [topic]", style="yellow")
            return True, state
        learn_parts = arg.split(maxsplit=1)
        url = learn_parts[0]
        topic = learn_parts[1] if len(learn_parts) > 1 else "general"

        console.print(f"🕷️  Scraping {url}...", style="dim")
        content = scrape_url.invoke({"url": url})

        console.print(f"🧠 Storing under topic '{topic}'...", style="dim")
        result = store_knowledge.invoke({
            "content": content,
            "source": url,
            "topic": topic,
        })
        console.print(result, style="green")
        return True, state

    elif cmd == "/docs":
        if not arg:
            console.print("Usage: /docs <url> [topic]", style="yellow")
            console.print("  Example: /docs https://react.dev/learn react", style="dim")
            return True, state
        doc_parts = arg.split(maxsplit=1)
        url = doc_parts[0]
        topic = doc_parts[1] if len(doc_parts) > 1 else "general"

        console.print(f"📖 Fetching documentation from {url}...", style="dim")
        content = scrape_url.invoke({"url": url})

        if content.startswith("Error"):
            console.print(content, style="red")
            return True, state

        console.print(f"🧠 Storing docs under topic '{topic}'...", style="dim")
        result = store_knowledge.invoke({
            "content": content,
            "source": url,
            "topic": topic,
        })
        console.print(result, style="green")
        console.print(
            f"\n💡 [dim]Tip: Feed more pages with /docs <url> {topic} to build deeper knowledge.[/]"
        )
        return True, state

    elif cmd == "/index":
        if not arg:
            console.print("Usage: /index <directory> [topic]", style="yellow")
            console.print("  Example: /index C:\\\\Projects\\\\my-app my-app", style="dim")
            return True, state
        index_parts = arg.split(maxsplit=1)
        directory = index_parts[0]
        topic = index_parts[1] if len(index_parts) > 1 else None

        console.print(f"\n📂 Indexing project: {directory}", style="bold cyan")
        console.print("   This may take a moment for large projects...\n", style="dim")

        with console.status("[bold cyan]Scanning and indexing files...", spinner="dots"):
            result = index_project.invoke({
                "directory_path": directory,
                "topic": topic if topic else directory,
            })

        console.print(Panel(result, title="📂 Project Indexed", border_style="green"))
        console.print(
            "\n💡 [dim]Now you can ask the agent about your project code![/]"
        )
        return True, state

    elif cmd == "/knowledge":
        if not arg:
            console.print("Usage: /knowledge <query> [--topic <topic>]", style="yellow")
            return True, state

        # Parse optional --topic flag
        topic = None
        query = arg
        if "--topic" in arg:
            parts = arg.split("--topic")
            query = parts[0].strip()
            topic = parts[1].strip() if len(parts) > 1 else None

        from tools.knowledge import search_knowledge as sk
        invoke_args = {"query": query}
        if topic:
            invoke_args["topic"] = topic

        result = sk.invoke(invoke_args)
        console.print(Panel(result, title="🧠 Knowledge Search", border_style="magenta"))
        return True, state

    elif cmd == "/topics":
        from tools.knowledge import list_knowledge_topics as lkt
        result = lkt.invoke({})
        console.print(Panel(result, title="📚 Knowledge Topics", border_style="blue"))
        return True, state

    elif cmd == "/clear-kb":
        if arg:
            console.print(f"🗑️  Clearing knowledge for topic '{arg}'...", style="dim")
            result = clear_knowledge.invoke({"topic": arg})
        else:
            # Confirm before clearing everything
            confirm = Prompt.ask(
                "⚠️  Clear ALL knowledge? This cannot be undone",
                choices=["yes", "no"],
                default="no",
            )
            if confirm != "yes":
                console.print("Cancelled.", style="dim")
                return True, state
            result = clear_knowledge.invoke({})

        console.print(result, style="yellow")
        return True, state

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
