from __future__ import annotations

import datetime
from pathlib import Path

import typer

from repomind.config.settings import ProjectEntry, RepoMindConfig, load_config, save_config
from repomind.embedder.embed import EmbedClient
from repomind.indexer.indexer import count_indexable_files, index_repository
from repomind.llm.ollama import LLMClient
from repomind.retriever.pipeline import RAGPipeline
from repomind.retriever.qdrant import VectorStore
from repomind.utils.display import (
    console,
    error,
    info,
    make_progress,
    make_table,
    panel,
    section,
    spinner,
    success,
    warning,
)
from repomind.utils.safety import validate_question, validate_repo_path
from repomind.utils.session import SessionData, save_session


def run_chat(agent_name: str) -> None:
    config = load_config()

    if not config.installed:
        error("RepoMind is not set up. Run [bold]repomind install[/bold] first.")
        raise typer.Exit(1)

    llm = LLMClient(host=config.ollama_host)
    embedder = EmbedClient(host=config.ollama_host, model=config.embed_model)
    store = VectorStore(host=config.qdrant_host, port=config.qdrant_port)

    if not llm.is_running():
        error("Ollama is not running. Start it with [bold]ollama serve[/bold].")
        raise typer.Exit(1)

    if not store.is_healthy():
        error("Qdrant is not running. Start it with [bold]repomind install[/bold].")
        raise typer.Exit(1)

    rag = RAGPipeline(llm, embedder, store, config.model, agent_name=agent_name)
    session = SessionData(agent_name=agent_name)

    while True:
        _show_menu(agent_name)
        choice = typer.prompt("Choice", default="1").strip()

        if choice == "1":
            _ask_flow(config, rag, agent_name, session)
        elif choice == "2":
            _index_flow(config, llm, embedder, store, session)
        elif choice == "3":
            _list_flow(config)
        elif choice == "4":
            _delete_flow(config, store)
        elif choice in ("5", "q", "quit", "exit"):
            saved_path = save_session(session)
            if saved_path:
                panel(
                    f"[success]Session saved →[/success] [muted]{saved_path}[/muted]\n\n"
                    f"[muted]Come back anytime — {agent_name} remembers your projects.[/muted]",
                    style="success",
                )
            else:
                panel("[muted]Goodbye! See you next time.[/muted]", style="success")
            break
        else:
            warning("Invalid choice — enter 1–5.")


def _show_menu(agent_name: str) -> None:
    console.print()
    console.print(f"[agent]  ⚡  {agent_name}[/agent] [muted]is listening[/muted]")
    console.print()
    console.print("  [primary]1.[/primary]  Ask a question about your code")
    console.print("  [primary]2.[/primary]  Index a new project")
    console.print("  [primary]3.[/primary]  View indexed projects")
    console.print("  [primary]4.[/primary]  Remove a project")
    console.print("  [primary]5.[/primary]  Exit")
    console.print()


def _ask_flow(
    config: RepoMindConfig,
    rag: RAGPipeline,
    agent_name: str,
    session: SessionData,
) -> None:
    if not config.projects:
        warning("No projects indexed yet — choose option 2 to add one.")
        return

    section("Select Project")
    projects = list(config.projects.items())
    for i, (name, entry) in enumerate(projects, start=1):
        chunks_label = f"({entry.chunk_count} chunks)"
        console.print(
            f"  [primary]{i}.[/primary]  [bold]{name}[/bold]  [muted]{chunks_label}[/muted]"
        )
    console.print()

    raw = typer.prompt("Project number", default="1").strip()
    try:
        idx = int(raw) - 1
        if not (0 <= idx < len(projects)):
            raise ValueError
    except ValueError:
        warning("Invalid selection.")
        return

    project_name, _ = projects[idx]
    console.print()
    console.print(
        f"  [muted]Project:[/muted] [bold]{project_name}[/bold]  "
        f"[muted]Model:[/muted] [bold]{config.model}[/bold]"
    )
    console.print("  [muted]Ask in English or Hindi. Empty line to go back.[/muted]")
    console.print()

    while True:
        try:
            question = typer.prompt(f"  You → {agent_name}").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not question:
            break

        ok, reason = validate_question(question)
        if not ok:
            warning(reason)
            continue

        console.print()
        console.print(f"  [agent]🤖 {agent_name}:[/agent]\n")

        collected: list[str] = []
        try:
            for token in rag.ask(project_name, question):
                console.print(token, end="", highlight=False)
                collected.append(token)
        except Exception as exc:
            console.print()
            error(f"Generation failed: {exc}")
            break

        console.print()
        session.log_question(project_name, question, "".join(collected))


