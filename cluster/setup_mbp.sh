#!/bin/bash
set -e

FNOS_SERVER="http://100.72.67.60:8080"
REPO_URL="https://github.com/suofengying981-lang/board-card-games.git"
INSTALL_DIR="$HOME/board-card-games"

echo "========================================================"
echo "  [MacBook Pro] 计算节点 Agent 一键配置"
echo "  中央控制台: $FNOS_SERVER"
echo "========================================================"

# 1. 检查 Python 3
if ! command -v python3 &> /dev/null; then
    echo "[-] 未检测到 python3，请先安装 Python 3"
    exit 1
fi

# 2. 拉取或更新仓库
if [ -d "$INSTALL_DIR" ]; then
    echo "[*] 更新现有仓库: $INSTALL_DIR"
    cd "$INSTALL_DIR"
    git pull origin main || true
else
    echo "[*] 克隆项目仓库到: $INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

cd "$INSTALL_DIR/cluster"

# 3. 停止旧的 Agent
pkill -f "agent_node.py.*MacBook-Pro" || true

# 4. 启动 Agent（后台常驻）
echo "[*] 启动 MacBook Pro 计算节点 Agent..."
nohup python3 agent_node.py --server "$FNOS_SERVER" --name "MacBook-Pro" > agent_mbp.log 2>&1 &

sleep 2

if ps aux | grep -v grep | grep -q "agent_node.py"; then
    echo ""
    echo "========================================================"
    echo "  [✓] MacBook Pro 算力节点已成功启动！"
    echo "  正在向飞牛 OS ($FNOS_SERVER) 汇报 Apple Silicon MPS 算力"
    echo "  打开浏览器查看: http://100.72.67.60:8080"
    echo "========================================================"
else
    echo "[-] 启动失败，请查看 agent_mbp.log 日志"
fi
