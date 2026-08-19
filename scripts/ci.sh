#!/usr/bin/env bash
set -euo pipefail

echo "== Backend =="
(
  cd backend
  ruff check .
  pytest -q
)

echo "== Frontend =="
(
  cd frontend
  npm run lint
  npm run test
  npm run build
  npm run test:e2e
)

echo "CI checks complete."
