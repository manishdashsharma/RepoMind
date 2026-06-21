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

_DOCKER_COMPOSE_TEMPLATE = """\
services:
  qdrant:
    image: qdrant/qdrant:{qdrant_version}
    container_name: repomind-qdrant
    ports:
      - "{port}:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__LOG_LEVEL=WARN
    restart: unless-stopped
    networks:
      - repomind

networks:
  repomind:
    name: repomind

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

    raw = typer.prompt("Confirm model (or type another)", default=recommendation.model).strip()
    chosen_model = recommendation.model if raw.lower() in ("y", "yes", "") else raw

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

    qdrant_port = _start_qdrant()

    section("Health Checks")

    _run_health_checks(ollama, qdrant_port)

    new_config = RepoMindConfig(
        model=chosen_model,
        embed_model="nomic-embed-text",
        installed=True,
        qdrant_port=qdrant_port,
    )
    save_config(new_config)

    section("Done")

    panel(
        "[success]✓  RepoMind is ready![/success]\n\n"
        f"  Model  :  [bold]{chosen_model}[/bold]\n"
        f"  Embed  :  [bold]nomic-embed-text[/bold]\n"
        f"  Qdrant :  [bold]localhost:{qdrant_port}[/bold]\n\n"
        "  [bold]How to use:[/bold]\n\n"
        "    [bold cyan]repomind[/bold cyan]                 — start chatting\n"
        "    [bold cyan]repomind install[/bold cyan]         — reconfigure\n\n"
        "  [bold]Inside chat:[/bold]\n\n"
        "    [primary]1.[/primary] Index a project  →  give the full path to your repo\n"
        "    [primary]2.[/primary] Ask anything     →  in English or Hindi\n"
        "    [primary]3.[/primary] Switch projects  →  from the main menu\n\n"
        "  [muted]Everything runs locally. No data leaves your machine.[/muted]",
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


def _start_qdrant() -> int:
    from repomind.config.settings import REPOMIND_DIR

    for candidate in range(6333, 6343):
        try:
            resp = httpx.get(f"http://localhost:{candidate}/collections", timeout=1.0)
            if resp.status_code == 200:
                success(f"Qdrant already running on port {candidate}")
                return candidate
        except Exception:
            pass

    subprocess.run(
        ["docker", "rm", "-f", "repomind-qdrant"],
        capture_output=True,
    )

    port = _find_free_port(6333)
    if port != 6333:
        info(f"Port 6333 is in use — using port {port} instead")

    compose_dir = REPOMIND_DIR / "docker"
    compose_dir.mkdir(parents=True, exist_ok=True)
    compose_file = compose_dir / "docker-compose.yml"
    compose_file.write_text(
        _DOCKER_COMPOSE_TEMPLATE.format(port=port, qdrant_version=_qdrant_server_version()),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        error(f"Failed to start Qdrant:\n{result.stderr.strip()}")
        raise typer.Exit(1)

    with spinner("Waiting for Qdrant to be ready..."):
        for _ in range(45):
            try:
                resp = httpx.get(f"http://localhost:{port}/collections", timeout=2.0)
                if resp.status_code == 200:
                    break
            except Exception:
                time.sleep(1)
        else:
            error(
                "Qdrant did not become healthy in time."
                " Run: [bold]docker logs repomind-qdrant[/bold]"
            )
            raise typer.Exit(1)

    success(f"Qdrant vector database is running on port {port}")
    return port


def _find_free_port(start: int) -> int:
    import socket

    for port in range(start, start + 10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port
    return start + 10


def _qdrant_server_version() -> str:
    try:
        import importlib.metadata

        raw = importlib.metadata.version("qdrant-client")
        parts = raw.split(".")
        return f"v{parts[0]}.{parts[1]}.0"
    except Exception:
        return "v1.13.0"


def _run_health_checks(ollama: OllamaClient, qdrant_port: int = 6333) -> None:
    checks: list[tuple[str, object]] = [
        ("Ollama API", ollama.is_running),
        ("Qdrant API", lambda: _qdrant_healthy(qdrant_port)),
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


def _qdrant_healthy(port: int = 6333) -> bool:
    try:
        return httpx.get(f"http://localhost:{port}/collections", timeout=5.0).status_code == 200
    except Exception:
        return False


def run_uninstall() -> None:
    from repomind.config.settings import REPOMIND_DIR

    panel(
        "This will remove:\n\n"
        "  [primary]1.[/primary] Qdrant Docker container ([bold]repomind-qdrant[/bold])\n"
        "  [primary]2.[/primary] Qdrant data volume ([bold]repomind_qdrant_data[/bold])\n"
        "  [primary]3.[/primary] RepoMind config & sessions ([bold]~/.repomind/[/bold])\n\n"
        "  [muted]The repomind command stays — run repomind install to start fresh.[/muted]\n"
        "  [muted]Ollama models are NOT removed — they may be used by other apps.[/muted]",
        title="  Uninstall RepoMind  ",
        style="error",
    )
    console.print()

    if not typer.confirm("  Are you sure? This cannot be undone.", default=False):
        info("Uninstall cancelled.")
        raise typer.Exit(0)

    console.print()
    section("Removing Qdrant")

    result = subprocess.run(
        ["docker", "rm", "-f", "repomind-qdrant"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        success("Qdrant container removed")
    else:
        info("Qdrant container not found — skipping")

    result = subprocess.run(
        ["docker", "volume", "rm", "repomind_qdrant_data"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        success("Qdrant data volume removed")
    else:
        info("Qdrant volume not found — skipping")

    result = subprocess.run(
        ["docker", "network", "rm", "repomind"],
        capture_output=True,
        text=True,
    )

    section("Removing Config & Sessions")

    import shutil

    if REPOMIND_DIR.exists():
        shutil.rmtree(REPOMIND_DIR)
        success(f"Removed {REPOMIND_DIR}")
    else:
        info("Config directory not found — skipping")

    console.print()
    panel(
        "[success]RepoMind data has been cleared.[/success]\n\n"
        "  The [bold]repomind[/bold] command is still installed.\n"
        "  Run [bold cyan]repomind install[/bold cyan] to start fresh anytime.",
        title="  Done  ",
        style="success",
    )
