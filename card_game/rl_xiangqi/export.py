"""
中国象棋模型导出工具：将 PyTorch 检查点转为浏览器端极速运行的 Float32/Float16 二进制文件
格式：'XQNN' + 3层权重的纯二进制流
"""

import os
import struct
import torch
import numpy as np

def export_to_bin(ckpt_path, out_bin="xiangqi_nn.bin"):
    state = torch.load(ckpt_path, map_location="cpu")
    # 提取 Linear 层权重和偏置
    # net.0 (1261 -> 256), net.2 (256 -> 128), net.4 (128 -> 1)
    w1 = state['net.0.weight'].numpy().astype(np.float32) # [256, 1261]
    b1 = state['net.0.bias'].numpy().astype(np.float32)   # [256]
    w2 = state['net.2.weight'].numpy().astype(np.float32) # [128, 256]
    b2 = state['net.2.bias'].numpy().astype(np.float32)   # [128]
    w3 = state['net.4.weight'].numpy().astype(np.float32) # [1, 128]
    b3 = state['net.4.bias'].numpy().astype(np.float32)   # [1]

    with open(out_bin, "wb") as f:
        f.write(b"XQNN")
        for arr in [w1, b1, w2, b2, w3, b3]:
            f.write(arr.tobytes())

    sz = os.path.getsize(out_bin) / 1024
    print(f"[*] 象棋神经网络已导出至: {out_bin} (大小: {sz:.1f} KB)")

if __name__ == "__main__":
    import sys
    ckpt = sys.argv[1] if len(sys.argv) > 1 else "ckpt_xiangqi/last.pt"
    out = sys.argv[2] if len(sys.argv) > 2 else "xiangqi_nn.bin"
    export_to_bin(ckpt, out)
