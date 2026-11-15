"""
轻量级分布式计算节点 Agent (Tailscale 节点工作端)
运行在各终端设备上 (MacBook Pro / 飞牛OS / 5090D 工作站等)
无需安装复杂框架，只需 Python 3 标准库即可运行。

功能：
1. 定时向飞牛OS上的中央控制台汇报自身硬件状态与空闲算力 (CPU / GPU / 内存 / 当前任务)
2. 接收控制台下发的训练/推演任务并异步执行
3. 实时上报训练日志与进度
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import threading
import time
import urllib.request

class NodeAgent:
    def __init__(self, node_id, node_name, server_url, poll_interval=3):
        self.node_id = node_id
        self.node_name = node_name
        self.server_url = server_url.rstrip("/")
        self.poll_interval = poll_interval
        self.current_process = None
        self.current_task = None
        self.task_log = []
        self.lock = threading.Lock()

    def detect_hardware(self):
        """自动检测本机平台与计算能力 (Apple MPS / NVIDIA CUDA / CPU)"""
        system = platform.system()
        accel = "CPU"
        detail = f"{platform.processor()} ({os.cpu_count()} 核)"

        if system == "Darwin":
            accel = "Apple Silicon (MPS)"
        else:
            try:
                res = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                                     capture_output=True, text=True, timeout=2)
                if res.returncode == 0 and res.stdout.strip():
                    accel = "NVIDIA CUDA"
                    detail = res.stdout.strip().replace("\n", "; ")
            except Exception:
                pass

        return {
            "system": system,
            "accelerator": accel,
            "hardware_detail": detail,
            "cpu_cores": os.cpu_count()
        }

    def heartbeat(self):
        """向中央服务器发送心跳"""
        hw = self.detect_hardware()
        with self.lock:
            status = "idle"
            task_info = None
            if self.current_process and self.current_process.poll() is None:
                status = "running"
                task_info = self.current_task

            recent_logs = self.task_log[-15:] if self.task_log else []

        payload = {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "status": status,
            "hardware": hw,
            "task": task_info,
            "recent_logs": recent_logs,
            "timestamp": time.time()
        }

        try:
            req = urllib.request.Request(
                f"{self.server_url}/api/heartbeat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                cmd = resp_data.get("command")
                if cmd:
                    self.handle_command(cmd)
        except Exception as e:
            # 服务端暂时不可达时静默等待
            pass

    def handle_command(self, cmd_info):
        """处理服务端下发的指令"""
        action = cmd_info.get("action")
        if action == "stop":
            with self.lock:
                if self.current_process and self.current_process.poll() is None:
                    self.current_process.terminate()
                    self.task_log.append("[Agent] 任务已被服务端手动终止")
        elif action == "start":
            with self.lock:
                if self.current_process and self.current_process.poll() is None:
                    return # 已经在运行中
                task_cmd = cmd_info.get("command_line")
                task_name = cmd_info.get("task_name", "未知任务")
                self.current_task = {"name": task_name, "command": task_cmd, "start_time": time.time()}
                self.task_log = [f"[Agent] 启动任务: {task_name}", f"[Agent] 命令行: {task_cmd}"]
                threading.Thread(target=self._run_task, args=(task_cmd,), daemon=True).start()

    def _run_task(self, command_line):
        """在后台异步执行任务并收集日志"""
        try:
            cwd = os.path.dirname(os.path.abspath(__file__))
            repo_root = os.path.dirname(cwd)
            proc = subprocess.Popen(
                command_line,
                shell=True,
                cwd=os.path.join(repo_root, "card_game"),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            with self.lock:
                self.current_process = proc

            for line in proc.stdout:
                line_str = line.strip()
                if line_str:
                    with self.lock:
                        self.task_log.append(line_str)
                        if len(self.task_log) > 200:
                            self.task_log.pop(0)

            proc.wait()
            with self.lock:
                self.task_log.append(f"[Agent] 任务完成，退出码: {proc.returncode}")
        except Exception as e:
            with self.lock:
                self.task_log.append(f"[Agent] 执行异常: {str(e)}")

    def run(self):
        print(f"==================================================")
        print(f"  Tailscale 训练节点 Agent 已启动")
        print(f"  节点名称: {self.node_name} ({self.node_id})")
        print(f"  中央控制台: {self.server_url}")
        print(f"==================================================")
        while True:
            self.heartbeat()
            time.sleep(self.poll_interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tailscale 训练节点 Agent")
    parser.add_argument("--server", default="http://127.0.0.1:8080", help="控制台服务器地址 (如 http://100.x.x.x:8080)")
    parser.add_argument("--name", default=None, help="节点友好名称 (默认自动获取主机名)")
    parser.add_argument("--id", default=None, help="节点唯一ID")
    args = parser.parse_args()

    hostname = platform.node() or "unknown_node"
    node_name = args.name or hostname
    node_id = args.id or f"{hostname}_{os.getpid()}"

    agent = NodeAgent(node_id, node_name, args.server)
    agent.run()
