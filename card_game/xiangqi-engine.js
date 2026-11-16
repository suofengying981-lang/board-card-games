/**
 * 中国象棋规则与 AI 引擎 (纯 JS / 浏览器与 Node 通用)
 * 棋盘坐标：0..9 行 (row)，0..8 列 (col)
 * 红方在下 (row 6..9)，黑方在上 (row 0..3)
 * 棋子编码：
 *   红方 (大写): K(帅), A(仕), B(相), N(马), R(车), C(炮), P(兵)
 *   黑方 (小写): k(将), a(士), b(象), n(马), r(车), c(炮), p(卒)
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.XiangqiEngine = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const PIECE_NAMES = {
    'K': '帅', 'A': '仕', 'B': '相', 'N': '马', 'R': '车', 'C': '炮', 'P': '兵',
    'k': '将', 'a': '士', 'b': '象', 'n': '马', 'r': '车', 'c': '炮', 'p': '卒'
  };

  const PIECE_VALUES = {
    'K': 10000, 'k': 10000,
    'R': 900, 'r': 900,
    'C': 450, 'c': 450,
    'N': 400, 'n': 400,
    'B': 200, 'b': 200,
    'A': 200, 'a': 200,
    'P': 100, 'p': 100
  };

  // 初始棋盘 10 行 9 列
  function initBoard() {
    return [
      ['r', 'n', 'b', 'a', 'k', 'a', 'b', 'n', 'r'],
      [null, null, null, null, null, null, null, null, null],
      [null, 'c', null, null, null, null, null, 'c', null],
      ['p', null, 'p', null, 'p', null, 'p', null, 'p'],
      [null, null, null, null, null, null, null, null, null],
      [null, null, null, null, null, null, null, null, null],
      ['P', null, 'P', null, 'P', null, 'P', null, 'P'],
      [null, 'C', null, null, null, null, null, 'C', null],
      [null, null, null, null, null, null, null, null, null],
      ['R', 'N', 'B', 'A', 'K', 'A', 'B', 'N', 'R']
    ];
  }

  function isRed(p) { return p && p >= 'A' && p <= 'Z'; }
  function isBlack(p) { return p && p >= 'a' && p <= 'z'; }
  function sameColor(p1, p2) {
    if (!p1 || !p2) return false;
    return (isRed(p1) && isRed(p2)) || (isBlack(p1) && isBlack(p2));
  }

  function inBoard(r, c) { return r >= 0 && r < 10 && c >= 0 && c < 9; }

  // 生成特定位置的所有合法移动 [ {from: [r,c], to: [tr,tc], piece, captured} ]
  function getMoves(board, r, c) {
    const p = board[r][c];
    if (!p) return [];
    const red = isRed(p);
    const moves = [];
    const add = (tr, tc) => {
      if (!inBoard(tr, tc)) return;
      const target = board[tr][tc];
      if (sameColor(p, target)) return;
      moves.push({ from: [r, c], to: [tr, tc], piece: p, captured: target });
    };

    const type = p.toUpperCase();
    if (type === 'K') { // 将/帅：只能在九宫格内走一步
      const minR = red ? 7 : 0, maxR = red ? 9 : 2;
      const dirs = [[0, 1], [0, -1], [1, 0], [-1, 0]];
      for (const [dr, dc] of dirs) {
        const tr = r + dr, tc = c + dc;
        if (tr >= minR && tr <= maxR && tc >= 3 && tc <= 5) add(tr, tc);
      }
      // 飞将规则 (老将照面)
      const step = red ? -1 : 1;
      let tr = r + step;
      while (tr >= 0 && tr < 10) {
        const tp = board[tr][c];
        if (tp) {
          if (tp.toUpperCase() === 'K' && !sameColor(p, tp)) {
            moves.push({ from: [r, c], to: [tr, c], piece: p, captured: tp });
          }
          break;
        }
        tr += step;
      }
    } else if (type === 'A') { // 士/仕：只能在九宫格斜走
      const minR = red ? 7 : 0, maxR = red ? 9 : 2;
      const dirs = [[1, 1], [1, -1], [-1, 1], [-1, -1]];
      for (const [dr, dc] of dirs) {
        const tr = r + dr, tc = c + dc;
        if (tr >= minR && tr <= maxR && tc >= 3 && tc <= 5) add(tr, tc);
      }
    } else if (type === 'B') { // 象/相：田字格，不可过河，有塞象眼
      const dirs = [[2, 2, 1, 1], [2, -2, 1, -1], [-2, 2, -1, 1], [-2, -2, -1, -1]];
      for (const [dr, dc, er, ec] of dirs) {
        const tr = r + dr, tc = c + dc;
        if (red && tr < 5) continue; // 不能过河
        if (!red && tr > 4) continue;
        if (inBoard(tr, tc) && !board[r + er][c + ec]) add(tr, tc);
      }
    } else if (type === 'N') { // 马：日字格，有蹩马腿
      const dirs = [
        [-2, -1, -1, 0], [-2, 1, -1, 0],
        [2, -1, 1, 0], [2, 1, 1, 0],
        [-1, -2, 0, -1], [1, -2, 0, -1],
        [-1, 2, 0, 1], [1, 2, 0, 1]
      ];
      for (const [dr, dc, br, bc] of dirs) {
        const tr = r + dr, tc = c + dc;
        if (inBoard(tr, tc) && !board[r + br][c + bc]) add(tr, tc);
      }
    } else if (type === 'R') { // 车：直线滑行
      const dirs = [[0, 1], [0, -1], [1, 0], [-1, 0]];
      for (const [dr, dc] of dirs) {
        let tr = r + dr, tc = c + dc;
        while (inBoard(tr, tc)) {
          const target = board[tr][tc];
          if (!target) {
            add(tr, tc);
          } else {
            if (!sameColor(p, target)) add(tr, tc);
            break;
          }
          tr += dr; tc += dc;
        }
      }
    } else if (type === 'C') { // 炮：隔一子打一子
      const dirs = [[0, 1], [0, -1], [1, 0], [-1, 0]];
      for (const [dr, dc] of dirs) {
        let tr = r + dr, tc = c + dc;
        let jumped = false;
        while (inBoard(tr, tc)) {
          const target = board[tr][tc];
          if (!jumped) {
            if (!target) add(tr, tc);
            else jumped = true;
          } else {
            if (target) {
              if (!sameColor(p, target)) add(tr, tc);
              break;
            }
          }
          tr += dr; tc += dc;
        }
      }
    } else if (type === 'P') { // 兵/卒：过河前只能向前，过河后可左右
      const fwd = red ? -1 : 1;
      add(r + fwd, c);
      const crossed = red ? (r <= 4) : (r >= 5);
      if (crossed) {
        add(r, c - 1);
        add(r, c + 1);
      }
    }

    return moves;
  }

  // 获取某方所有的合法走法
  function getAllMoves(board, forRed) {
    const res = [];
    for (let r = 0; r < 10; r++) {
      for (let c = 0; c < 9; c++) {
        const p = board[r][c];
        if (p && (forRed ? isRed(p) : isBlack(p))) {
          res.push(...getMoves(board, r, c));
        }
      }
    }
    return res;
  }

  function applyMove(board, move) {
    const [fr, fc] = move.from;
    const [tr, tc] = move.to;
    const next = board.map(row => row.slice());
    next[tr][tc] = next[fr][fc];
    next[fr][fc] = null;
    return next;
  }

  // 评估局面分数 (从黑方视角，黑方为正，红方为负)
  function evaluate(board) {
    let score = 0;
    for (let r = 0; r < 10; r++) {
      for (let c = 0; c < 9; c++) {
        const p = board[r][c];
        if (!p) continue;
        const v = PIECE_VALUES[p] || 0;
        if (isBlack(p)) score += v;
        else score -= v;
      }
    }
    return score;
  }

  // ---------- 神经网络价值评估 (xiangqi_nn.bin) ----------
  let nnModel = null;
  const PIECES_LIST = ['K', 'A', 'B', 'N', 'R', 'C', 'P', 'k', 'a', 'b', 'n', 'r', 'c', 'p'];
  const P2IDX = {};
  PIECES_LIST.forEach((p, i) => { P2IDX[p] = i; });

  function parseNN(buf) {
    const magic = String.fromCharCode(...new Uint8Array(buf, 0, 4));
    if (magic !== 'XQNN') throw new Error('无效的象棋模型文件');
    let off = 4;
    function readF32(len) {
      const arr = new Float32Array(buf, off, len);
      off += len * 4;
      return arr;
    }
    // w1: [256, 1261], b1: [256], w2: [128, 256], b2: [128], w3: [1, 128], b3: [1]
    const w1 = readF32(256 * 1261);
    const b1 = readF32(256);
    const w2 = readF32(128 * 256);
    const b2 = readF32(128);
    const w3 = readF32(1 * 128);
    const b3 = readF32(1);
    return { w1, b1, w2, b2, w3, b3 };
  }

  async function loadNN(url = 'xiangqi_nn.bin') {
    try {
      const res = await fetch(url);
      if (!res.ok) return null;
      const buf = await res.arrayBuffer();
      nnModel = parseNN(buf);
      return nnModel;
    } catch(e) {
      return null;
    }
  }

  function evaluateNN(board, isRedTurn) {
    if (!nnModel) return evaluate(board);
    // 构造 1261 维特征
    const h1 = new Float32Array(256);
    for (let i = 0; i < 256; i++) h1[i] = nnModel.b1[i];

    let featIdx = 0;
    for (let r = 0; r < 10; r++) {
      for (let c = 0; c < 9; c++) {
        const p = board[r][c];
        if (p && P2IDX[p] !== undefined) {
          const pIdx = featIdx + P2IDX[p];
          for (let i = 0; i < 256; i++) {
            h1[i] += nnModel.w1[i * 1261 + pIdx];
          }
        }
        featIdx += 14;
      }
    }
    if (isRedTurn) {
      for (let i = 0; i < 256; i++) h1[i] += nnModel.w1[i * 1261 + 1260];
    }
    // ReLU
    for (let i = 0; i < 256; i++) if (h1[i] < 0) h1[i] = 0;

    // Layer 2
    const h2 = new Float32Array(128);
    for (let i = 0; i < 128; i++) {
      let sum = nnModel.b2[i];
      for (let j = 0; j < 256; j++) sum += h1[j] * nnModel.w2[i * 256 + j];
      h2[i] = sum > 0 ? sum : 0;
    }

    // Output
    let out = nnModel.b3[0];
    for (let j = 0; j < 128; j++) out += h2[j] * nnModel.w3[j];
    const val = Math.tanh(out);
    // 从黑方视角返回分值 (黑方越有利分越高)
    return -val * 1000;
  }

  // 简单/中等/大师 AI 搜索
  function search(board, depth, alpha, beta, isBlackTurn, useNN = false) {
    if (depth === 0) return { score: useNN ? evaluateNN(board, !isBlackTurn) : evaluate(board) };

    const moves = getAllMoves(board, !isBlackTurn);
    if (!moves.length) {
      return { score: isBlackTurn ? -99999 : 99999 };
    }

    // 优先搜索吃子走法
    moves.sort((a, b) => (b.captured ? PIECE_VALUES[b.captured] || 0 : 0) - (a.captured ? PIECE_VALUES[a.captured] || 0 : 0));

    let bestMove = moves[0];
    if (isBlackTurn) { // Maximize
      let maxEval = -Infinity;
      for (const m of moves) {
        if (m.captured && m.captured.toUpperCase() === 'K') return { score: 99999, move: m };
        const next = applyMove(board, m);
        const ev = search(next, depth - 1, alpha, beta, false, useNN).score;
        if (ev > maxEval) {
          maxEval = ev;
          bestMove = m;
        }
        alpha = Math.max(alpha, ev);
        if (beta <= alpha) break;
      }
      return { score: maxEval, move: bestMove };
    } else { // Minimize
      let minEval = Infinity;
      for (const m of moves) {
        if (m.captured && m.captured.toUpperCase() === 'K') return { score: -99999, move: m };
        const next = applyMove(board, m);
        const ev = search(next, depth - 1, alpha, beta, true, useNN).score;
        if (ev < minEval) {
          minEval = ev;
          bestMove = m;
        }
        beta = Math.min(beta, ev);
        if (beta <= alpha) break;
      }
      return { score: minEval, move: bestMove };
    }
  }

  function aiPlay(board, level = 3) {
    const useNN = (level === 3);
    const depth = level >= 2 ? 3 : 2;
    const res = search(board, depth, -Infinity, Infinity, true, useNN);
    return res.move;
  }

  return {
    initBoard,
    isRed,
    isBlack,
    getMoves,
    getAllMoves,
    applyMove,
    evaluate,
    evaluateNN,
    loadNN,
    aiPlay,
    PIECE_NAMES
  };
});
