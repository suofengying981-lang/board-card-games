# Tailscale 分布式训练调度集群使用指南

本项目包含一个开箱即用的轻量级分布式调度器，专门为 **Tailscale 虚拟专网** 环境设计。支持在 Web 界面上实时监控各终端在线情况，并一键指派训练任务。

---

## 架构说明

- **中央调度控制台 (`cluster_manager.py`)**：纯 Python 标准库编写的 Web 服务端，推荐常驻运行在 **飞牛 OS (NAS)** 上（7×24小时在线）。
- **计算节点 Agent (`agent_node.py`)**：常驻运行在各终端设备（如 MacBook Pro、5090D 工作站或飞牛OS自身），自动汇报硬件与任务进度，接收执行指令。

---

## 快速使用步骤

### 第一步：启动中央控制台（推荐在飞牛 OS 上）

在飞牛 OS（或其他常开设备）上运行：

```bash
cd board-card-games/cluster
python cluster_manager.py --port 8080
```

启动后，在你的 **任何连入 Tailscale 的设备（包括手机或 MacBook）** 浏览器中，打开飞牛 OS 的 Tailscale IP 即可进入控制台：
`http://<飞牛OS的Tailscale_IP>:8080`

---

### 第二步：各终端设备加入集群

#### 1. MacBook Pro 加入集群（负责模型微调/蒸馏）
在你的 Mac 终端上运行：
```bash
cd board-card-games/cluster
python agent_node.py --server http://<飞牛OS的Tailscale_IP>:8080 --name "MacBook-Pro"
```
> Agent 会自动识别 Mac 的 Apple Silicon 芯片与 MPS 硬件加速，并在控制台显示为就绪状态。

#### 2. 飞牛 OS 自身作为算力节点（负责挂机生成推演对局）
在飞牛 OS 的另一个后台终端（或 screen/tmux）运行：
```bash
cd board-card-games/cluster
python agent_node.py --server http://127.0.0.1:8080 --name "fnOS-NAS"
```

#### 3. 5090D 工作站（开机即可连入）
在 5090D 电脑上运行：
```bash
cd board-card-games/cluster
python agent_node.py --server http://<飞牛OS的Tailscale_IP>:8080 --name "RTX-5090D"
```

---

### 第三步：在 Web 网页上一键调度

打开 Web 控制台，你将看到所有在线的设备卡片：
1. **点选目标设备**（例如点选 MacBook Pro 或 fnOS-NAS）。
2. **选择任务类型**：
   - ⚡ **模型微调/蒸馏**：推荐指派给 MacBook Pro（自动调用 MPS 加速）或 5090D。
   - 🎲 **挂机推演生成牌谱**：推荐指派给飞牛 OS（多核 CPU 挂机，不占日常笔记本电量）。
   - 🔥 **强化学习自对弈**：推荐指派给 5090D。
   - 📊 **对局胜率快速评测**：任意设备均可。
3. 点击 **「下发执行」**，目标终端会自动拉起任务，且实时日志会直接滚屏显示在网页下方！
