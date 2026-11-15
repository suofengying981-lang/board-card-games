#!/bin/bash
set -e

FNOS_SERVER="http://100.72.67.60:8080"
REPO_URL="https://github.com/suofengying981-lang/board-card-games.git"
INSTALL_DIR="$HOME/board-card-games"

echo "========================================================"
echo "  [RTX 5090D 工作站] 计算节点 Agent 一键配置"
echo "  中央控制台: $FNOS_SERVER"
echo "========================================================"

if ! command -v python3 &> /dev/null; then
    echo "[-] 未检测到 python3，请先安装 Python 3"
    exit 1
fi

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

pkill -f "agent_node.py.*RTX-5090D" || true

echo "[*] 启动 5090D 计算节点 Agent..."
nohup python3 agent_node.py --server "$FNOS_SERVER" --name "RTX-5090D" > agent_5090d.log 2>&1 &

sleep 2

if ps aux | grep -v grep | grep -q "agent_node.py"; then
    echo ""
    echo "========================================================"
    echo "  [✓] RTX 5090D 算力节点已成功启动！"
    echo "  已成功接入飞牛 OS 集群控制台: $FNOS_SERVER"
    echo "========================================================"
else
    echo "[-] 启动失败，请查看 agent_5090d.log 日志"
fi
