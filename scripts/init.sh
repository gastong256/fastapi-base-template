#!/usr/bin/env bash
# init.sh — Replace template placeholders and rename the source package.
#
# Usage (via Makefile):
#   PROJECT_NAME="Acme API" PROJECT_SLUG="acme_api" \
#   SERVICE_NAME="acme-api" OWNER="acme-org"       \
#   DESCRIPTION="Internal API for Acme" make init
#
# Or directly:
#   bash scripts/init.sh
set -euo pipefail

# ── Validate required variables ────────────────────────────────────────────────
: "${PROJECT_NAME:?PROJECT_NAME is required}"
: "${PROJECT_SLUG:?PROJECT_SLUG is required}"
: "${SERVICE_NAME:?SERVICE_NAME is required}"
: "${OWNER:?OWNER is required}"
: "${DESCRIPTION:?DESCRIPTION is required}"

echo "→ Initializing template: ${PROJECT_NAME} (${PROJECT_SLUG})"

# ── Replace placeholders in all tracked and untracked (non-ignored) files ─────
# git ls-files skips .git/, .venv/, __pycache__, and anything in .gitignore.
# The | delimiter in sed handles spaces in PROJECT_NAME and DESCRIPTION.
git ls-files --others --cached --exclude-standard | while IFS= read -r file; do
    [[ -f "$file" ]] || continue
    sed -i \
        -e "s|__PROJECT_NAME__|${PROJECT_NAME}|g" \
        -e "s|__PROJECT_SLUG__|${PROJECT_SLUG}|g" \
        -e "s|__SERVICE_NAME__|${SERVICE_NAME}|g" \
        -e "s|__OWNER__|${OWNER}|g" \
        -e "s|__DESCRIPTION__|${DESCRIPTION}|g" \
        "$file"
done

# ── Rename source package directory ──────────────────────────────────────────
if [[ -d "src/__PROJECT_SLUG__" ]]; then
    mv "src/__PROJECT_SLUG__" "src/${PROJECT_SLUG}"
    echo "→ Renamed src/__PROJECT_SLUG__ → src/${PROJECT_SLUG}"
fi

echo ""
echo "✓ Template initialized successfully."
echo ""
echo "Next steps:"
echo "  make install   # Install dependencies"
echo "  make run       # Start development server"
echo "  curl http://localhost:8000/api/v1/ping"
