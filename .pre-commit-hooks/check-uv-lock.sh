#!/bin/bash
# Pre-commit hook to ensure uv.lock is committed when pyproject.toml changes

set -e

# Check if pyproject.toml is staged
if git diff --cached --name-only | grep -q "^pyproject.toml$"; then
    # Check if uv.lock is also staged
    if ! git diff --cached --name-only | grep -q "^uv.lock$"; then
        echo "Error: pyproject.toml is staged but uv.lock is not!"
        echo ""
        echo "When pyproject.toml changes, uv.lock must also be updated and committed."
        echo ""
        echo "Please run:"
        echo "  git add uv.lock"
        echo ""
        echo "If uv.lock is not modified, it may be out of sync. Run:"
        echo "  uv sync"
        echo "  git add uv.lock"
        exit 1
    fi
fi

exit 0
