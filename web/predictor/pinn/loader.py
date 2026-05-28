import logging
import pickle
import torch
from django.conf import settings

from predictor.pinn.model import PINNModal_v4

logger = logging.getLogger(__name__)

_model = None
_SC = None
_device = None


def get_model_and_scalers():
    global _model, _SC, _device
    if _model is None:
        logger.info('Loading PINN model from %s', settings.MODEL_PATH)
        _device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        with open(settings.SCALERS_PATH, 'rb') as f:
            _SC = pickle.load(f)
        _model = PINNModal_v4().to(_device)
        sd = torch.load(settings.MODEL_PATH, map_location=_device, weights_only=True)
        _model.load_state_dict(sd, strict=True)
        _model.eval()
        n_params = sum(p.numel() for p in _model.parameters())
        logger.info('PINN model ready: %s params on %s', f'{n_params:,}', _device)
    return _model, _SC, _device
