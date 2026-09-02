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
# requirements.txt is a pip-compile-generated, hash-pinned lockfile (see
# its own header, and requirements.in for the human-edited source policy);
# --require-hashes is what satisfies OpenSSF Scorecard's Pinned-Dependencies
# check. A hash mismatch means the resolved package isn't what this repo
# actually vetted, so this is a hard failure now, not a "continue anyway".
echo "📦 Installing dependencies..."
pip install --require-hashes -r requirements.txt

# Install TrenTorch in development mode
#
# `pip install -e .` can't be hash-pinned: it installs from this local
# checkout, not a resolved PyPI artifact, so there's no hash to check
# against. This is a real, permanent Scorecard finding (dismissed in the
# Security tab with that reasoning), not an oversight.
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
