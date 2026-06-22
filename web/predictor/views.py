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
from predictor.pinn.sugerencias import sugerir_modificaciones

_FLOAT_CHOICE_FIELDS = {'gk_kN_m2', 'h_story_m', 't_muro_nucleo_m', 't_muro_borde_m', 't_muro_mid_m'}


def _default_params():
    params = dict(DEFAULTS_SIMPLE)
    params.update(N_pisos=8, n_unid_lado=3, fc_MPa=30, suelo='C', zona=2)
    return params


def _parse_and_validate(request):
    """
    Parsea el body JSON, normaliza campos float-choice y valida con EdificioForm.
    Devuelve (params_dict, None) en éxito o (None, JsonResponse_de_error) en fallo.
    """
    try:
        raw = json.loads(request.body)
    except json.JSONDecodeError:
        return None, JsonResponse({'error': 'JSON inválido'}, status=400)

    body = {k: v for k, v in raw.items() if not k.startswith('_')}

    # JSON serializa 7.0 como 7 (int). Normalizar antes de validar choices.
    body = {k: (float(v) if k in _FLOAT_CHOICE_FIELDS and isinstance(v, int) else v)
            for k, v in body.items()}

    form = EdificioForm(body)
    if not form.is_valid():
        return None, JsonResponse({'error': form.errors}, status=400)

    params = {k: v for k, v in form.cleaned_data.items() if not k.startswith('_')}
    return params, None


def _get_real_geometry(params: dict) -> dict:
    """Extrae geometría real del edificio usando familia_B_core."""
    from predictor.pinn.derived import enrich_params
    from familia_B_core import build_family_B_geometry
    enriched = enrich_params(params)
    geom = build_family_B_geometry(enriched)
    walls = [
        {
            'cx':    w['x'] + w['w'] / 2,
            'cy':    w['y'] + w['h'] / 2,
            'w':     w['w'],
            'h':     w['h'],
            'group': w.get('group', 'B3'),
        }
        for w in geom['walls']
    ]
    cor = geom['corridor']
    return {
        'walls':    walls,
        'corridor': {'x': cor['x'], 'y': cor['y'], 'w': cor['w'], 'h': cor['h']},
    }


def index(request):
    defaults = _default_params()
    return render(request, 'predictor/index.html', {'defaults': defaults})


@require_http_methods(['POST'])
def api_predict(request):
    params, err = _parse_and_validate(request)
    if err:
        return err

    try:
        model, SC, device = get_model_and_scalers()
        res          = predict_edificio(params, model, SC, device)
        rep          = reporte_normativo(res)
        sugerencias  = sugerir_modificaciones(res, rep, params)
        T1           = float(res['modal']['T'][0])
        spectrum     = espectro_nch433(params['zona'], params['suelo'], T_star=T1)
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)

    try:
        geom_real = _get_real_geometry(params)
    except Exception:
        geom_real = {'walls': [], 'corridor': {}}

    payload = {
        'params':       params,
        'avisos':       res['avisos'],
        'extrapolando': res['extrapolando'],
        'geometria':    res['geometria'],
        'geometria_real': geom_real,
        'modal': {
            'T':         res['modal']['T'].tolist(),
            'Phi_x':     res['modal']['Phi_x'].tolist(),
            'Phi_y':     res['modal']['Phi_y'].tolist(),
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
        'normativa':    rep,
        'spectrum':     spectrum,
        'sugerencias':  sugerencias,
    }
    return JsonResponse(payload)
