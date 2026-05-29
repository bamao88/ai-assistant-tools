#!/bin/bash
# 一键启动 wechat-article-exporter 服务
# 用法: ./start-exporter.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXPORTER_DIR="$SCRIPT_DIR/wechat-article-exporter"

if [ "${1:-}" = "--background" ] || [ "${1:-}" = "--ensure" ]; then
    exec python3 "$SCRIPT_DIR/scripts/gzh/exporter_service.py"
fi

if [ ! -d "$EXPORTER_DIR" ]; then
    echo "❌ 未找到 wechat-article-exporter 目录: $EXPORTER_DIR"
    echo "请先 clone 仓库:"
    echo "  cd $(dirname "$EXPORTER_DIR")"
    echo "  git clone https://github.com/wechat-article/wechat-article-exporter.git"
    exit 1
fi

cd "$EXPORTER_DIR"

# 确保依赖已安装
if [ ! -d "node_modules" ]; then
    echo "📦 安装依赖..."
    corepack enable 2>/dev/null || true
    yarn install
fi

echo "🚀 启动 wechat-article-exporter (http://localhost:3000)..."
echo "   按 Ctrl+C 停止"
yarn dev
