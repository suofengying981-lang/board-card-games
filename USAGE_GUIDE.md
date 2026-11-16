# 棋牌游戏合集 · 用户与集群训练完整使用指南

欢迎使用**棋牌游戏合集 (Board and Card Games Collection)**。本项目整合了**网页/安卓多款经典棋牌（中国象棋、斗地主、掼蛋、德州扑克、麻将等）**以及基于 Tailscale 虚拟局域网的**多设备分布式 AI 训练调度集群（RTX 5090D / 飞牛OS NAS / MacBook Pro）**。

---

## 目录
1. [📱 客户端与手机 App 使用指南](#1-客户端与手机-app-使用指南)
2. [♟️ 中国象棋全新功能使用说明](#2-中国象棋全新功能使用说明)
3. [🖥️ 多设备 AI 训练调度中心使用指南](#3-多设备-ai-训练调度中心使用指南)
4. [⚡ 5090D / NAS / MBP 节点接入与保活](#4-5090d--nas--mbp-节点接入与保活)
5. [🤖 AI 强化学习与自对弈训练实操说明](#5-ai-强化学习与自对弈训练实操说明)

---

## 1. 📱 客户端与手机 App 使用指南

### 1.1 安装与更新方式
- **安卓 APK 下载**：
  - 官方 GitHub Actions 每次代码合并会自动打包发布最新 APK。
  - 最新安装包下载地址：
    👉 [点击下载最新版 qipai.apk](https://github.com/suofengying981-lang/board-card-games/releases/download/apk-latest/qipai.apk)
  - 手机直接安装，允许“安装未知来源应用”即可。内置了版本自动递增与统一签名，**后续新版本可直接覆盖安装，对局战绩与设置不丢失**。
- **网页端即开即玩**：
  - 支持手机/电脑浏览器直接打开大厅 `card_game/index.html`。
  - 支持 PWA 离线缓存，无网络也可单机畅玩。

---

## 2. ♟️ 中国象棋全新功能使用说明

最新版象棋已全面还原经典实战界面，融合了由 RTX 5090D 训练的 NNUE 深度神经网络评估引擎：

### 2.1 核心界面与走棋
- **执红先行**：点击棋子，棋盘会以绿点（空位）或红色虚线圈（吃子目标）高亮所有合法走法。
- **局势评估条（胜率/形势）**：
  - 顶栏红黑双色动态能量条，实时显示双方盘面优势。
  - 右侧显示 `红优 +X`、`黑优 +X` 或 `均势 0`，基于神经网络盘面价值推算。
- **上一手轨迹指示**：对方或己方刚才走的棋子，会以绿色方框高亮标出起点与落点。

### 2.2 核心操作按钮
1. **💡 智能提示**：
   - 轮到你走棋时点击「提示」，AI 会以黄色虚线圈在棋盘上标出最佳推荐招法，状态栏显示如 `💡 推荐走法: 炮二平五`。
   - **循环切换**：再次点击「提示」可在前 3 种建议方案之间切换，并附带方案编号。
2. **📈 评棋**：
   - 点击可唤出深度局势分析卡片，给出当前优劣得失（微优/大优/防守建议）以及当前局面的最优解。
3. **↩️ 悔棋**：
   - 走错时点击，自动撤销己方与电脑的上一步，回到你的回合。
4. **🏳️ 认输 & ➕ 新局**：
   - 随时认输或开启全新对局。

### 2.3 棋谱记录、复盘与导出
- **实时标准记谱**：对局中的每一步均被自动转换为专业中文记谱（如 `1. 炮二平五 马8进7`）。
- **点击底部「📄 棋谱」**：
  - 查看完整对局走子回合列表。
  - **复制文本棋谱**：一键将整局棋谱复制到剪贴板，方便分享至微信或供复盘工具分析。
  - **导出 PGN 棋谱**：一键保存为 `.txt` 棋谱文件到手机或电脑本地。

### 2.4 难度切换（神经网络大师）
- 点击底部 **「⚙️ 设置」** 或右上角菜单：
  - **新手**：2层浅层启发式搜索，适合初学者。
  - **高手**：3层深度 Minimax 搜索，杀法攻守兼备。
  - **大师 (神经网络)**：加载 5090D 自对弈演化生成的 `xiangqi_nn.bin`（NNUE 1261 维稀疏特征全连接价值网络），具备敏锐的大局观与战术洞察。

---

## 3. 🖥️ 多设备 AI 训练调度中心使用指南

我们构建了基于 Tailscale 虚拟专网的轻量级集中调度中心，Web 界面地址：
👉 **`http://100.72.67.60:18080/`** （飞牛OS NAS 节点）

### 3.1 调度中心功能布局
1. **🌐 终端设备节点卡片**：
   - 每 3 秒自动轮询在线设备状态（CPU/GPU 型号、可用显存、当前运行任务、心跳时间）。
2. **🎮 游戏任务分类选项卡**：
   - `[ ♠️ 斗地主 ]`、`[ ♟️ 中国象棋 ]`、`[ 🎴 掼蛋 ]`。
3. **🎯 目标终端与预设任务**：
   - 点击选中上方某台在线设备（如 RTX-5090D）。
   - 点击预设任务卡片（如“强化学习自对弈训练”）。
   - 点击 **「下发执行」** 即可驱动该节点开始跑训练！
4. **💻 实时终端日志输出**：
   - 自动滚动捕获远程节点运行的实时训练 Loss、胜负比例与 Epoch 进度。

---

## 4. ⚡ 5090D / NAS / MBP 节点接入与保活

如果调度中心页面中显示某个设备离线（超过 15 秒无心跳自动隐藏），按照以下命令重新启动对应设备的 Agent 即可：

### 4.1 RTX 5090D 节点接入 (Windows PowerShell)
```powershell
cd C:\Users\Administrator\board-card-games
python cluster/agent_node.py --manager http://100.72.67.60:18080 --name RTX-5090D
```
*(如果更新了代码，启动前可执行 `git pull origin main`)*

### 4.2 飞牛OS NAS 节点接入 (Linux SSH)
- **调度服务端（后台保持）**：
  ```bash
  cd ~/board-card-games/cluster
  nohup python3 cluster_manager.py --port 18080 > manager.log 2>&1 &
  ```
- **NAS 本机计算 Agent（用于 CPU 挂机推演）**：
  ```bash
  cd ~/board-card-games
  nohup python3 cluster/agent_node.py --manager http://127.0.0.1:18080 --name fnOS-NAS > node.log 2>&1 &
  ```

### 4.3 MacBook Pro 节点接入 (macOS Terminal)
```bash
cd ~/board-card-games
python3 cluster/agent_node.py --manager http://100.72.67.60:18080 --name MBP-Local
```

---

## 5. 🤖 AI 强化学习与自对弈训练实操说明

### 5.1 中国象棋神经网络训练 (NNUE / AlphaZero 演化)
- **在调度中心一键下发**，或在 5090D 本地执行：
  ```bash
  cd card_game
  # 自对弈训练 100 轮，每轮 20 局，利用 CUDA 极速并行
  python rl_xiangqi/train.py --device auto --epochs 100 --games_per_epoch 20
  ```
- **导出并应用模型**：
  ```bash
  python rl_xiangqi/export.py rl_xiangqi/ckpt/last.pt card_game/xiangqi_nn.bin
  ```
- 模型导出后 `git push` 到仓库，手机 App 与网页版即可立即继承新训练出来的大师棋力！

### 5.2 斗地主自对弈与蒸馏体系
- **5090D 算力重型自对弈**：
  ```bash
  cd card_game
  python rl/supervise.py --device cuda --batch 4096 --actors 16
  ```
- **飞牛OS NAS 24小时挂机推演（生成专家对局库）**：
  ```bash
  cd card_game
  node rl/gen_teacher.js teacher/data_nas.bin 60 250 8
  ```
- **模型微调/蒸馏与导出**：
  ```bash
  python rl/distill.py --data "teacher/*.bin" --epochs 20
  python rl/export.py rl/ckpt/last.pt card_game/ddz_nn.bin
  ```
