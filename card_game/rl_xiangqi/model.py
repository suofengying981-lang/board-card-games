"""
中国象棋价值评估网络 (NNUE 结构轻量级版)
输入：1261 维特征 (90 棋位 × 14 种棋子 + 走子方标记)
网络：Linear(1261 -> 256) -> ReLU -> Linear(256 -> 128) -> ReLU -> Linear(128 -> 1) -> Tanh
输出：当前红方胜率预期回报 (-1.0 必输 ~ +1.0 必胜)
总参数量：约 35 万参数，模型权重仅约 700 KB！
支持 PyTorch CUDA (5090D)、Apple Silicon MPS (Mac) 以及快速 CPU 推理。
"""

import torch
import torch.nn as nn
import numpy as np

IN_DIM = 10 * 9 * 14 + 1 # 1261

class XiangqiValueNet(nn.Module):
    def __init__(self, in_dim=IN_DIM):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 256),
            nn.ReLU(inplace=True),
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, 1),
            nn.Tanh()
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)

class FastNumpyEvaluator:
    """CPU 端极速推理（无需 PyTorch 依赖，供对局和 JS 导出验证）"""
    def __init__(self, state_dict):
        self.W1 = state_dict['net.0.weight'].cpu().numpy().T
        self.b1 = state_dict['net.0.bias'].cpu().numpy()
        self.W2 = state_dict['net.2.weight'].cpu().numpy().T
        self.b2 = state_dict['net.2.bias'].cpu().numpy()
        self.W3 = state_dict['net.4.weight'].cpu().numpy().T
        self.b3 = state_dict['net.4.bias'].cpu().numpy()

    def evaluate(self, features):
        h1 = np.maximum(features @ self.W1 + self.b1, 0)
        h2 = np.maximum(h1 @ self.W2 + self.b2, 0)
        out = h2 @ self.W3 + self.b3
        return float(np.tanh(out[0]))
