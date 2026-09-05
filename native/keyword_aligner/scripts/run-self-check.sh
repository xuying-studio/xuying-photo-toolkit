#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT="${TMPDIR:-/tmp}/keyword-aligner-self-check"

swiftc \
  "$ROOT_DIR/Sources/KeywordAlignerCore/Models.swift" \
  "$ROOT_DIR/Sources/KeywordAlignerCore/TimelineMath.swift" \
  "$ROOT_DIR/scripts/self-check.swift" \
  -o "$OUTPUT"

"$OUTPUT"