def _index_flow(
    config: RepoMindConfig,
    llm: LLMClient,
    embedder: EmbedClient,
    store: VectorStore,
    session: SessionData,
) -> None:
    section("Index New Project")

    raw_path = typer.prompt("  Project path").strip()
    repo_path = Path(raw_path).expanduser().resolve()

    safety = validate_repo_path(repo_path)
    if not safety.is_safe:
        error(safety.block_reason)
        return

    if safety.warnings:
        for w in safety.warnings:
            warning(w)
        if safety.sensitive_files:
            console.print(f"  [muted]Files: {', '.join(safety.sensitive_files[:5])}[/muted]")
        if not typer.confirm("  Continue anyway?", default=False):
            return

    default_name = repo_path.name
    project_name = typer.prompt("  Project name", default=default_name).strip() or default_name

    if project_name in config.projects and not typer.confirm(
        f"  '{project_name}' is already indexed. Reindex?", default=False
    ):
        return

    with spinner("Scanning repository..."):
        file_count = count_indexable_files(repo_path)

    if file_count == 0:
        warning("No indexable source files found.")
        return

    info(f"Found [bold]{file_count}[/bold] indexable files")
    console.print()

    section("Indexing")
    progress = make_progress()

    with progress:
        chunk_task = progress.add_task("Chunking files...", total=None)
        all_chunks = index_repository(repo_path)
        progress.update(
            chunk_task, total=1, completed=1, description=f"Created {len(all_chunks)} chunks"
        )

        embed_task = progress.add_task("Embedding & storing...", total=len(all_chunks))
        store.ensure_collection(project_name, dim=embedder.dim)

        batch_size = 8
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i : i + batch_size]
            vectors = embedder.embed_batch([str(c["content"]) for c in batch])
            store.upsert(project_name, batch, vectors)
            progress.advance(embed_task, len(batch))

    entry = ProjectEntry(
        name=project_name,
        path=str(repo_path),
        indexed_at=datetime.datetime.now().isoformat(),
        file_count=file_count,
        chunk_count=len(all_chunks),
    )
    config.projects[project_name] = entry
    save_config(config)
    session.log_index(project_name, file_count, len(all_chunks))

    console.print()
    success(f"[bold]{project_name}[/bold] — {file_count} files, {len(all_chunks)} chunks indexed")


def _list_flow(config: RepoMindConfig) -> None:
    section("Indexed Projects")

    if not config.projects:
        info("No projects indexed yet. Use option 2 to add one.")
        return

    table = make_table(
        "Your Projects",
        [
            ("#", "muted"),
            ("Name", "bold cyan"),
            ("Path", "white"),
            ("Files", "green"),
            ("Chunks", "blue"),
            ("Last Indexed", "muted"),
        ],
    )
    for i, (name, entry) in enumerate(config.projects.items(), start=1):
        table.add_row(
            str(i),
            name,
            entry.path,
            str(entry.file_count),
            str(entry.chunk_count),
            entry.indexed_at[:10],
        )
    console.print(table)


def _delete_flow(config: RepoMindConfig, store: VectorStore) -> None:
    section("Remove Project")

    if not config.projects:
        info("No projects to remove.")
        return

    projects = list(config.projects.keys())
    for i, name in enumerate(projects, start=1):
        console.print(f"  [primary]{i}.[/primary]  {name}")
    console.print()

    raw = typer.prompt("  Project number to remove").strip()
    try:
        idx = int(raw) - 1
        if not (0 <= idx < len(projects)):
            raise ValueError
    except ValueError:
        warning("Invalid selection.")
        return

    project_name = projects[idx]
    if not typer.confirm(f"  Remove '{project_name}' and all its vectors?", default=False):
        return

    store.delete_project(project_name)
    del config.projects[project_name]
    save_config(config)
    success(f"[bold]{project_name}[/bold] removed.")
