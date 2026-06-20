from __future__ import annotations

import subprocess
import sys
import time

import httpx
import typer

from repomind.config.settings import RepoMindConfig, load_config, save_config
from repomind.llm.ollama import LLMClient as OllamaClient
from repomind.utils.display import (
    console,
    error,
    info,
    make_progress,
    make_table,
    panel,
    print_banner,
    section,
    spinner,
    success,
    warning,
)
from repomind.utils.system import SystemSpec, detect_system, recommend_model

_DOCKER_COMPOSE_CONTENT = """\
services:
  qdrant:
    image: qdrant/qdrant:v1.9.4
    container_name: repomind-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__LOG_LEVEL=WARN
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:6333/collections || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s

volumes:
  qdrant_data:
    name: repomind_qdrant_data
"""


def run_install() -> None:
    print_banner()

    config = load_config()
    if config.installed:
        warning("RepoMind is already installed.")
        if not typer.confirm("Reinstall / reconfigure?", default=False):
            success("Nothing changed.")
            raise typer.Exit(0)

    section("System Detection")

    with spinner("Analyzing your hardware..."):
        spec = detect_system()
        time.sleep(0.3)

    _show_system_table(spec)
    recommendation = recommend_model(spec)

    section("Model Selection")

    model_table = make_table(
        "Recommended Model",
        [("Field", "bold cyan"), ("Value", "white")],
    )
    model_table.add_row("Model", recommendation.model)
    model_table.add_row("Quality", recommendation.quality_label)
    model_table.add_row("Reason", recommendation.reason)
    model_table.add_row("Min RAM needed", f"{recommendation.min_ram_gb:.0f} GB")
    console.print(model_table)
    console.print()

    chosen_model = typer.prompt(
        "Confirm model (or type another)", default=recommendation.model
    ).strip()

    section("Permission & Consent")

    panel(
        f"RepoMind will:\n\n"
        f"  [primary]1.[/primary] Pull Ollama models:\n"
        f"      • [bold]{chosen_model}[/bold] (language model)\n"
        f"      • [bold]nomic-embed-text[/bold] (embedding model)\n\n"
        "  [primary]2.[/primary] Start Qdrant vector database"
        " via Docker [bold](port 6333)[/bold]\n\n"
        f"  [primary]3.[/primary] Store config at [bold]~/.repomind/config.json[/bold]\n\n"
        f"  [muted]No data leaves your machine. 100% local. Zero telemetry.[/muted]",
        title="  RepoMind Setup  ",
        style="primary",
    )
    console.print()

    if not typer.confirm("Proceed with installation?", default=True):
        warning("Installation cancelled.")
        raise typer.Exit(0)

    section("Checking Prerequisites")

    _check_ollama()
    _check_docker()

    section("Pulling Models")

    ollama = OllamaClient()
    _pull_model(ollama, "nomic-embed-text")
    _pull_model(ollama, chosen_model)

    section("Starting Qdrant")

    _start_qdrant()

    section("Health Checks")

    _run_health_checks(ollama)

    new_config = RepoMindConfig(
        model=chosen_model,
        embed_model="nomic-embed-text",
        installed=True,
    )
    save_config(new_config)

    section("Done")

    panel(
        "[success]✓  RepoMind is ready![/success]\n\n"
        "  Run [bold cyan]repomind[/bold cyan] to start chatting with your codebase.\n\n"
        f"  Model  :  [bold]{chosen_model}[/bold]\n"
        f"  Embed  :  [bold]nomic-embed-text[/bold]\n"
        f"  Qdrant :  [bold]localhost:6333[/bold]",
        title="  Installation Complete  ",
        style="success",
    )


def _show_system_table(spec: SystemSpec) -> None:
    table = make_table("Your Machine", [("Property", "bold cyan"), ("Value", "white")])
    table.add_row("OS", spec.os_name)
    table.add_row("CPU", spec.cpu_brand)
    table.add_row("CPU Cores", str(spec.cpu_count))
    table.add_row("RAM", f"{spec.ram_gb:.1f} GB")
    if spec.is_apple_silicon:
        table.add_row("Chip", "[success]Apple Silicon[/success] (unified memory)")
    if spec.gpu_name:
        table.add_row("GPU", spec.gpu_name)
        table.add_row("GPU VRAM", f"{spec.gpu_vram_gb:.1f} GB")
    console.print(table)
    console.print()


