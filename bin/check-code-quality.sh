#!/bin/bash
# Script to run code quality checks

set -e

echo "🔍 Running code quality checks..."

# Run ruff for linting and formatting
echo "🧹 Running ruff..."
ruff check .
ruff format --check .

# Run mypy for type checking
echo "🔍 Running mypy..."
mypy route_listener

# Run radon for code complexity
echo "📊 Running radon..."
radon cc route_listener -a

# Run pylint for additional analysis
echo "🔍 Running pylint..."
pylint route_listener

echo "✅ All code quality checks passed!" 