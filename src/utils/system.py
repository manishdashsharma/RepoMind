from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass

import psutil


@dataclass(frozen=True)
class SystemSpec:
    ram_gb: float
    cpu_count: int
    cpu_brand: str
    is_apple_silicon: bool
    gpu_name: str | None
    gpu_vram_gb: float | None
    os_name: str


@dataclass(frozen=True)
class ModelRecommendation:
    model: str
    embed_model: str
    reason: str
    quality_label: str
    min_ram_gb: float


def detect_system() -> SystemSpec:
    ram_gb = psutil.virtual_memory().total / (1024**3)
    cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count() or 1
    gpu_name, gpu_vram_gb = _detect_nvidia_gpu()
    return SystemSpec(
        ram_gb=round(ram_gb, 1),
        cpu_count=cpu_count,
        cpu_brand=_get_cpu_brand(),
        is_apple_silicon=_is_apple_silicon(),
        gpu_name=gpu_name,
        gpu_vram_gb=gpu_vram_gb,
        os_name=platform.system(),
    )


def recommend_model(spec: SystemSpec) -> ModelRecommendation:
    if spec.gpu_vram_gb and spec.gpu_vram_gb >= 24:
        return ModelRecommendation(
            model="llama3.3:70b",
            embed_model="nomic-embed-text",
            reason=f"NVIDIA GPU with {spec.gpu_vram_gb:.0f} GB VRAM — max quality unlocked",
            quality_label="★★★★★  Best",
            min_ram_gb=8,
        )
    if spec.gpu_vram_gb and spec.gpu_vram_gb >= 8:
        return ModelRecommendation(
            model="llama3.1:8b",
            embed_model="nomic-embed-text",
            reason=f"NVIDIA GPU with {spec.gpu_vram_gb:.0f} GB VRAM — GPU-accelerated inference",
            quality_label="★★★★☆  Great",
            min_ram_gb=8,
        )
    if spec.is_apple_silicon and spec.ram_gb >= 32:
        return ModelRecommendation(
            model="llama3.3:70b",
            embed_model="nomic-embed-text",
            reason="Apple Silicon + 32 GB unified memory — run the big model locally",
            quality_label="★★★★★  Best",
            min_ram_gb=40,
        )
    if spec.is_apple_silicon and spec.ram_gb >= 16:
        return ModelRecommendation(
            model="llama3.1:8b",
            embed_model="nomic-embed-text",
            reason="Apple Silicon + 16 GB — excellent local inference with Metal",
            quality_label="★★★★☆  Great",
            min_ram_gb=10,
        )
    if spec.ram_gb >= 16:
        return ModelRecommendation(
            model="llama3.1:8b",
            embed_model="nomic-embed-text",
            reason="16 GB RAM — solid 8B model, good Hindi + code reasoning",
            quality_label="★★★★☆  Great",
            min_ram_gb=10,
        )
    if spec.ram_gb >= 8:
        return ModelRecommendation(
            model="llama3.2:3b",
            embed_model="nomic-embed-text",
            reason="8 GB RAM — fast and capable 3B model",
            quality_label="★★★☆☆  Good",
            min_ram_gb=4,
        )
    return ModelRecommendation(
        model="phi3.5:3.8b",
        embed_model="nomic-embed-text",
        reason="Limited RAM — phi3.5 is lightweight and surprisingly capable",
        quality_label="★★☆☆☆  Lite",
        min_ram_gb=3,
    )


def _get_cpu_brand() -> str:
    system = platform.system()
    if system == "Darwin":
        for sysctl_key in ("machdep.cpu.brand_string", "hw.model"):
            try:
                result = subprocess.run(
                    ["sysctl", "-n", sysctl_key],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                brand = result.stdout.strip()
                if brand:
                    return brand
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
        return "Apple"
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if "model name" in line:
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "Unknown CPU"


def _is_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def _detect_nvidia_gpu() -> tuple[str | None, float | None]:
    if not shutil.which("nvidia-smi"):
        return None, None
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None, None
        line = result.stdout.strip().split("\n")[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            return parts[0], round(float(parts[1]) / 1024, 1)
    except (subprocess.SubprocessError, ValueError, IndexError):
        pass
    return None, None
