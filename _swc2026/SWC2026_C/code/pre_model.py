
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P2 预训练判决实验 —— 编码器骨架与三个头。

骨架：因果无关的膨胀 TCN（对输入窗内双向可见，窗口外无任何信息），
      4 个残差块，通道 64，dilation (1,2,4,8)，每块 2 个 k=3 卷积，感受野 61 帧
      （1 + 4*(1+2+4+8)）。
      编码器参数 105600 (< 300k 上限)。

三个头：
  Predictor   —— C0 / C3 共用：最后帧特征 -> MLP -> L*3
  MaskedRecon —— 自监督 (a)：逐帧特征 -> 133 维（21*2 关键点 + 头部位姿）
  Contrastive —— 自监督 (b)：窗级嵌入 -> InfoNCE
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class TCNBlock(nn.Module):
    def __init__(self, ch, dil, p=0.10):
        super().__init__()
        self.c1 = nn.Conv1d(ch, ch, 3, padding=dil, dilation=dil)
        self.c2 = nn.Conv1d(ch, ch, 3, padding=dil, dilation=dil)
        self.n1 = nn.GroupNorm(8, ch)
        self.n2 = nn.GroupNorm(8, ch)
        self.drop = nn.Dropout(p)

    def forward(self, x):
        h = F.gelu(self.n1(self.c1(x)))
        h = self.drop(h)
        h = self.n2(self.c2(h))
        h = self.drop(h)
        return F.gelu(x + h)


class Encoder(nn.Module):
    def __init__(self, in_dim=87, ch=64, dilations=(1, 2, 4, 8), p=0.10):
        super().__init__()
        self.inp = nn.Conv1d(in_dim, ch, 1)
        self.blocks = nn.ModuleList([TCNBlock(ch, d, p) for d in dilations])
        self.norm = nn.LayerNorm(ch)

    def forward(self, x):
        # x: (B,T,in) -> (B,T,ch)
        h = self.inp(x.transpose(1, 2))
        for b in self.blocks:
            h = b(h)
        return self.norm(h.transpose(1, 2))


def n_params(m):
    return int(sum(p.numel() for p in m.parameters() if p.requires_grad))


class Predictor(nn.Module):
    def __init__(self, L, enc=None, ch=64, hid=128, p=0.10):
        super().__init__()
        self.enc = enc if enc is not None else Encoder()
        self.head = nn.Sequential(
            nn.LayerNorm(ch), nn.Linear(ch, hid), nn.GELU(), nn.Dropout(p),
            nn.Linear(hid, L * 3))
        self.L = L

    def forward(self, x):
        h = self.enc(x)[:, -1]
        return self.head(h).view(-1, self.L, 3)

    def features(self, x):
        """冻结探针用：最后帧 + 时间均值，128 维。"""
        h = self.enc(x)
        return torch.cat([h[:, -1], h.mean(1)], dim=-1)


class MaskedRecon(nn.Module):
    def __init__(self, enc, in_dim=87, out_dim=133, ch=64, hid=128):
        super().__init__()
        self.enc = enc
        self.mask = nn.Parameter(torch.zeros(in_dim))
        self.dec = nn.Sequential(nn.Linear(ch, hid), nn.GELU(), nn.Linear(hid, out_dim))

    def forward(self, x, mask):
        # x: (B,T,in) 已归一化；mask: (B,T) bool
        m = mask.unsqueeze(-1)
        h = torch.where(m, self.mask.view(1, 1, -1), x)
        return self.dec(self.enc(h))


class Contrastive(nn.Module):
    def __init__(self, enc, ch=64, proj=64):
        super().__init__()
        self.enc = enc
        self.proj = nn.Sequential(nn.Linear(2 * ch, 128), nn.GELU(), nn.Linear(128, proj))

    def forward(self, x):
        h = self.enc(x)
        z = torch.cat([h[:, -1], h.mean(1)], dim=-1)
        return F.normalize(self.proj(z), dim=-1)


def supcon_loss(z, labels, tau=0.10):
    """多正例 InfoNCE（同记录不同时间窗为正，其余为负）。"""
    sim = z @ z.t() / tau
    n = z.shape[0]
    eye = torch.eye(n, device=z.device, dtype=torch.bool)
    sim = sim.masked_fill(eye, -1e4)
    log_prob = sim - torch.logsumexp(sim, dim=1, keepdim=True)
    pos = (labels[:, None] == labels[None, :]) & ~eye
    npos = pos.sum(1).clamp(min=1)
    return -(log_prob.masked_fill(~pos, 0.0).sum(1) / npos).mean()