#!/bin/bash
# TinyTorch Development Environment Setup
# This script sets up the development environment for TinyTorch

set -e  # Exit on error

echo "🔥 Setting up TinyTorch development environment..."

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
echo "📦 Installing dependencies..."
pip install -r requirements.txt || {
    echo "⚠️  Some dependencies failed - continuing with essential packages"
}

# Install TinyTorch in development mode
echo "🔧 Installing TinyTorch in development mode..."
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
