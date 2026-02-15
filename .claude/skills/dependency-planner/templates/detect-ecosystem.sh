#!/bin/bash
# Template: Detect Ecosystem
# Purpose: Identify package manager from manifest files
# Usage: ./detect-ecosystem.sh <manifest-path>
#
# Returns the ecosystem type and required files for updates

set -euo pipefail

MANIFEST="${1:?Usage: $0 <manifest-path>}"

detect_ecosystem() {
    local file="$1"
    local basename=$(basename "$file")

    case "$basename" in
        "pyproject.toml")
            # Check for uv vs poetry
            if [[ -f "uv.lock" ]] || grep -q "\[tool.uv\]" "$file" 2>/dev/null; then
                echo "uv"
            elif [[ -f "poetry.lock" ]] || grep -q "\[tool.poetry\]" "$file" 2>/dev/null; then
                echo "poetry"
            else
                echo "pip"
            fi
            ;;
        "requirements.txt")
            echo "pip"
            ;;
        "package.json")
            if [[ -f "pnpm-lock.yaml" ]]; then
                echo "pnpm"
            elif [[ -f "yarn.lock" ]]; then
                echo "yarn"
            else
                echo "npm"
            fi
            ;;
        "Cargo.toml")
            echo "cargo"
            ;;
        "go.mod")
            echo "go"
            ;;
        "Gemfile")
            echo "bundler"
            ;;
        "composer.json")
            echo "composer"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

get_required_files() {
    local ecosystem="$1"

    case "$ecosystem" in
        "uv")
            echo "pyproject.toml uv.lock"
            ;;
        "poetry")
            echo "pyproject.toml poetry.lock"
            ;;
        "pip")
            echo "requirements.txt"
            ;;
        "npm")
            echo "package.json package-lock.json"
            ;;
        "yarn")
            echo "package.json yarn.lock"
            ;;
        "pnpm")
            echo "package.json pnpm-lock.yaml"
            ;;
        "cargo")
            echo "Cargo.toml Cargo.lock"
            ;;
        "go")
            echo "go.mod go.sum"
            ;;
        "bundler")
            echo "Gemfile Gemfile.lock"
            ;;
        "composer")
            echo "composer.json composer.lock"
            ;;
        *)
            echo "$MANIFEST"
            ;;
    esac
}

get_update_command() {
    local ecosystem="$1"
    local package="$2"
    local version="$3"

    case "$ecosystem" in
        "uv")
            echo "uv lock --upgrade-package ${package}==${version}"
            ;;
        "poetry")
            echo "poetry update ${package}@${version} --lock"
            ;;
        "pip")
            echo "pip install ${package}==${version}"
            ;;
        "npm")
            echo "npm install ${package}@${version} --package-lock-only"
            ;;
        "yarn")
            echo "yarn add ${package}@${version} --mode update-lockfile"
            ;;
        "pnpm")
            echo "pnpm update ${package}@${version} --lockfile-only"
            ;;
        "cargo")
            echo "cargo update -p ${package}@${version}"
            ;;
        "go")
            echo "go get ${package}@v${version} && go mod tidy"
            ;;
        *)
            echo "# Unknown ecosystem: manual update required"
            ;;
    esac
}

# Main
ECOSYSTEM=$(detect_ecosystem "$MANIFEST")
REQUIRED_FILES=$(get_required_files "$ECOSYSTEM")

echo "Ecosystem: $ECOSYSTEM"
echo "Required files: $REQUIRED_FILES"

# If package and version provided, show update command
if [[ -n "${2:-}" ]] && [[ -n "${3:-}" ]]; then
    echo "Update command: $(get_update_command "$ECOSYSTEM" "$2" "$3")"
fi