def _check_ollama() -> None:
    import shutil

    if not shutil.which("ollama"):
        error("Ollama is not installed.")
        console.print()
        console.print("  Install it from: [bold cyan]https://ollama.com/download[/bold cyan]")
        console.print("  Then run:        [bold]repomind install[/bold]")
        raise typer.Exit(1)

    ollama = OllamaClient()
    if not ollama.is_running():
        info("Ollama installed but not running — attempting to start...")
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(3)
        except OSError:
            pass

    if not ollama.is_running():
        error("Could not start Ollama. Please run [bold]ollama serve[/bold] in another terminal.")
        raise typer.Exit(1)

    success("Ollama is running")


def _check_docker() -> None:
    import shutil

    if not shutil.which("docker"):
        error("Docker is not installed.")
        console.print(
            "  Install Docker Desktop: [bold cyan]https://www.docker.com/get-started[/bold cyan]"
        )
        raise typer.Exit(1)

    result = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
    if result.returncode != 0:
        error("Docker is not running.")
        if sys.platform == "darwin":
            console.print("  Start it with: [bold]open -a Docker[/bold]")
        else:
            console.print("  Start it with: [bold]sudo systemctl start docker[/bold]")
        raise typer.Exit(1)

    success("Docker is running")


def _pull_model(ollama: OllamaClient, model: str) -> None:
    if ollama.has_model(model):
        success(f"[bold]{model}[/bold] already present — skipping download")
        return

    console.print(f"  Pulling [bold]{model}[/bold]...")
    progress = make_progress()
    task = progress.add_task(f"Downloading {model}", total=None)

    with progress:
        for event in ollama.pull_model(model):
            status = event.get("status", "")
            total = event.get("total")
            completed = event.get("completed")
            if isinstance(total, (int, float)) and isinstance(completed, (int, float)):
                progress.update(task, total=int(total), completed=int(completed))
            elif status:
                progress.update(task, description=f"{model}: {status[:60]}")
            if event.get("status") == "success":
                progress.update(task, completed=1, total=1)
                break

    success(f"[bold]{model}[/bold] is ready")


def _start_qdrant() -> None:
    from repomind.config.settings import REPOMIND_DIR

    compose_dir = REPOMIND_DIR / "docker"
    compose_dir.mkdir(parents=True, exist_ok=True)
    compose_file = compose_dir / "docker-compose.yml"
    compose_file.write_text(_DOCKER_COMPOSE_CONTENT, encoding="utf-8")

    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d", "--remove-orphans"],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode != 0:
        error(f"Failed to start Qdrant:\n{result.stderr.strip()}")
        raise typer.Exit(1)

    with spinner("Waiting for Qdrant to be ready..."):
        for _ in range(30):
            try:
                resp = httpx.get("http://localhost:6333/collections", timeout=2.0)
                if resp.status_code == 200:
                    break
            except (httpx.ConnectError, httpx.TimeoutException):
                time.sleep(1)
        else:
            error(
                "Qdrant did not become healthy in time."
                " Run: [bold]docker logs repomind-qdrant[/bold]"
            )
            raise typer.Exit(1)

    success("Qdrant vector database is running")


def _run_health_checks(ollama: OllamaClient) -> None:
    checks: list[tuple[str, object]] = [
        ("Ollama API", ollama.is_running),
        ("Qdrant API", _qdrant_healthy),
    ]
    all_ok = True
    for name, fn in checks:
        try:
            ok: bool = fn()  # type: ignore[operator]
        except Exception:
            ok = False
        if ok:
            success(f"{name}  ·  healthy")
        else:
            error(f"{name}  ·  NOT responding")
            all_ok = False

    if not all_ok:
        console.print()
        error(
            "One or more services failed health checks."
            " Fix the issue and run [bold]repomind install[/bold] again."
        )
        raise typer.Exit(1)


def _qdrant_healthy() -> bool:
    try:
        return httpx.get("http://localhost:6333/collections", timeout=5.0).status_code == 200
    except Exception:
        return False
