import logging
import pickle
import torch
from django.conf import settings

from predictor.pinn.model import PINNModal_v4

logger = logging.getLogger(__name__)

# Caché a nivel de proceso (cada worker de gunicorn tiene la suya)
_model    = None
_SC       = None
_device   = None
_firma    = None   # identifica qué carga está en caché


def _calcular_firma():
    """
    Devuelve una cadena que identifica de forma única el par modelo/scalers
    actualmente configurado. Cambia cuando:
      - Se activa un registro diferente en el admin (pk + timestamp).
      - No hay registro activo y el archivo en disco fue modificado (mtime).
    """
    try:
        from predictor.models import ModeloPINN
        activo = ModeloPINN.get_activo()
        if activo is not None:
            return f'db:{activo.pk}:{activo.actualizado.isoformat()}'
    except Exception:
        pass  # DB no disponible (ej. durante collectstatic)

    # Fallback a mtime de los archivos
    import os
    try:
        mt_m = os.path.getmtime(settings.MODEL_PATH)
        mt_s = os.path.getmtime(settings.SCALERS_PATH)
        return f'fs:{mt_m}:{mt_s}'
    except OSError:
        return 'fs:unknown'


def _resolver_paths():
    """
    Devuelve (model_path, scalers_path) según el registro activo en la DB
    o, si no existe, los paths de settings (fallback).
    """
    try:
        from predictor.models import ModeloPINN
        activo = ModeloPINN.get_activo()
        if activo is not None:
            return activo.archivo_modelo.path, activo.archivo_scalers.path
    except Exception:
        pass
    return str(settings.MODEL_PATH), str(settings.SCALERS_PATH)


def get_model_and_scalers():
    """
    Devuelve (model, SC, device).

    Recarga automáticamente si el registro activo en el admin cambió
    (invalidación de caché por firma), sin necesidad de reiniciar gunicorn.
    """
    global _model, _SC, _device, _firma

    firma_actual = _calcular_firma()
    if _model is not None and firma_actual == _firma:
        return _model, _SC, _device

    model_path, scalers_path = _resolver_paths()
    logger.info('Cargando modelo PINN desde %s', model_path)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    with open(scalers_path, 'rb') as f:
        SC = pickle.load(f)
    model = PINNModal_v4().to(device)
    sd = torch.load(model_path, map_location=device, weights_only=True)
    model.load_state_dict(sd, strict=True)
    model.eval()

    n_params = sum(p.numel() for p in model.parameters())
    logger.info('Modelo PINN listo: %s parámetros en %s', f'{n_params:,}', device)

    _model  = model
    _SC     = SC
    _device = device
    _firma  = firma_actual
    return _model, _SC, _device
