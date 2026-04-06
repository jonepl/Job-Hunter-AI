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
# STEP 3 — Scaffold Project Structure
# =============================================================================
info "Step 3: Scaffolding project structure..."

# Create directories
mkdir -p ai/skills
mkdir -p docs
mkdir -p src/scraper
mkdir -p src/evaluator
mkdir -p src/tools
mkdir -p tests

# Create placeholder Python init files
touch src/__init__.py
touch src/scraper/__init__.py
touch src/evaluator/__init__.py
touch src/tools/__init__.py
touch tests/__init__.py

# Create placeholder markdown files (do not overwrite if they exist)
[ -f "ai/rules.md" ]                        || touch ai/rules.md
[ -f "ai/commands.md" ]                     || touch ai/commands.md
[ -f "ai/skills/feature-development.md" ]   || touch ai/skills/feature-development.md
[ -f "ai/skills/debugging.md" ]             || touch ai/skills/debugging.md
[ -f "ai/skills/testing.md" ]               || touch ai/skills/testing.md
[ -f "ai/skills/environment-setup.md" ]     || touch ai/skills/environment-setup.md
[ -f "docs/prd.md" ]                        || touch docs/prd.md
[ -f "docs/architecture.md" ]               || touch docs/architecture.md
[ -f "README.md" ]                          || touch README.md

success "Project structure created"

echo ""

# =============================================================================
# STEP 4 — Create .gitignore
# =============================================================================
info "Step 4: Creating .gitignore..."

if [ -f ".gitignore" ]; then
    warn ".gitignore already exists — skipping"
else
cat > .gitignore << 'EOF'
# Environment
.env
.venv/
__pycache__/
*.pyc
*.pyo

# VS Code
.vscode/

# OS
.DS_Store
Thumbs.db

# Python packaging
*.egg-info/
dist/
build/

# Test artifacts
.pytest_cache/
.coverage
htmlcov/

# Playwright
playwright-report/
test-results/
EOF
success ".gitignore created"
fi

echo ""

# =============================================================================
# STEP 5 — Create .env File
# =============================================================================
info "Step 5: Creating .env file..."

if [ -f ".env" ]; then
    warn ".env already exists — skipping (your keys are safe)"
else
cat > .env << 'EOF'

# -- Scheduler --
SCHEDULE_ENABLED=false
SCHEDULE_CRON=*/6 * * * * #0 10 * * 1,4
SCHEDULE_TIMEZONE=America/New_York

# ── API Keys & Evaluator ──
EVALUATOR_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
JSEARCH_API_KEY=your_jsearch_api_key_here

# ── Evaluator Cost ──
OPENAI_INPUT_COST_PER_1M=2.50
OPENAI_OUTPUT_COST_PER_1M=10.00
ANTHROPIC_INPUT_COST_PER_1M=3.00
ANTHROPIC_OUTPUT_COST_PER_1M=15.00

# ── Email ──
GMAIL_ADDRESS=your_sender_email_address
GMAIL_APP_PASSWORD=your_gmail_password
EMAIL_RECIPIENT=your_recipient_email_address

# -- Evaluator Costs ───────────────────────────────────────────────────────
SHOW_COST_ESTIMATE=false
OPENAI_INPUT_COST_PER_1M=2.50
OPENAI_OUTPUT_COST_PER_1M=10.00
ANTHROPIC_INPUT_COST_PER_1M=3.00
ANTHROPIC_OUTPUT_COST_PER_1M=15.00

# ── Search Profiles ──
PROFILE_COUNT=1

# Search Profile 1
PROFILE_1_QUERY=Senior Software Engineer
PROFILE_1_WORK_TYPE=remote
# PROFILE_1_LOCATION=New York, US
PROFILE_1_DATE_POSTED=3days # 24h, 3days, week, month. Default: `3days`.
PROFILE_1_SCORE_THRESHOLD=80 # 0 - 100 
PROFILE_1_SCRAPERS=indeed #linkedin,indeed,glassdoor,ziprecruiter
PROFILE_1_SCORE_THRESHOLD=90

EOF
success ".env created with placeholder values"
warn "ACTION REQUIRED: Replace placeholder values in .env with your real API keys"
fi

echo ""

# =============================================================================
# STEP 6 — Create requirements.txt
# =============================================================================
info "Step 6: Creating requirements.txt..."

if [ -f "requirements.txt" ]; then
    warn "requirements.txt already exists — skipping"
else
cat > requirements.txt << 'EOF'
# LLM Provider
openai

# Environment variable management
python-dotenv

# Web scraping
playwright
beautifulsoup4
requests

# Resume parsing
pypdf2

# Testing
pytest
pytest-asyncio

# Utilities
lxml
EOF
success "requirements.txt created"
fi

echo ""

# =============================================================================
# STEP 7 — Install Python Dependencies
# =============================================================================
info "Step 7: Installing Python dependencies..."

.venv/bin/pip install -r requirements.txt --quiet
success "Python dependencies installed"

echo ""

# =============================================================================
# STEP 8 — Install Playwright Browser Binaries
# =============================================================================
info "Step 8: Installing Playwright browser binaries..."

.venv/bin/playwright install
success "Playwright browser binaries installed"

echo ""

# =============================================================================
# STEP 9 — Initialize Git Repository
# =============================================================================
info "Step 9: Initializing Git repository..."

if [ -d ".git" ]; then
    warn "Git repository already exists — skipping init"
else
    git init
    git add .
    git commit -m "Initial project setup — environment bootstrap complete"
    success "Git repository initialized with initial commit"
fi

echo ""

# =============================================================================
# STEP 10 — Final Validation
# =============================================================================
info "Step 10: Running final validation..."

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
echo "  4. Ask Claude Code to read ai/skills/environment-setup.md for project context"
echo ""
