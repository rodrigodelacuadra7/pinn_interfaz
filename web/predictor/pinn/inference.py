import numpy as np
import torch

from predictor.pinn.domain import validar_dominio
from predictor.pinn.features import construir_X


def predict_edificio(params, model, SC, device):
    """Predicción completa de un edificio. Devuelve un dict estructurado."""
    avisos, grave = validar_dominio(params)

    COLS_BASE = SC['COLS_BASE']
    x_raw, mask = construir_X(params, COLS_BASE)

    X = torch.from_numpy(((x_raw - SC['X_mean']) / SC['X_std']).astype(np.float32))
    X = X.unsqueeze(0).to(device)
    msk = torch.from_numpy(mask).unsqueeze(0).to(device)

    with torch.no_grad():
        logT, Phi_x, Phi_y, Phi_t, Ux, Uy, dx, dy, Vb, ratio = model(X, msk)

    Np = int(params['N_pisos'])
    T    = np.exp(logT[0].cpu().numpy() * SC['logT_std'] + SC['logT_mean'])
    Ux_r = np.exp(Ux[0, :Np].cpu().numpy() * SC['Ux_std'] + SC['Ux_mean'])
    Uy_r = np.exp(Uy[0, :Np].cpu().numpy() * SC['Uy_std'] + SC['Uy_mean'])
    dx_r = np.exp(dx[0, :Np].cpu().numpy() * SC['Dx_std'] + SC['Dx_mean'])
    dy_r = np.exp(dy[0, :Np].cpu().numpy() * SC['Dy_std'] + SC['Dy_mean'])
    Vbx  = float(np.exp(Vb[0, 0].item() * SC['Vbx_std'] + SC['Vbx_mean']))
    Vby  = float(np.exp(Vb[0, 1].item() * SC['Vby_std'] + SC['Vby_mean']))

    n_mod_lado  = params['n_unid_lado'] * 2
    n_mod_total = 2 * (n_mod_lado + 1)
    Lx = round(n_mod_total * params['L_mod_m'], 2)
    prof_sup = round(params['prof_depto_m'] + params['ancho_corredor_m'], 2)
    prof_inf = round(params['prof_depto_m'] * 0.7 + params['ancho_corredor_m'], 2)
    Ly = round(prof_sup + prof_inf, 2)
    H  = Np * params['h_story_m']

    return dict(
        params       = params,
        avisos       = avisos,
        extrapolando = grave,
        geometria    = dict(Lx=Lx, Ly=Ly, H=H),
        modal        = dict(
            T        = T,
            Phi_x    = Phi_x[0, :Np].cpu().numpy(),
            Phi_y    = Phi_y[0, :Np].cpu().numpy(),
            Phi_theta= Phi_t[0, :Np].cpu().numpy(),
        ),
        respuesta    = dict(
            Ux_por_piso = Ux_r,
            Uy_por_piso = Uy_r,
            dx_por_piso = dx_r,
            dy_por_piso = dy_r,
            Vb_x        = Vbx,
            Vb_y        = Vby,
        ),
    )
