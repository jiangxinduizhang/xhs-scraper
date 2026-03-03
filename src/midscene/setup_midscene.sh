#!/bin/bash
# 安装 Midscene 环境依赖

# 检查 node 是否安装
if ! command -v node &> /dev/null; then
    echo "错误: 未检测到 node 环境。请先安装 Node.js 18+。"
    exit 1
fi

echo "正在安装 Node.js 依赖..."
cd "$(dirname "$0")" || exit
npm install

if [ $? -eq 0 ]; then
    echo "✓ 依赖安装成功。"
else
    echo "✗ 依赖安装失败，请检查网络。"
    exit 1
fi
