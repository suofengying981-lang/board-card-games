"""
分布式集群中央调度控制台 (Cluster Manager)
推荐部署在 飞牛 OS (NAS) 上（常开机），或者任意一台机器上。
纯 Python 3 标准库实现（无需安装 Flask、FastAPI 等第三方包），开箱即用。

功能：
1. 提供 Web 界面，实时展示 Tailscale 网络中各机器的在线状态、硬件与负载
2. 支持在网页上一键对指定机器下发：
   - 模型微调/蒸馏 (推荐 MBP)
   - 挂机批量生成推演牌局 (推荐 飞牛OS)
   - 强化学习自对弈 (推荐 5090D)
   - 对局胜率评测
3. 网页实时查看执行中的终端日志与进度
"""

import http.server
import json
import os
import sys
import threading
import time
import urllib.parse

# 状态字典：记录所有已注册节点
# node_id -> { info, last_seen, pending_command }
NODES = {}
LOCK = threading.Lock()

# 预设任务模板
PRESET_TASKS = [
    {
        "id": "distill",
        "name": "⚡ 模型微调/蒸馏 (Distill)",
        "desc": "基于推演或公开数据进行监督学习，耗时短，优先推荐 MBP (MPS) 或 GPU",
        "recommended_device": "Apple Silicon (MPS) / NVIDIA CUDA",
        "command": "python rl/distill.py --data \"teacher/*.bin\" --epochs 20"
    },
    {
        "id": "gen_teacher",
        "name": "🎲 挂机推演生成专家牌谱 (ISMCTS)",
        "desc": "利用多核 CPU 挂机模拟，自动生成高质量推演对局数据，极适合 NAS 常开挂机",
        "recommended_device": "飞牛OS (CPU 多核)",
        "command": "node rl/gen_teacher.js teacher/data_nas.bin 60 250 8"
    },
    {
        "id": "supervise_rl",
        "name": "🔥 强化学习自对弈训练 (RL Supervise)",
        "desc": "重型自对弈强化学习，计算量大，专为 5090D 等专业显卡设计",
        "recommended_device": "NVIDIA 5090D (CUDA 12.8+)",
        "command": "python rl/supervise.py --device cuda --batch 4096 --actors 16"
    },
    {
        "id": "eval",
        "name": "📊 对局胜率快速评测",
        "desc": "当前模型与困难档蒙特卡洛对打 100 局，检验水平提升幅度",
        "recommended_device": "任意设备",
        "command": "node rl/eval_vs_hard.js 100 25"
    },
    {
        "id": "export_model",
        "name": "🚀 导出最新模型并生效 (Export)",
        "desc": "将最新检查点导出为浏览器端 ddz_nn.bin，完成 AI 棋力升级闭环",
        "recommended_device": "5090D / MBP",
        "command": "python rl/export.py rl/ckpt/last.pt ddz_nn.bin"
    },
    {
        "id": "train_xiangqi",
        "name": "♟️ 中国象棋神经网络自对弈训练",
        "desc": "基于 NNUE 价值网络自我对弈，极速演化，专为 5090D 或 MBP 设计",
        "recommended_device": "5090D (CUDA) / MBP (MPS)",
        "command": "python rl_xiangqi/train.py --device auto --epochs 30 --games_per_epoch 15"
    }
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>棋牌 AI 集群训练调度控制台</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background-color: #0f172a; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  </style>
</head>
<body class="p-4 md:p-8">
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <header class="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-700/60 gap-4">
      <div>
        <div class="flex items-center gap-3">
          <span class="inline-block w-3 h-3 rounded-full bg-emerald-400 animate-ping"></span>
          <h1 class="text-2xl font-bold tracking-tight text-white">棋牌 AI 集群训练调度中心</h1>
        </div>
        <p class="text-xs text-slate-400 mt-1">基于 Tailscale 虚拟专网 · 跨平台协同算力调度 (MBP / 飞牛OS / 5090D)</p>
      </div>
      <div class="flex items-center gap-3 text-xs bg-slate-800/80 px-3.5 py-2 rounded-lg border border-slate-700">
        <span>已连入节点: <strong id="node-count" class="text-emerald-400 text-sm font-mono">0</strong> 台</span>
        <span class="text-slate-500">|</span>
        <span class="text-slate-400">调度器状态: <span class="text-emerald-400">运行中</span></span>
      </div>
    </header>

    <!-- Node Grid -->
    <div>
      <h2 class="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
        <span>🌐 终端设备节点</span>
        <span class="text-[11px] font-normal text-slate-500">(每 3 秒自动刷新)</span>
      </h2>
      <div id="nodes-grid" class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- 动态注入节点卡片 -->
      </div>
    </div>

    <!-- Task Dispatching Panel -->
    <div class="bg-slate-800/60 border border-slate-700/80 rounded-xl p-5 shadow-lg space-y-4">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
        <span>🎯 任务调度指派</span>
        <span id="target-hint" class="text-xs text-indigo-400 font-mono">请先在上方选择目标终端</span>
      </h2>

      <!-- Task presets -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3" id="task-presets">
        <!-- 任务列表 -->
      </div>

      <!-- Command preview & launch -->
      <div class="bg-slate-900/80 rounded-lg p-3.5 border border-slate-700/80 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
        <div class="flex-1 font-mono text-slate-300 overflow-x-auto py-1" id="cmd-preview">
          # 选择任务后将在此生成命令
        </div>
        <div class="flex items-center gap-2">
          <button onclick="stopCurrentTask()" id="btn-stop" class="hidden px-4 py-2 bg-rose-600/80 hover:bg-rose-600 text-white font-medium rounded-lg transition-all">
            终止当前任务
          </button>
          <button onclick="dispatchSelectedTask()" id="btn-dispatch" class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg shadow transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed">
            下发执行
          </button>
        </div>
      </div>
    </div>

    <!-- Live Log Console -->
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl space-y-2">
      <div class="flex items-center justify-between text-xs text-slate-400 pb-2 border-b border-slate-800">
        <span class="font-mono flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
          实时终端日志输出 (<span id="log-node-title">无</span>)
        </span>
        <span class="text-[11px] text-slate-500">自动滚动</span>
      </div>
      <div id="log-console" class="font-mono text-xs text-emerald-400/90 bg-black/40 p-3 rounded-lg h-56 overflow-y-auto space-y-1 select-text">
        <div class="text-slate-500">// 点击上方任意节点，即可在此处查看其运行日志...</div>
      </div>
    </div>
  </div>

  <script>
    const PRESETS = """ + json.dumps(PRESET_TASKS, ensure_ascii=False) + """;
    let selectedNodeId = null;
    let selectedTaskId = 'distill';

    function renderTasks() {
      const container = document.getElementById('task-presets');
      container.innerHTML = PRESETS.map(t => `
        <div onclick="selectTask('${t.id}')" id="task-card-${t.id}"
             class="cursor-pointer p-3 rounded-lg border transition-all ${t.id === selectedTaskId ? 'border-indigo-500 bg-indigo-950/40 text-white' : 'border-slate-700 bg-slate-800/40 text-slate-300 hover:border-slate-500'}">
          <div class="flex items-center justify-between">
            <span class="font-medium text-xs md:text-sm text-slate-100">${t.name}</span>
            <span class="text-[10px] bg-slate-700/60 text-slate-300 px-2 py-0.5 rounded font-mono">${t.recommended_device}</span>
          </div>
          <p class="text-[11px] text-slate-400 mt-1 line-clamp-1">${t.desc}</p>
        </div>
      `).join('');
      updateCmdPreview();
    }

    function selectTask(tid) {
      selectedTaskId = tid;
      renderTasks();
    }

    function updateCmdPreview() {
      const task = PRESETS.find(t => t.id === selectedTaskId);
      const cmdEl = document.getElementById('cmd-preview');
      cmdEl.innerText = task ? task.command : '';
    }

    function selectNode(nid) {
      selectedNodeId = nid;
      updateUI();
    }

    async function fetchNodes() {
      try {
        const res = await fetch('/api/nodes');
        const data = await res.json();
        window.currentNodesData = data;
        updateUI();
      } catch(e) {}
    }

    function updateUI() {
      const nodes = window.currentNodesData || {};
      const nodeIds = Object.keys(nodes);
      document.getElementById('node-count').innerText = nodeIds.length;

      if (!selectedNodeId && nodeIds.length > 0) {
        selectedNodeId = nodeIds[0];
      }

      const grid = document.getElementById('nodes-grid');
      if (nodeIds.length === 0) {
        grid.innerHTML = `
          <div class="col-span-3 text-center py-8 text-slate-500 text-xs border border-dashed border-slate-700 rounded-xl">
            暂无终端节点在线。请在任意终端 (如 MBP 或飞牛OS) 运行：<br>
            <code class="bg-slate-800 text-slate-300 px-2 py-1 rounded mt-2 inline-block font-mono">python cluster/agent_node.py --server http://&lt;当前机器IP&gt;:8080</code>
          </div>
        `;
      } else {
        grid.innerHTML = nodeIds.map(nid => {
          const n = nodes[nid];
          const isSel = nid === selectedNodeId;
          const isRunning = n.status === 'running';
          return `
            <div onclick="selectNode('${nid}')" class="cursor-pointer p-4 rounded-xl border transition-all ${isSel ? 'border-indigo-500 bg-indigo-950/20 shadow-md ring-1 ring-indigo-500/40' : 'border-slate-700/80 bg-slate-800/40 hover:border-slate-500'}">
              <div class="flex items-center justify-between">
                <span class="font-bold text-sm text-white flex items-center gap-1.5">
                  ${n.node_name}
                </span>
                <span class="text-[10px] px-2 py-0.5 rounded font-mono font-medium ${isRunning ? 'bg-amber-500/20 text-amber-400' : 'bg-emerald-500/20 text-emerald-400'}">
                  ${isRunning ? '运行中' : '空闲'}
                </span>
              </div>
              <p class="text-xs text-slate-400 mt-2 font-mono">${n.hardware.accelerator} · ${n.hardware.hardware_detail}</p>
              <div class="mt-3 pt-2 border-t border-slate-700/50 flex items-center justify-between text-[11px] text-slate-400">
                <span>任务: ${n.task ? n.task.name : '无'}</span>
                <span class="text-slate-500">${Math.round(Date.now()/1000 - n.last_seen)}秒前活跃</span>
              </div>
            </div>
          `;
        }).join('');
      }

      // 更新选中提示与按钮
      const cur = nodes[selectedNodeId];
      const hint = document.getElementById('target-hint');
      const btnStop = document.getElementById('btn-stop');
      const btnDispatch = document.getElementById('btn-dispatch');

      if (cur) {
        hint.innerText = `目标节点: ${cur.node_name} (${cur.hardware.accelerator})`;
        document.getElementById('log-node-title').innerText = cur.node_name;
        if (cur.status === 'running') {
          btnStop.classList.remove('hidden');
          btnDispatch.disabled = true;
          btnDispatch.innerText = '执行中...';
        } else {
          btnStop.classList.add('hidden');
          btnDispatch.disabled = false;
          btnDispatch.innerText = '下发执行';
        }

        // 更新日志
        if (cur.recent_logs && cur.recent_logs.length > 0) {
          const consoleEl = document.getElementById('log-console');
          consoleEl.innerHTML = cur.recent_logs.map(l => `<div>${escapeHtml(l)}</div>`).join('');
          consoleEl.scrollTop = consoleEl.scrollHeight;
        }
      } else {
        hint.innerText = '未选择目标终端';
        btnDispatch.disabled = true;
      }
    }

    function escapeHtml(str) {
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    async function dispatchSelectedTask() {
      if (!selectedNodeId) return alert('请先选择一台目标终端设备！');
      const task = PRESETS.find(t => t.id === selectedTaskId);
      if (!task) return;

      const res = await fetch('/api/dispatch', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          node_id: selectedNodeId,
          task_name: task.name,
          command_line: task.command
        })
      });
      const ret = await res.json();
      if (ret.ok) {
        alert('指令已成功下发至 ' + selectedNodeId + '！');
        fetchNodes();
      } else {
        alert('下发失败: ' + ret.error);
      }
    }

    async function stopCurrentTask() {
      if (!selectedNodeId) return;
      if (!confirm('确定要强制终止该节点上的任务吗？')) return;
      await fetch('/api/stop', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ node_id: selectedNodeId })
      });
      fetchNodes();
    }

    renderTasks();
    fetchNodes();
    setInterval(fetchNodes, 3000);
  </script>
