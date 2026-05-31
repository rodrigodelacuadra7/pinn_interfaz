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

_FLOAT_CHOICE_FIELDS = {'gk_kN_m2', 'h_story_m', 't_muro_nucleo_m', 't_muro_borde_m', 't_muro_mid_m'}


def _default_params():
    params = dict(DEFAULTS_SIMPLE)
    params.update(N_pisos=8, n_unid_lado=3, fc_MPa=30, suelo='C', zona=2)
    return params


def _parse_and_validate(request):
    """
    Parsea el body JSON, normaliza campos float-choice y valida con EdificioForm.
    Campos que empiezan con '_' se extraen antes de validar y se devuelven aparte.

    Devuelve (params_dict, extra_dict, None) en éxito
         o  (None, None, JsonResponse_de_error) en fallo.
    """
    try:
        raw = json.loads(request.body)
    except json.JSONDecodeError:
        return None, None, JsonResponse({'error': 'JSON inválido'}, status=400)

    # Separar campos auxiliares (_T1, _cumple, etc.) del resto
    extra = {k: v for k, v in raw.items() if k.startswith('_')}
    body  = {k: v for k, v in raw.items() if not k.startswith('_')}

    # JSON serializa 7.0 como 7 (int). Normalizar antes de validar choices.
    body = {k: (float(v) if k in _FLOAT_CHOICE_FIELDS and isinstance(v, int) else v)
            for k, v in body.items()}

    form = EdificioForm(body)
    if not form.is_valid():
        return None, None, JsonResponse({'error': form.errors}, status=400)

    params = {k: v for k, v in form.cleaned_data.items() if not k.startswith('_')}
    return params, extra, None


def index(request):
    defaults = _default_params()
    return render(request, 'predictor/index.html', {'defaults': defaults})


@require_http_methods(['POST'])
def api_predict(request):
    params, _extra, err = _parse_and_validate(request)
    if err:
        return err

    try:
        model, SC, device = get_model_and_scalers()
        res      = predict_edificio(params, model, SC, device)
        rep      = reporte_normativo(res)
        spectrum = espectro_nch433(params['zona'], params['suelo'])
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)

    payload = {
        'params':  params,
        'avisos':  res['avisos'],
        'extrapolando': res['extrapolando'],
        'geometria': res['geometria'],
        'modal': {
            'T':        res['modal']['T'].tolist(),
            'Phi_x':    res['modal']['Phi_x'].tolist(),
            'Phi_y':    res['modal']['Phi_y'].tolist(),
            'Phi_theta':res['modal']['Phi_theta'].tolist(),
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
        'spectrum':  spectrum,
    }
    return JsonResponse(payload)


@require_http_methods(['POST'])
def api_view_3d(request):
    params, extra, err = _parse_and_validate(request)
    if err:
        return err
    try:
        from predictor.pinn.visualizer_adapter import render_3d
        T1     = extra.get('_T1')
        cumple = extra.get('_cumple')
        html   = render_3d(params, cumple=cumple, T1=T1)
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)
    return JsonResponse({'html': html})


@require_http_methods(['POST'])
def api_view_planta(request):
    params, _extra, err = _parse_and_validate(request)
    if err:
        return err
    try:
        from predictor.pinn.visualizer_adapter import render_planta
        html = render_planta(params)
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)
    return JsonResponse({'html': html})
