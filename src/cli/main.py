from __future__ import annotations

import typer

from zeocloud.cli.chat import run_chat
from zeocloud.cli.install import run_install, run_uninstall
from zeocloud.config.settings import load_config, save_config
from zeocloud.llm.ollama import LLMClient
from zeocloud.retriever.qdrant import VectorStore
from zeocloud.utils.display import console, make_table, panel, print_banner, section, success

app = typer.Typer(
    name="zeocloud",
    help="Ask your codebase anything — locally, privately, powerfully.",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=False,
    pretty_exceptions_enable=False,
)


@app.command("install", help="First-time setup: hardware detection, model pull, Qdrant start.")
def install_command() -> None:
    run_install()


@app.command("uninstall", help="Remove Zeocloud container, data volume, and config.")
def uninstall_command() -> None:
    run_uninstall()


@app.command("status", help="Check health of all Zeocloud services.")
def status_command() -> None:
    print_banner()
    config = load_config()
    section("Service Health")

    llm = LLMClient(host=config.ollama_host)
    store = VectorStore(host=config.qdrant_host, port=config.qdrant_port)

    checks: list[tuple[str, str, bool]] = [
        ("Ollama", config.ollama_host, llm.is_running()),
        ("Qdrant", f"{config.qdrant_host}:{config.qdrant_port}", store.is_healthy()),
    ]

    table = make_table(
        "Services", [("Service", "bold cyan"), ("Address", "white"), ("Status", "bold")]
    )
    for name, addr, ok in checks:
        status_cell = "[success]✓  Running[/success]" if ok else "[error]✗  Offline[/error]"
        table.add_row(name, addr, status_cell)
    console.print(table)

    section("Configuration")
    cfg_table = make_table("Config", [("Key", "bold cyan"), ("Value", "white")])
    cfg_table.add_row("Agent", config.agent_name or "[muted]not set[/muted]")
    cfg_table.add_row("Model", config.model)
    cfg_table.add_row("Embed model", config.embed_model)
    cfg_table.add_row("Projects", str(len(config.projects)))
    cfg_table.add_row("Config file", "~/.zeocloud/config.json")
    console.print(cfg_table)

    if config.projects:
        section("Indexed Projects")
        proj_table = make_table(
            "Projects",
            [("Name", "bold cyan"), ("Files", "green"), ("Chunks", "blue"), ("Indexed", "muted")],
        )
        for name, entry in config.projects.items():
            proj_table.add_row(
                name, str(entry.file_count), str(entry.chunk_count), entry.indexed_at[:10]
            )
        console.print(proj_table)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return

    print_banner()
    config = load_config()

    if not config.installed:
        panel(
            "Looks like this is your first time here. Welcome! 👋\n\n"
            "Run [bold cyan]zeocloud install[/bold cyan] to set up models and start Qdrant.\n"
            "[muted]Takes 5–10 minutes depending on your internet speed.[/muted]",
            title="  Welcome to Zeocloud  ",
            style="primary",
        )
        raise typer.Exit(0)

    if not config.agent_name:
        section("Name Your Agent")
        console.print(
            "  Give your AI assistant a name — something that feels right to you.\n"
            "  [muted]Examples: buddy, sage, aria, max, nova, cody, orion[/muted]\n"
        )
        name = typer.prompt("  Agent name", default="buddy").strip() or "buddy"
        config.agent_name = name
        save_config(config)
        console.print()
        success(f"[bold]{name}[/bold] is your Zeocloud agent. Let's go!")
        console.print()

    try:
        run_chat(config.agent_name)
    except (KeyboardInterrupt, EOFError):
        console.print()
        panel(
            f"[muted]See you later! {config.agent_name} will be here when you're back.[/muted]",
            style="success",
        )