</body>
</html>
"""

class ClusterRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif url.path == "/api/nodes":
            with LOCK:
                now = time.time()
                # 过滤掉 15 秒以上没心跳的离线节点
                active_nodes = {}
                for k, v in list(NODES.items()):
                    if now - v["last_seen"] <= 15:
                        active_nodes[k] = v
                    else:
                        pass
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(active_nodes, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        if url.path == "/api/heartbeat":
            node_id = data.get("node_id")
            if not node_id:
                self.send_response(400)
                self.end_headers()
                return

            with LOCK:
                node = NODES.get(node_id, {})
                node.update({
                    "node_id": node_id,
                    "node_name": data.get("node_name", node_id),
                    "status": data.get("status", "idle"),
                    "hardware": data.get("hardware", {}),
                    "task": data.get("task"),
                    "recent_logs": data.get("recent_logs", []),
                    "last_seen": time.time()
                })
                # 检查是否有等待下发的指令
                pending_cmd = node.pop("pending_command", None)
                NODES[node_id] = node

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "command": pending_cmd}).encode("utf-8"))

        elif url.path == "/api/dispatch":
            node_id = data.get("node_id")
            with LOCK:
                if node_id in NODES:
                    NODES[node_id]["pending_command"] = {
                        "action": "start",
                        "task_name": data.get("task_name"),
                        "command_line": data.get("command_line")
                    }
                    resp = {"ok": True}
                else:
                    resp = {"ok": False, "error": "节点不在线"}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))

        elif url.path == "/api/stop":
            node_id = data.get("node_id")
            with LOCK:
                if node_id in NODES:
                    NODES[node_id]["pending_command"] = {"action": "stop"}
                    resp = {"ok": True}
                else:
                    resp = {"ok": False, "error": "节点不在线"}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # 禁用烦人的常规请求控制台刷屏日志
        return

def run_server(port=8080):
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), ClusterRequestHandler)
    print("=" * 60)
    print(f"  棋牌 AI 集群训练调度中心已启动！")
    print(f"  本地访问:   http://127.0.0.1:{port}")
    print(f"  Tailscale:  请使用此机器的 Tailscale IP，在任意设备浏览器打开")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止。")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="集群中央控制台")
    parser.add_argument("--port", type=int, default=8080, help="服务端口 (默认 8080)")
    args = parser.parse_args()
    run_server(args.port)
