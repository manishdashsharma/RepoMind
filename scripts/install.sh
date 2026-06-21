#!/usr/bin/env bash
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${CYAN}  →${NC}  $1"; }
success() { echo -e "${GREEN}  ✓${NC}  $1"; }
error()   { echo -e "${RED}  ✗${NC}  $1" >&2; exit 1; }
warning() { echo -e "${YELLOW}  ⚠${NC}  $1"; }

echo -e "${CYAN}"
cat << 'EOF'
 ██████╗ ███████╗██████╗  ██████╗ ███╗   ███╗██╗███╗   ██╗██████╗
 ██╔══██╗██╔════╝██╔══██╗██╔═══██╗████╗ ████║██║████╗  ██║██╔══██╗
 ██████╔╝█████╗  ██████╔╝██║   ██║██╔████╔██║██║██╔██╗ ██║██║  ██║
 ██╔══██╗██╔══╝  ██╔═══╝ ██║   ██║██║╚██╔╝██║██║██║╚██╗██║██║  ██║
 ██║  ██║███████╗██║     ╚██████╔╝██║ ╚═╝ ██║██║██║ ╚████║██████╔╝
 ╚═╝  ╚═╝╚══════╝╚═╝      ╚═════╝ ╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝
EOF
echo -e "${NC}"
echo "  Ask your codebase anything — locally, privately, powerfully."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

check_python() {
    if ! command -v python3 &>/dev/null; then
        error "Python 3.11+ is required. Install from https://python.org"
    fi
    py_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor}")')
    if [ "$py_version" -lt "311" ]; then
        error "Python 3.11+ required. Found $(python3 --version)"
    fi
    success "Python $(python3 --version | cut -d' ' -f2)"
}

ensure_docker() {
    if ! command -v docker &>/dev/null; then
        error "Docker is not installed. Install Docker Desktop from https://www.docker.com/get-started"
    fi

    if docker info &>/dev/null 2>&1; then
        success "Docker is running"
        return
    fi

    info "Docker is installed but not running — starting Docker..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open -a Docker
    elif command -v systemctl &>/dev/null; then
        sudo systemctl start docker
    else
        error "Could not start Docker automatically. Please start it manually and re-run this script."
    fi

    local waited=0
    while ! docker info &>/dev/null 2>&1; do
        if [ "$waited" -ge 60 ]; then
            error "Docker did not start within 60 seconds. Please start Docker manually and re-run."
        fi
        printf "\r${CYAN}  →${NC}  Waiting for Docker to start... ${waited}s"
        sleep 2
        waited=$((waited + 2))
    done
    echo ""
    success "Docker is running"
}

install_repomind() {
    info "Installing RepoMind..."
    if command -v uv &>/dev/null; then
        uv tool install "$REPO_DIR" --reinstall --quiet
        export PATH="$HOME/.local/bin:$PATH"
    elif command -v pipx &>/dev/null; then
        pipx install "$REPO_DIR" --force --quiet
    else
        warning "Neither uv nor pipx found. Trying pip..."
        /usr/bin/python3 -m pip install --user "$REPO_DIR" --quiet
        export PATH="$HOME/.local/bin:$PATH"
    fi
    success "RepoMind installed"
}

run_setup() {
    info "Starting RepoMind setup wizard..."
    echo ""
    repomind install
}

main() {
    echo "  Checking requirements..."
    echo ""
    check_python
    ensure_docker
    install_repomind
    echo ""
    run_setup
}

main
