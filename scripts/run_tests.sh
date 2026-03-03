#!/bin/bash
# 运行单元测试（无设备依赖）
set -e

cd "$(dirname "$0")/.."

echo "=== 小红书抓取系统 - 单元测试 ==="
echo "工作目录: $(pwd)"
echo ""

# 检查 pytest 是否安装
if ! python3 -m pytest --version &>/dev/null; then
    echo "安装测试依赖..."
    pip install pytest pytest-mock
fi

# 运行单元测试
python3 -m pytest tests/unit/ -v --tb=short

echo ""
echo "=== 单元测试完成 ==="
