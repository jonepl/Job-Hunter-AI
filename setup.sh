#!/bin/bash

# =============================================================================
# Job Hunter Agent — Environment Setup Script
# =============================================================================
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
# =============================================================================

set -e  # Exit immediately if any command fails

# -----------------------------------------------------------------------------
# Color output helpers
# -----------------------------------------------------------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

success() { echo -e "${GREEN}✅ $1${NC}"; }
warn()    { echo -e "${YELLOW}⚠️  $1${NC}"; }
error()   { echo -e "${RED}❌ $1${NC}"; exit 1; }
info()    { echo -e "▶  $1"; }

echo ""
echo "=============================================="
echo "  Job Hunter Agent — Environment Setup"
echo "=============================================="
echo ""

# =============================================================================
# STEP 1 — Verify Prerequisites
# =============================================================================
info "Step 1: Verifying prerequisites..."

# Python 3.10+
if ! command -v python3 &>/dev/null; then
    error "Python 3 not found. Install Python 3.10+ from https://python.org"
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    error "Python 3.10+ required. Found: $PYTHON_VERSION. Visit https://python.org"
fi
success "Python $PYTHON_VERSION found"

# Node.js 18+
if ! command -v node &>/dev/null; then
    error "Node.js not found. Install Node.js 18+ from https://nodejs.org"
fi

NODE_VERSION=$(node -e "console.log(process.versions.node.split('.')[0])")
if [ "$NODE_VERSION" -lt 18 ]; then
    error "Node.js 18+ required. Found: $NODE_VERSION. Visit https://nodejs.org"
fi
success "Node.js v$(node --version) found"

# Git
if ! command -v git &>/dev/null; then
    error "Git not found. Install Git from https://git-scm.com"
fi
success "Git $(git --version | awk '{print $3}') found"

# pip
if ! command -v pip3 &>/dev/null; then
    error "pip not found. Reinstall Python from https://python.org"
fi
success "pip found"

echo ""

# =============================================================================
# STEP 2 — Create Python Virtual Environment
# =============================================================================
info "Step 2: Creating Python virtual environment..."

if [ -d ".venv" ]; then
    warn ".venv already exists — skipping creation"
else
    python3 -m venv .venv
    success "Virtual environment created at .venv/"
fi

# Activate virtual environment
source .venv/bin/activate
success "Virtual environment activated"

echo ""

# =============================================================================
# STEP 3 — Create .env File
# =============================================================================
info "Step 3: Creating .env file..."

if [ -f ".env" ]; then
    warn ".env already exists — skipping (your keys are safe)"
elif [ -f ".env.example" ]; then
    cp .env.example .env
    success ".env created from .env.example"
    warn "ACTION REQUIRED: Replace placeholder values in .env with your real API keys"
else
    error ".env.example not found — cannot create .env template"
fi

echo ""

# =============================================================================
# STEP 4 — Install Python Dependencies
# =============================================================================
info "Step 4: Installing Python dependencies..."

.venv/bin/pip install -r requirements.txt --quiet
success "Python dependencies installed"

echo ""

# =============================================================================
# STEP 5 — Install Playwright Browser Binaries
# =============================================================================
info "Step 5: Installing Playwright browser binaries..."

.venv/bin/playwright install
success "Playwright browser binaries installed"

echo ""

# =============================================================================
# STEP 6 — Final Validation
# =============================================================================
info "Step 6: Running final validation..."

# Check .env is git-ignored
if git check-ignore -q .env 2>/dev/null; then
    success ".env is properly git-ignored"
else
    warn ".env may not be git-ignored — verify your .gitignore contains '.env'"
fi

# Check virtual environment is active
if [[ "$VIRTUAL_ENV" != "" ]]; then
    success "Virtual environment is active: $VIRTUAL_ENV"
else
    warn "Virtual environment may not be active — run: source .venv/bin/activate"
fi

# Check key packages installed
python3 -c "import openai, dotenv, playwright, bs4, pypdf2, pytest" 2>/dev/null \
    && success "All core packages verified" \
    || warn "Some packages may not have installed correctly — run: pip list"

echo ""
echo "=============================================="
echo -e "${GREEN}  ✅ Environment setup complete!${NC}"
echo "=============================================="
echo ""
echo "Next steps:"
echo "  1. Replace placeholder API keys in .env"
echo "  2. Activate your environment: source .venv/bin/activate"
echo "  3. Open VS Code and select the .venv interpreter"
echo "  4. Open Claude Code — it auto-loads CLAUDE.md; run /setup or the"
echo "     environment-setup skill for project context"
echo ""
