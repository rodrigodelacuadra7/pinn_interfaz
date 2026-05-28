import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from predictor.forms import EdificioForm
from predictor.pinn.domain import DEFAULTS_SIMPLE
from predictor.pinn.inference import predict_edificio
from predictor.pinn.loader import get_model_and_scalers
from predictor.pinn.normativa import reporte_normativo
from predictor.pinn.spectrum import espectro_nch433


def _default_params():
    params = dict(DEFAULTS_SIMPLE)
    params.update(N_pisos=8, n_unid_lado=3, fc_MPa=30, suelo='C', zona=2)
    return params


def index(request):
    defaults = _default_params()
    return render(request, 'predictor/index.html', {'defaults': defaults})


@require_http_methods(['POST'])
def api_predict(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    form = EdificioForm(body)
    if not form.is_valid():
        return JsonResponse({'error': form.errors}, status=400)

    params = {k: v for k, v in form.cleaned_data.items() if not k.startswith('_')}

    try:
        model, SC, device = get_model_and_scalers()
        res = predict_edificio(params, model, SC, device)
        rep = reporte_normativo(res)
        spectrum = espectro_nch433(params['zona'], params['suelo'])
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)

    payload = {
        'params': params,
        'avisos': res['avisos'],
        'extrapolando': res['extrapolando'],
        'geometria': res['geometria'],
        'modal': {
            'T': res['modal']['T'].tolist(),
            'Phi_x': res['modal']['Phi_x'].tolist(),
            'Phi_y': res['modal']['Phi_y'].tolist(),
            'Phi_theta': res['modal']['Phi_theta'].tolist(),
        },
        'respuesta': {
            'Ux_por_piso': res['respuesta']['Ux_por_piso'].tolist(),
            'Uy_por_piso': res['respuesta']['Uy_por_piso'].tolist(),
            'dx_por_piso': res['respuesta']['dx_por_piso'].tolist(),
            'dy_por_piso': res['respuesta']['dy_por_piso'].tolist(),
            'Vb_x': res['respuesta']['Vb_x'],
            'Vb_y': res['respuesta']['Vb_y'],
        },
        'normativa': rep,
        'spectrum': spectrum,
    }
    return JsonResponse(payload)
