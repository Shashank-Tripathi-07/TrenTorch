#!/bin/bash
# TrenTorch Development Environment Setup
# This script sets up the development environment for TrenTorch

set -e  # Exit on error

echo "🔥 Setting up TrenTorch development environment..."

# Check if virtual environment exists, create if not
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv || {
        echo "❌ Failed to create virtual environment"
        exit 1
    }
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
#
# OpenSSF Scorecard's Pinned-Dependencies check flags these three pip
# commands as unpinned (no --hash / --require-hashes). Deliberately left
# that way, not overlooked: requirements.txt and pyproject.toml already
# declare this project's actual dependency-version policy (deliberate
# floors, e.g. numpy>=2.2.6,<3.0.0, not exact pins -- see
# docs/implementation.md's own note on the settings.ini/pyproject.toml
# version-range discussion), and hash-pinning every transitive dependency
# would mean maintaining a separate lockfile this project doesn't
# otherwise have, just for this one entry point. `pip install -e .` in
# particular can't be hash-pinned at all -- it installs from the local
# checkout, not a resolved PyPI package. ruff's own pip install (lint.yml,
# autofix.yml) got pinned to an exact version instead, since that one's a
# standalone tool install, not a project-dependency install governed by
# requirements.txt's own policy.
echo "📦 Installing dependencies..."
pip install -r requirements.txt || {
    echo "⚠️  Some dependencies failed - continuing with essential packages"
}

# Install TrenTorch in development mode
echo "🔧 Installing TrenTorch in development mode..."
pip install -e . || {
    echo "⚠️  Development install had issues - continuing"
}

echo "✅ Development environment setup complete!"
echo ""
echo "💡 To activate the environment in the future, run:"
echo "   source .venv/bin/activate"
echo ""
echo "💡 Quick commands:"
echo "   tren system health    - Diagnose environment"
echo "   tren module test      - Run tests"
echo "   tren --help           - See all commands"
echo ""
echo "📋 Optional Developer Tools:"
echo "   VHS (GIF generation): brew install vhs"
echo "   See docs/development/DEVELOPER_SETUP.md for details"
