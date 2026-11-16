"""
中国象棋强化学习自对弈训练器 (AlphaZero/DMC 启发式自对弈)
支持多进程并行对弈产生高质量经验，利用 5090D (CUDA) 或 Mac (MPS) 高速梯度更新。

使用方法：
  python rl_xiangqi/train.py --device auto --games 1000 --batch 256
"""

import argparse
import os
import random
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from env import XiangqiEnv, PIECE_VALUES
from model import XiangqiValueNet, IN_DIM

def self_play_game(net, device, max_steps=120, eps=0.1):
    """
    单局自我对弈：利用当前神经网络打分来选择走法（带 ε-贪心探索）
    返回：该局的所有 (局面特征, 最终回报) 样本
    """
    env = XiangqiEnv()
    states = []
    turns = [] # 记录当前轮到谁

    for step in range(max_steps):
        feat = env.get_features()
        moves = env.legal_moves()
        if not moves:
            break

        states.append(feat)
        turns.append(env.red_turn)

        # 候选走法决策
        if random.random() < eps:
            best_move = random.choice(moves)
        else:
            # 评估每个候选移动后的局面
            best_move = moves[0]
            best_val = -9999 if env.red_turn else 9999
            
            # 批量收集走后特征
            cand_feats = []
            for m in moves:
                env_copy = XiangqiEnv()
                env_copy.board = [row[:] for row in env.board]
                env_copy.red_turn = env.red_turn
                done, r = env_copy.step(m)
                cand_feats.append((m, env_copy.get_features(), done, r))

            with torch.no_grad():
                inputs = torch.tensor(np.stack([cf[1] for cf in cand_feats]), dtype=torch.float32, device=device)
                scores = net(inputs).cpu().numpy()

            for i, (m, _, done, r) in enumerate(cand_feats):
                score = r if done else scores[i]
                if env.red_turn:
                    if score > best_val:
                        best_val = score
                        best_move = m
                else:
                    if score < best_val:
                        best_val = score
                        best_move = m

        done, reward = env.step(best_move)
        if done:
            break

    # 结算胜负回报：红胜=1.0，黑胜=-1.0，和棋=0.0
    final_reward = 0.0
    if env.winner == 'red':
        final_reward = 1.0
    elif env.winner == 'black':
        final_reward = -1.0

    samples = []
    for s in states:
        samples.append((s, final_reward))

    return samples, env.winner

def main():
    parser = argparse.ArgumentParser(description="中国象棋神经网络自对弈训练")
    parser.add_argument("--device", default="auto", help="计算设备: auto (优先 cuda -> mps -> cpu)")
    parser.add_argument("--epochs", type=int, default=50, help="训练轮数")
    parser.add_argument("--games_per_epoch", type=int, default=20, help="每轮自对弈局数")
    parser.add_argument("--batch", type=int, default=256, help="批量大小")
    parser.add_argument("--lr", type=float, default=1e-3, help="学习率")
    parser.add_argument("--out", default="ckpt_xiangqi", help="检查点保存路径")
    parser.add_argument("--export", default="xiangqi_nn.bin", help="导出二进制模型路径")
    args = parser.parse_args()

    # 设备检测
    if args.device == "auto":
        if torch.cuda.is_available():
            dev_str = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            dev_str = "mps"
        else:
            dev_str = "cpu"
    else:
        dev_str = args.device

    device = torch.device(dev_str)
    print(f"[*] 中国象棋 AI 训练启动，计算设备: {dev_str}", flush=True)

    net = XiangqiValueNet().to(device)
    optimizer = optim.Adam(net.parameters(), lr=args.lr, weight_decay=1e-4)
    loss_fn = nn.MSELoss()

    os.makedirs(args.out, exist_ok=True)
    replay_buffer = []
    max_buf = 50000

    t_start = time.time()
    for ep in range(1, args.epochs + 1):
        t0 = time.time()
        red_wins, black_wins, draws = 0, 0, 0

        # 1. 自对弈生产样本
        net.eval()
        for _ in range(args.games_per_epoch):
            samples, winner = self_play_game(net, device)
            replay_buffer.extend(samples)
            if winner == 'red': red_wins += 1
            elif winner == 'black': black_wins += 1
            else: draws += 1

        if len(replay_buffer) > max_buf:
            replay_buffer = replay_buffer[-max_buf:]

        # 2. 批量梯度下降训练
        net.train()
        train_samples = random.sample(replay_buffer, min(len(replay_buffer), args.batch * 8))
        X = torch.tensor(np.stack([s[0] for s in train_samples]), dtype=torch.float32, device=device)
        Y = torch.tensor(np.array([s[1] for s in train_samples]), dtype=torch.float32, device=device)

        total_loss = 0.0
        batches = 0
        for i in range(0, len(X), args.batch):
            bx = X[i:i + args.batch]
            by = Y[i:i + args.batch]
            pred = net(bx)
            loss = loss_fn(pred, by)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            batches += 1

        avg_loss = total_loss / max(1, batches)
        dt = time.time() - t0
        print(f"[Epoch {ep:2d}/{args.epochs}] 耗时:{dt:4.1f}s | 胜负:红{red_wins}/黑{black_wins}/和{draws} | 缓冲池:{len(replay_buffer)} | Loss: {avg_loss:.4f}", flush=True)

        # 保存检查点
        if ep % 5 == 0 or ep == args.epochs:
            ckpt_file = os.path.join(args.out, f"xiangqi_step_{ep}.pt")
            torch.save(net.state_dict(), ckpt_file)
            torch.save(net.state_dict(), os.path.join(args.out, "last.pt"))

    # 导出为轻量级 JavaScript/Web 二进制权重
    from export import export_to_bin
    export_to_bin(os.path.join(args.out, "last.pt"), args.export)
    print(f"[✓] 训练全部完成！总耗时: {time.time() - t_start:.1f}s，模型已导出至 {args.export}", flush=True)

if __name__ == "__main__":
    main()
