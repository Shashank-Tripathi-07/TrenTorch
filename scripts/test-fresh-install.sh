#!/bin/bash
# =============================================================================
# TrenTorch Fresh Install Test
# =============================================================================
# Simulates exactly what a student experiences: fresh machine, curl install,
# run through modules and milestones.
#
# Usage:
#   ./scripts/test-fresh-install.sh                    # Test against main
#   ./scripts/test-fresh-install.sh --branch dev       # Test against dev
#   ./scripts/test-fresh-install.sh --branch feature/foo --ci  # CI mode
#
# This catches issues like:
#   - Git LFS files not being pulled correctly
#   - Missing dependencies in requirements.txt
#   - Interactive prompts blocking non-interactive use
#   - Broken install script
# =============================================================================

set -e

# Defaults
BRANCH="main"
CI_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --ci)
            CI_MODE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--branch BRANCH] [--ci]"
            exit 1
            ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

print_step() { echo -e "\n${CYAN}▶ $1${NC}"; }
print_pass() { echo -e "${GREEN}✓ $1${NC}"; }
print_fail() { echo -e "${RED}✗ $1${NC}"; }

# Build the test script that runs inside container (or CI)
# Using a function to allow variable interpolation
build_test_script() {
    cat << 'OUTER_EOF'
set -e

BRANCH="__BRANCH__"

echo "══════════════════════════════════════════════════════════════"
echo "  TrenTorch Fresh Install Test"
echo "  Branch: $BRANCH"
echo "══════════════════════════════════════════════════════════════"

# Step 1: Install from specified branch
echo ""
echo "▶ Step 1: Running install script (branch: $BRANCH)..."
export TRENTORCH_BRANCH="$BRANCH"
export TRENTORCH_NON_INTERACTIVE=1
# TrenTorch is currently a private repo: raw.githubusercontent.com 404s an
# anonymous request the same way it would for a nonexistent file, so this
# needs GITHUB_TOKEN (present automatically in this repo's own CI) passed
# as a bearer token. install.sh's own internal git clone needs the same
# token, which it already reads from this same env var -- exported above
# via TRENTORCH_BRANCH and here via GITHUB_TOKEN, which stays in the
# environment for `bash /tmp/install.sh` below to inherit.
CURL_AUTH=()
if [ -n "$GITHUB_TOKEN" ]; then
    CURL_AUTH=(-H "Authorization: token $GITHUB_TOKEN")
fi
curl -fsSL "${CURL_AUTH[@]}" "https://raw.githubusercontent.com/Shashank-Tripathi-07/TrenTorch/${BRANCH}/quarto/install.sh" -o /tmp/install.sh || {
bash /tmp/install.sh

cd trentorch
source .venv/bin/activate

# Step 2: Verify tren works
echo ""
echo "▶ Step 2: Verifying tren CLI..."
tren --version

# Step 3: Verify datasets are real files (not LFS pointers)
echo ""
echo "▶ Step 3: Checking dataset files..."
TRAIN_PKL="datasets/tinydigits/train.pkl"
if [ -f "$TRAIN_PKL" ]; then
    # Check first bytes - pickle files start with 0x80, LFS pointers start with "version"
    FIRST_CHAR=$(head -c 1 "$TRAIN_PKL" | xxd -p)
    if [ "$FIRST_CHAR" = "80" ]; then
        echo "✓ train.pkl is valid pickle data"
    else
        echo "✗ train.pkl appears to be an LFS pointer, not actual data"
        head -c 100 "$TRAIN_PKL"
        exit 1
    fi
else
    echo "✗ train.pkl not found"
    exit 1
fi

# Step 4: Test loading the dataset directly
echo ""
echo "▶ Step 4: Testing dataset loading..."
python3 -c "
import pickle
with open('datasets/tinydigits/train.pkl', 'rb') as f:
    data = pickle.load(f)
print(f'✓ Loaded {len(data[\"images\"])} training images')
"

# Step 5: Run milestone 01 (Perceptron - simplest)
# No --non-interactive flag: `tren milestone run` doesn't have one, and
# doesn't need one -- it already checks sys.stdin/stdout.isatty() itself
# and skips its "Press Enter to begin" / "Continue to next part?" prompts
# automatically whenever it isn't attached to a real terminal, which is
# always true here (piped/CI). Passing --non-interactive just makes
# argparse reject the whole command before any of that logic runs.
echo ""
echo "▶ Step 5: Running Milestone 01 (Perceptron)..."
timeout 120 tren milestone run 01 || {
    echo "⚠ Milestone 01 did not complete (may need module implementations)"
}

# Step 6: Run milestone 03 (MLP with TinyDigits - the one that caught the LFS bug)
echo ""
echo "▶ Step 6: Running Milestone 03 (MLP/TinyDigits)..."
timeout 180 tren milestone run 03 || {
    echo "⚠ Milestone 03 did not complete (may need module implementations)"
}

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  ✓ Fresh install test completed!"
echo "══════════════════════════════════════════════════════════════"
OUTER_EOF
}

# =============================================================================
# Main
# =============================================================================

echo "Testing TrenTorch installation from branch: $BRANCH"

# Build test script with branch substituted
TEST_SCRIPT=$(build_test_script | sed "s|__BRANCH__|$BRANCH|g")

if [ "$CI_MODE" = true ]; then
    print_step "Running in CI mode (no Docker)"

    # Install git and curl if needed (for CI environments)
    if ! command -v git &> /dev/null; then
        apt-get update && apt-get install -y git curl xxd
    fi

    eval "$TEST_SCRIPT"
else
    print_step "Running via Docker (simulates clean student machine)"

    # Check Docker is available
    if ! command -v docker &> /dev/null; then
        print_fail "Docker not found. Install Docker or run with --ci in a clean environment."
        exit 1
    fi

    # Run in Docker - note: no git-lfs installed, just like a typical student machine
    docker run --rm \
        -e DEBIAN_FRONTEND=noninteractive \
        -e GITHUB_TOKEN="$GITHUB_TOKEN" \
        python:3.11-slim \
        bash -c "
            apt-get update && apt-get install -y git curl xxd > /dev/null 2>&1
            $TEST_SCRIPT
        "

    print_pass "Fresh install test completed successfully"
fi
