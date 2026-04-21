import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from langchain_core.messages import HumanMessage

from tools.web_scraper import scrape_url
from tools.knowledge import store_knowledge, index_project, clear_knowledge, search_knowledge, list_knowledge_topics
from tools.web_search import search_web

console = Console()

def handle_exit(arg: str, state: dict) -> tuple[bool, dict]:
    console.print("\n👋 Goodbye!", style="bold cyan")
    sys.exit(0)

def handle_help(arg: str, state: dict) -> tuple[bool, dict]:
    from main import BANNER, print_help
    print_help()
    return True, state

def handle_clear(arg: str, state: dict) -> tuple[bool, dict]:
    state["messages"] = []
    console.print("🗑️  Conversation cleared.", style="yellow")
    return True, state

def handle_mode(arg: str, state: dict) -> tuple[bool, dict]:
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

def handle_code(arg: str, state: dict) -> tuple[bool, dict]:
    state["mode"] = "coder"
    console.print("Switched to 💻 Autonomous Coder mode.", style="bold green")
    if arg:
        state["messages"].append(HumanMessage(content=arg))
        return False, state
    return True, state

def handle_search(arg: str, state: dict) -> tuple[bool, dict]:
    if not arg:
        console.print("Usage: /search <query>", style="yellow")
        return True, state
    
    console.print(f"🔍 Searching the web for '{arg}'...", style="dim")
    result = search_web.invoke({"query": arg})
    console.print(Panel(result, title=f"Search Results: {arg}", border_style="blue"))
    return True, state

def handle_scrape(arg: str, state: dict) -> tuple[bool, dict]:
    if not arg:
        console.print("Usage: /scrape <url>", style="yellow")
        return True, state
    console.print(f"🕷️  Scraping {arg}...", style="dim")
    result = scrape_url.invoke({"url": arg})
    console.print(Panel(result[:2000], title="Scraped Content", border_style="green"))
    return True, state

def handle_learn(arg: str, state: dict) -> tuple[bool, dict]:
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

def handle_docs(arg: str, state: dict) -> tuple[bool, dict]:
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

def handle_index(arg: str, state: dict) -> tuple[bool, dict]:
    if not arg:
        console.print("Usage: /index <directory> [topic]", style="yellow")
        console.print("  Example: /index C:\\\\Projects\\\\my-app my-app", style="dim")
        return True, state
    index_parts = arg.split(maxsplit=1)
    directory = index_parts[0]
    topic = index_parts[1] if len(index_parts) > 1 else None

    console.print(f"\n📂 Indexing project: {directory}", style="bold cyan")
    console.print("   This may take a moment for large projects...\n", style="dim")

    # Use basic console print for status as it's hard to pass rich.status easily
    console.print("[bold cyan]Scanning and indexing files...[/]")
    result = index_project.invoke({
        "directory_path": directory,
        "topic": topic if topic else directory,
    })

    console.print(Panel(result, title="📂 Project Indexed", border_style="green"))
    console.print(
        "\n💡 [dim]Now you can ask the agent about your project code![/]"
    )
    return True, state

def handle_knowledge(arg: str, state: dict) -> tuple[bool, dict]:
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

    invoke_args = {"query": query}
    if topic:
        invoke_args["topic"] = topic

    result = search_knowledge.invoke(invoke_args)
    console.print(Panel(result, title="🧠 Knowledge Search", border_style="magenta"))
    return True, state

def handle_topics(arg: str, state: dict) -> tuple[bool, dict]:
    result = list_knowledge_topics.invoke({})
    console.print(Panel(result, title="📚 Knowledge Topics", border_style="blue"))
    return True, state

def handle_clear_kb(arg: str, state: dict) -> tuple[bool, dict]:
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

COMMAND_REGISTRY = {
    "/exit": handle_exit,
    "/help": handle_help,
    "/clear": handle_clear,
    "/mode": handle_mode,
    "/code": handle_code,
    "/search": handle_search,
    "/scrape": handle_scrape,
    "/learn": handle_learn,
    "/docs": handle_docs,
    "/index": handle_index,
    "/knowledge": handle_knowledge,
    "/topics": handle_topics,
    "/clear-kb": handle_clear_kb,
}
