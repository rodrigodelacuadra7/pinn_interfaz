import torch
import torch.nn as nn
import torch.nn.functional as F


class ResBlock(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim), nn.LayerNorm(dim), nn.SiLU(),
            nn.Linear(dim, dim), nn.LayerNorm(dim))
        self.act = nn.SiLU()

    def forward(self, x):
        return self.act(x + self.net(x))


class PINNModal_v4(nn.Module):
    def __init__(self, n_inputs=21, n_modos=18, n_max_pisos=18, hidden=256, hidden_T1=128):
        super().__init__()
        self.n_modos = n_modos
        self.n_max_pisos = n_max_pisos

        self.encoder_T1 = nn.Sequential(
            nn.Linear(n_inputs, hidden_T1), nn.LayerNorm(hidden_T1), nn.SiLU(),
            ResBlock(hidden_T1), ResBlock(hidden_T1))
        self.head_T1 = nn.Sequential(nn.Linear(hidden_T1, 32), nn.SiLU(), nn.Linear(32, 1))

        self.encoder = nn.Sequential(
            nn.Linear(n_inputs, hidden), nn.LayerNorm(hidden), nn.SiLU(),
            ResBlock(hidden), ResBlock(hidden), ResBlock(hidden), ResBlock(hidden))
        self.head_T_rest = nn.Sequential(nn.Linear(hidden, 128), nn.SiLU(),
                                         nn.Linear(128, n_modos - 1))
        self.head_Phi = nn.Sequential(nn.Linear(hidden, 512), nn.SiLU(),
                                      nn.Linear(512, n_modos * n_max_pisos * 3))
        self.head_resp = nn.Sequential(nn.Linear(hidden, 256), nn.SiLU(),
                                       nn.Linear(256, n_max_pisos * 4))
        self.head_Vb = nn.Sequential(nn.Linear(hidden, 64), nn.SiLU(), nn.Linear(64, 2))

    def forward(self, X, mask):
        B = X.shape[0]
        h_T1 = self.encoder_T1(X)
        T1_out = self.head_T1(h_T1)
        h = self.encoder(X)
        T_deltas = F.softplus(self.head_T_rest(h))
        T_parts = [T1_out]
        for r in range(self.n_modos - 1):
            T_parts.append(T_parts[-1] - T_deltas[:, r:r + 1])
        logT_pred = torch.cat(T_parts, dim=1)

        Phi_raw = self.head_Phi(h).view(B, self.n_modos, self.n_max_pisos, 3)
        mask_4d = mask.unsqueeze(1).unsqueeze(-1)
        Phi_raw = Phi_raw * mask_4d
        norma = Phi_raw.norm(dim=2, keepdim=True).clamp(min=1e-8)
        Phi_norm = Phi_raw / norma
        Phi_all = Phi_norm.permute(0, 2, 1, 3)
        Phi_x_p, Phi_y_p, Phi_t_p = Phi_all[..., 0], Phi_all[..., 1], Phi_all[..., 2]

        resp = self.head_resp(h).view(B, self.n_max_pisos, 4)
        Ux_p = resp[..., 0] * mask
        Uy_p = resp[..., 1] * mask
        ratio_p = F.softplus(resp[..., 2]) * mask
        dy_p = resp[..., 3] * mask
        dx_p = ratio_p * dy_p
        Vb_p = self.head_Vb(h)

        return logT_pred, Phi_x_p, Phi_y_p, Phi_t_p, Ux_p, Uy_p, dx_p, dy_p, Vb_p, ratio_p
