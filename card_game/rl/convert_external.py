"""
外部公开斗地主数据集转换器
支持将 DouZero / 开源竞技平台 JSON/CSV 格式的专家对局数据，
转换为本项目 distill.py 原生支持的二进制训练数据格式：
  [u8 相对座位(0/1/2)] [u8 候选数 n] [u8[611] 状态特征]
  重复 n 次: [u8[60] 动作特征] [f32 目标胜率/回报 (-1.0 ~ 1.0)]
"""

import argparse
import json
import os
import struct
import numpy as np

# 导入环境基础维度与编码函数
from env import ADIM, NR, SDIM, FULL, onehot_counts

def cards_to_15(cards):
    """
    将牌列表 (3..10, J=11, Q=12, K=13, A=14, 2=15, B=16, R=17 或数字 0..14)
    映射到 15 维计数字数列表 (0:3 ... 12:2, 13:小王, 14:大王)
    """
    cnt = [0] * NR
    for c in cards:
        if isinstance(c, str):
            mapping = {
                '3': 0, '4': 1, '5': 2, '6': 3, '7': 4, '8': 5, '9': 6, '10': 7,
                'J': 8, 'Q': 9, 'K': 10, 'A': 11, '2': 12, 'B': 13, 'R': 14,
                'w': 13, 'W': 14, 'j': 13, 'JOKER': 14
            }
            idx = mapping.get(c.upper(), 0)
        else:
            idx = c
        if 0 <= idx < NR:
            cnt[idx] += 1
    return cnt

def build_record(seat_rel, hand_cnt, played_by, acts_history, counts, bombs, bottom_cnt, candidates_with_q):
    """
    根据某个决策点生成单条训练特征二进制流
    candidates_with_q: [(action_cnt_15, q_value), ...]
    """
    # 1. 状态特征 611 维
    s = seat_rel
    nxt, prv = (s + 1) % 3, (s + 2) % 3
    unseen = [FULL[i] - hand_cnt[i] - sum(played_by[k][i] for k in range(3)) for i in range(NR)]
    
    f = [
        onehot_counts(hand_cnt),
        onehot_counts(unseen),
        onehot_counts(played_by[s]),
        onehot_counts(played_by[nxt]),
        onehot_counts(played_by[prv])
    ]
    
    # 最近三手动作
    slots = [np.zeros(60, dtype=np.uint8) for _ in range(3)]
    for k in range(min(3, len(acts_history))):
        act = acts_history[-1 - k]
        if act is not None:
            slots[k] = onehot_counts(act)
    f += slots
    
    # 剩余牌数 (63维)
    left = np.zeros(63, dtype=np.uint8)
    for k, p in enumerate((s, nxt, prv)):
        left[k * 21 + min(20, counts[p])] = 1
    f.append(left)
    
    # 炸弹数 (8维)
    b = np.zeros(8, dtype=np.uint8)
    b[min(bombs, 7)] = 1
    f.append(b)
    
    # 底牌 (60维)
    f.append(onehot_counts(bottom_cnt))
    
    state_feat = np.concatenate(f)
    assert state_feat.shape[0] == SDIM
    
    # 2. 组装二进制
    n = len(candidates_with_q)
    parts = [struct.pack("<BB", seat_rel, n), state_feat.tobytes()]
    
    for act_cnt, q_val in candidates_with_q:
        act_feat = np.zeros(ADIM, dtype=np.uint8) if act_cnt is None else onehot_counts(act_cnt)
        parts.append(act_feat.tobytes())
        parts.append(struct.pack("<f", float(q_val)))
        
    return b"".join(parts)

def generate_mock_expert_dataset(out_file, num_samples=1000):
    """
    内置轻量测试用例：模拟生成专家格式样本，用于检验转换管道
    """
    print(f"[*] 正在生成模拟测试数据到 {out_file} (共 {num_samples} 个决策点)...")
    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
    
    with open(out_file, "wb") as f:
        for _ in range(num_samples):
            seat_rel = np.random.randint(0, 3)
            hand = [0] * NR
            for _ in range(10):
                hand[np.random.randint(0, NR)] += 1
            played_by = [[0] * NR for _ in range(3)]
            acts_history = []
            counts = [10, 12, 8]
            bombs = 0
            bottom = [0] * NR
            
            # 模拟 3 个候选动作
            cands = []
            # 候选1：出单张
            c1 = [0] * NR; c1[np.random.randint(0, 10)] = 1
            cands.append((c1, 0.8))  # 专家选择打分高
            # 候选2：出对子
            c2 = [0] * NR; c2[np.random.randint(0, 10)] = 2
            cands.append((c2, -0.2))
            # 候选3：不出
            cands.append((None, -0.5))
            
            buf = build_record(seat_rel, hand, played_by, acts_history, counts, bombs, bottom, cands)
            f.write(buf)
            
    print(f"[+] 模拟数据生成成功，文件大小: {os.path.getsize(out_file)} 字节")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="斗地主外部数据集转换器")
    parser.add_argument("--demo", action="store_true", help="生成微型模拟测试数据，用于打通并测试训练流")
    parser.add_argument("--out", default="teacher/mock_expert.bin", help="输出二进制文件路径")
    args = parser.parse_args()
    
    if args.demo:
        generate_mock_expert_dataset(args.out, num_samples=2000)
    else:
        print("请传入具体外部对局文件路径进行解析转换，或加 --demo 生成测试流。")
