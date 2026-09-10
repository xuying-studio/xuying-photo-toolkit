#!/usr/bin/env bash
set -euo pipefail

# 启动当前 Mac 开发版，不主动执行任何照片业务。
exec uv run xuying-toolbox "$@"
