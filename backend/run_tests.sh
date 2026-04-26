#!/usr/bin/env bash
# =============================================================================
# HCS LLD 管理系统 - 本地测试运行脚本
# 用法: bash run_tests.sh [选项]
#   选项: -v  (详细输出, 默认启用)
#         -q  (简洁模式)
#         -s  (显示 print 输出)
#         -k  (按关键字过滤测试, 如: -k "region")
#         -x  (首个失败即停止)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   HCS LLD 管理系统 - 测试运行                       ${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════${NC}"
echo ""

# 检测虚拟环境
if [ ! -f "venv/bin/activate" ]; then
    echo -e "${YELLOW}⚠ 未检测到虚拟环境 (venv)${NC}"
    echo -e "${YELLOW}  请先执行: python3 -m venv venv${NC}"
    echo -e "${YELLOW}           source venv/bin/activate${NC}"
    echo -e "${YELLOW}           pip install -r requirements.txt${NC}"
    echo -e "${YELLOW}           pip install -e .${NC}"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查是否有 pytest 和 httpx
if ! python -c "import pytest" 2>/dev/null || ! python -c "import httpx" 2>/dev/null; then
    echo -e "${YELLOW}⚠ 缺少测试依赖，正在安装...${NC}"
    pip install "pytest>=8.0" "httpx>=0.27.0"
    echo ""
fi

# 确认应用可导入
echo -e "${BLUE}► 检查应用导入...${NC}"
if python -c "from app.main import app" 2>/dev/null; then
    echo -e "${GREEN}  ✓ 应用导入成功${NC}"
else
    echo -e "${RED}  ✗ 应用导入失败，请检查 pip install -e . 是否执行${NC}"
    exit 1
fi

echo ""

# 构建 pytest 参数
PYTEST_ARGS="tests/"
PYTEST_ARGS+=" -v"

# 解析用户参数
USER_ARGS=""
for arg in "$@"; do
    USER_ARGS+=" $arg"
done

echo -e "${BLUE}► 运行测试...${NC}"
echo ""

# 执行测试
python -m pytest $PYTEST_ARGS $USER_ARGS
EXIT_CODE=$?

echo ""

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}   ✅ 全部测试通过!${NC}"
    echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
else
    echo -e "${RED}══════════════════════════════════════════════════════${NC}"
    echo -e "${RED}   ❌ 存在失败的测试 (退出码: $EXIT_CODE)${NC}"
    echo -e "${RED}══════════════════════════════════════════════════════${NC}"
fi

exit $EXIT_CODE
