"""
中国象棋 Python 核心规则环境与特征编码器
棋盘规格：10 行 9 列 (90 个交叉点)
棋子类型：14 种 (红方 7 种 KABNRCP, 黑方 7 种 kabnrcp)
特征维度：
  - 棋盘状态：90 个位置 × 14 种棋子 = 1260 维 (one-hot，稀疏编码)
  - 走子方特征：1 维 (1 表示红方走，0 表示黑方走)
  总特征维度 = 1261
"""

import copy
import random
import numpy as np

# 棋子定义与基础子力价值 (分值仅作基线参考)
PIECES = ['K', 'A', 'B', 'N', 'R', 'C', 'P', 'k', 'a', 'b', 'n', 'r', 'c', 'p']
P2I = {p: i for i, p in enumerate(PIECES)}

PIECE_VALUES = {
    'K': 10000, 'k': 10000,
    'R': 900, 'r': 900,
    'C': 450, 'c': 450,
    'N': 400, 'n': 400,
    'B': 200, 'b': 200,
    'A': 200, 'a': 200,
    'P': 100, 'p': 100
}

def is_red(p):
    return p is not None and 'A' <= p <= 'Z'

def is_black(p):
    return p is not None and 'a' <= p <= 'z'

def same_color(p1, p2):
    if not p1 or not p2:
        return False
    return (is_red(p1) and is_red(p2)) or (is_black(p1) and is_black(p2))

def in_board(r, c):
    return 0 <= r < 10 and 0 <= c < 9

class XiangqiEnv:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [
            ['r', 'n', 'b', 'a', 'k', 'a', 'b', 'n', 'r'],
            [None] * 9,
            [None, 'c', None, None, None, None, None, 'c', None],
            ['p', None, 'p', None, 'p', None, 'p', None, 'p'],
            [None] * 9,
            [None] * 9,
            ['P', None, 'P', None, 'P', None, 'P', None, 'P'],
            [None, 'C', None, None, None, None, None, 'C', None],
            [None] * 9,
            ['R', 'N', 'B', 'A', 'K', 'A', 'B', 'N', 'R']
        ]
        self.red_turn = True
        self.winner = None
        self.step_count = 0
        return self.get_features()

    def get_moves(self, r, c):
        p = self.board[r][c]
        if not p:
            return []
        red = is_red(p)
        moves = []

        def add(tr, tc):
            if not in_board(tr, tc):
                return
            target = self.board[tr][tc]
            if same_color(p, target):
                return
            moves.append(((r, c), (tr, tc), p, target))

        t = p.upper()
        if t == 'K':
            min_r, max_r = (7, 9) if red else (0, 2)
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                tr, tc = r + dr, c + dc
                if min_r <= tr <= max_r and 3 <= tc <= 5:
                    add(tr, tc)
            # 老将照面
            step = -1 if red else 1
            tr = r + step
            while 0 <= tr < 10:
                tp = self.board[tr][c]
                if tp:
                    if tp.upper() == 'K' and not same_color(p, tp):
                        moves.append(((r, c), (tr, c), p, tp))
                    break
                tr += step
        elif t == 'A':
            min_r, max_r = (7, 9) if red else (0, 2)
            for dr, dc in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
                tr, tc = r + dr, c + dc
                if min_r <= tr <= max_r and 3 <= tc <= 5:
                    add(tr, tc)
        elif t == 'B':
            for dr, dc, er, ec in [(2, 2, 1, 1), (2, -2, 1, -1), (-2, 2, -1, 1), (-2, -2, -1, -1)]:
                tr, tc = r + dr, c + dc
                if (red and tr < 5) or (not red and tr > 4):
                    continue
                if in_board(tr, tc) and not self.board[r + er][c + ec]:
                    add(tr, tc)
        elif t == 'N':
            dirs = [
                (-2, -1, -1, 0), (-2, 1, -1, 0),
                (2, -1, 1, 0), (2, 1, 1, 0),
                (-1, -2, 0, -1), (1, -2, 0, -1),
                (-1, 2, 0, 1), (1, 2, 0, 1)
            ]
            for dr, dc, br, bc in dirs:
                tr, tc = r + dr, c + dc
                if in_board(tr, tc) and not self.board[r + br][c + bc]:
                    add(tr, tc)
        elif t == 'R':
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                tr, tc = r + dr, c + dc
                while in_board(tr, tc):
                    target = self.board[tr][tc]
                    if not target:
                        add(tr, tc)
                    else:
                        if not same_color(p, target):
                            add(tr, tc)
                        break
                    tr += dr; tc += dc
        elif t == 'C':
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                tr, tc = r + dr, c + dc
                jumped = False
                while in_board(tr, tc):
                    target = self.board[tr][tc]
                    if not jumped:
                        if not target:
                            add(tr, tc)
                        else:
                            jumped = True
                    else:
                        if target:
                            if not same_color(p, target):
                                add(tr, tc)
                            break
                    tr += dr; tc += dc
        elif t == 'P':
            fwd = -1 if red else 1
            add(r + fwd, c)
            crossed = (r <= 4) if red else (r >= 5)
            if crossed:
                add(r, c - 1)
                add(r, c + 1)

        return moves

    def legal_moves(self):
        moves = []
        for r in range(10):
            for c in range(9):
                p = self.board[r][c]
                if p and (is_red(p) if self.red_turn else is_black(p)):
                    moves.extend(self.get_moves(r, c))
        return moves

    def step(self, move):
        (fr, fc), (tr, tc), p, captured = move
        self.board[tr][tc] = p
        self.board[fr][fc] = None
        self.step_count += 1

        if captured and captured.upper() == 'K':
            self.winner = 'red' if self.red_turn else 'black'
            return True, 1.0 if self.red_turn else -1.0

        if self.step_count >= 200: # 超过200回合和棋
            self.winner = 'draw'
            return True, 0.0

        self.red_turn = not self.red_turn
        # 检查对方是否无子可动
        if not self.legal_moves():
            self.winner = 'red' if not self.red_turn else 'black'
            return True, 1.0 if self.winner == 'red' else -1.0

        return False, 0.0

    def get_features(self):
        """返回 1261 维特征向量 (float32): 90×14 + 1"""
        feat = np.zeros(10 * 9 * 14 + 1, dtype=np.float32)
        idx = 0
        for r in range(10):
            for c in range(9):
                p = self.board[r][c]
                if p:
                    feat[idx + P2I[p]] = 1.0
                idx += 14
        feat[-1] = 1.0 if self.red_turn else 0.0
        return feat
