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

install_uv() {
    if command -v uv &>/dev/null; then
        success "uv $(uv --version | cut -d' ' -f2) already installed"
        return
    fi
    info "Installing uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    success "uv installed"
}

install_repomind() {
    info "Installing RepoMind..."
    uv tool install repomind
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
    install_uv
    install_repomind
    echo ""
    run_setup
}

main
