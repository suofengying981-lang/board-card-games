#!/bin/bash
set -e

FNOS_IP="100.72.67.60"
REPO_URL="https://github.com/suofengying981-lang/board-card-games.git"
INSTALL_DIR="$HOME/board-card-games"

echo "========================================================"
echo "  [飞牛 OS] 调度中央控制台一键安装部署"
echo "  本机 IP: $FNOS_IP"
echo "========================================================"

# 1. 检查 Python 3
if ! command -v python3 &> /dev/null; then
    echo "[-] 未检测到 python3，请在飞牛系统终端执行: apt update && apt install -y python3"
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

# 3. 停止已有进程
pkill -f "cluster_manager.py" || true
pkill -f "agent_node.py.*fnOS-NAS" || true

# 4. 启动中央 Web 控制台（后台运行，日志存入 manager.log）
echo "[*] 启动中央调度控制台 (Port 8080)..."
nohup python3 cluster_manager.py --port 8080 > manager.log 2>&1 &

# 5. 启动飞牛 OS 自身算力 Agent（可挂机跑推演生数据）
echo "[*] 启动飞牛本地算力节点 Agent..."
nohup python3 agent_node.py --server http://127.0.0.1:8080 --name "fnOS-NAS" > agent.log 2>&1 &

sleep 2

# 6. 验证
if ps aux | grep -v grep | grep -q "cluster_manager.py"; then
    echo ""
    echo "========================================================"
    echo "  [✓] 飞牛 OS 控制台部署成功！"
    echo "  请在任意设备（MBP/手机）浏览器访问:"
    echo "  👉 http://$FNOS_IP:8080"
    echo "========================================================"
else
    echo "[-] 启动失败，请检查 cluster/manager.log 日志内容"
fi
