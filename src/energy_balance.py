import calendar
from datetime import date as _date, timedelta

import numpy as np
import pandas as pd
import requests

from config import settings as S

# ---------- Demanda ----------
# Fraccion de la demanda de La Guajira contra la que se compara el parque.
# Ajustala: si con 0 contenedores el vertido sale 0, bajala; si sale enorme, subela.
FRACCION_DEMANDA = 0.4

# ---------- BESS (contenedor Microgrid) ----------
BESS_POT_MW = 5      # por contenedor
BESS_CAP_MWH = 10    # por contenedor
BESS_EFF = 0.88      # eficiencia de ida y vuelta
BESS_SOC_MIN = 0.10
BESS_SOC_MAX = 0.90
BESS_SOC_INI = 0.10  # arranca casi vacia para no regalar energia


def evaluar_dia(df, kpi):
    """Decide si el dia es FUNCIONAL, PARCIAL o NO FUNCIONAL."""
    horas_utiles = int((df["p_generada_kw"] > 0).sum())
    horas_nominal = int((df["p_generada_kw"] >= S.N_TURBINES * S.RATED_KW * 0.999).sum())
    cobertura = kpi["cobertura_pct"]

    if cobertura >= S.UMBRAL_FUNCIONAL_PCT and horas_utiles >= S.HORAS_UTILES_MIN:
        veredicto = "FUNCIONAL"
    elif cobertura >= S.UMBRAL_PARCIAL_PCT:
        veredicto = "PARCIAL"
    else:
        veredicto = "NO FUNCIONAL"

    motivo = (f"Cobertura {cobertura:.1f} % (funcional desde {S.UMBRAL_FUNCIONAL_PCT:.0f} %) "
              f"y {horas_utiles} h con generacion (minimo {S.HORAS_UTILES_MIN} h).")

    return {
        "veredicto": veredicto,
        "motivo": motivo,
        "cobertura_pct": round(cobertura, 1),
        "horas_utiles": horas_utiles,
        "horas_nominal": horas_nominal,
        "viento_medio": round(kpi["viento_hub_medio"], 2),
        "factor_capacidad_pct": round(kpi["factor_capacidad_pct"], 1),
        "deficit_mwh": round(kpi["deficit_MWh"], 1),
    }


def _viento_demo(dia):
    """Viento de demostracion a 10 m para un dia (24 valores), repetible por fecha."""
    rng = np.random.default_rng(int(dia.strftime("%Y%m%d")))
    factor_dia = rng.uniform(0.6, 1.3)  # dias flojos y dias buenos
    h = np.arange(24)
    v = (5.5 + 1.8 * np.sin((h - 9) / 24 * 2 * np.pi)) * factor_dia + rng.normal(0, 0.8, 24)
    return np.clip(v, 0, None)


def _clima(inicio, fin, demo=False):
    """Clima por hora entre dos fechas (date). Con demo=True no usa internet."""
    horas = pd.date_range(pd.Timestamp(inicio), pd.Timestamp(fin) + pd.Timedelta(days=1),
                          freq="h", inclusive="left")
    if demo:
        viento = np.concatenate([_viento_demo(d) for d in pd.date_range(inicio, fin)])
        return pd.DataFrame({"hora": horas, "viento_10m": viento,
                             "temp_c": 28.0, "presion_hpa": 1010.0})

    if fin < _date.today() - timedelta(days=7):
        url = "https://archive-api.open-meteo.com/v1/archive"
    else:
        url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": S.LATITUDE, "longitude": S.LONGITUDE, "timezone": S.TIMEZONE,
        "start_date": inicio.isoformat(), "end_date": fin.isoformat(),
        "hourly": "wind_speed_10m,temperature_2m,surface_pressure",
        "wind_speed_unit": "ms",
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    h = r.json()["hourly"]
    df = pd.DataFrame({"hora": pd.to_datetime(h["time"]),
                       "viento_10m": h["wind_speed_10m"],
                       "temp_c": h["temperature_2m"],
                       "presion_hpa": h["surface_pressure"]}).dropna()
    if df.empty:
        raise ValueError("Open-Meteo no devolvio datos para esas fechas")
    return df


def _demanda_kw(anio):
    """Demanda promedio (kW) de La Guajira para ese anio, por la fraccion elegida."""
    completos = [a for a, (_, horas) in S.CONSUMO_GUAJIRA.items() if horas >= 8760]
    if anio not in S.CONSUMO_GUAJIRA:
        anio = max(completos)
    gwh, horas = S.CONSUMO_GUAJIRA[anio]
    return gwh * 1e6 / horas * FRACCION_DEMANDA


def _calcular(clima):
    """Agrega viento a la altura del buje, generacion y demanda."""
    df = clima.copy()
    df["viento_hub"] = df["viento_10m"] * np.log(S.HUB_HEIGHT / S.Z0) / np.log(S.Z_REF / S.Z0)
    rho = df["presion_hpa"] * 100 / (S.R_AIRE * (df["temp_c"] + 273.15))
    area = np.pi * (S.ROTOR_DIAMETER / 2) ** 2
    p_turbina = (0.5 * rho * area * S.CP * df["viento_hub"] ** 3 / 1000).clip(upper=S.RATED_KW)
    fuera = (df["viento_hub"] < S.V_CUT_IN) | (df["viento_hub"] >= S.V_CUT_OUT)
    p_turbina = np.where(fuera, 0.0, p_turbina)

    df["p_generada_kw"] = p_turbina * S.N_TURBINES
    df["p_demanda_kw"] = _demanda_kw(int(df["hora"].iloc[0].year))
    return df


def _aplicar_bess(df, n_contenedores=0):
    """Simula el BESS hora a hora. Con n_contenedores=0 no hay bateria.

    Agrega al df (todo en MWh por hora): bess_carga_mwh, bess_descarga_mwh,
    bess_soc_mwh, vertido_mwh y deficit_mwh.
    """
    df = df.copy()
    gen = df["p_generada_kw"].to_numpy() / 1000   # kW durante 1 h -> MWh
    dem = df["p_demanda_kw"].to_numpy() / 1000
    n = len(df)

    cap = BESS_CAP_MWH * n_contenedores
    pot = BESS_POT_MW * n_contenedores
    eta = BESS_EFF ** 0.5                          # eficiencia por sentido
    soc = BESS_SOC_INI * cap                       # energia guardada (MWh)

    carga = np.zeros(n)
    descarga = np.zeros(n)
    vertido = np.zeros(n)
    deficit = np.zeros(n)
    soc_h = np.zeros(n)

    for i in range(n):
        exceso = gen[i] - dem[i]
        if exceso > 0:                             # sobra energia -> cargar
            c = max(min(exceso, pot, (BESS_SOC_MAX * cap - soc) / eta), 0.0)
            soc += c * eta
            carga[i] = c
            vertido[i] = exceso - c
        else:                                      # falta energia -> descargar
            d = max(min(-exceso, pot, (soc - BESS_SOC_MIN * cap) * eta), 0.0)
            soc -= d / eta
            descarga[i] = d
            deficit[i] = -exceso - d
        soc_h[i] = soc

    df["bess_carga_mwh"] = carga
    df["bess_descarga_mwh"] = descarga
    df["bess_soc_mwh"] = soc_h
    df["vertido_mwh"] = vertido
    df["deficit_mwh"] = deficit
    return df


def _kpi(df):
    gen = df["p_generada_kw"]
    dem = df["p_demanda_kw"]
    dem_mwh = dem.sum() / 1000

    if "deficit_mwh" in df:                        # ya paso por el BESS
        deficit_mwh = df["deficit_mwh"].sum()
        vertido_mwh = df["vertido_mwh"].sum()
        almacenado_mwh = df["bess_carga_mwh"].sum()
        descargado_mwh = df["bess_descarga_mwh"].sum()
    else:                                          # sin BESS (calculo original)
        deficit_mwh = (dem - gen).clip(lower=0).sum() / 1000
        vertido_mwh = (gen - dem).clip(lower=0).sum() / 1000
        almacenado_mwh = 0.0
        descargado_mwh = 0.0

    return {
        "generada_MWh": gen.sum() / 1000,
        "demanda_MWh": dem_mwh,
        "deficit_MWh": deficit_mwh,
        "vertido_MWh": vertido_mwh,
        "almacenado_MWh": almacenado_mwh,
        "descargado_MWh": descargado_mwh,
        "cobertura_pct": 100 * (1 - deficit_mwh / dem_mwh),
        "viento_hub_medio": df["viento_hub"].mean(),
        "factor_capacidad_pct": 100 * gen.sum() / (S.N_TURBINES * S.RATED_KW * len(df)),
    }


def run_balance(date, demo=False, n_contenedores=0):
    """date = 'AAAA-MM-DD'. Devuelve (df, k)."""
    dia = _date.fromisoformat(date)
    df = _aplicar_bess(_calcular(_clima(dia, dia, demo)), n_contenedores)
    return df, _kpi(df)


def run_month(year, month, demo=False, n_contenedores=0):
    ultimo = calendar.monthrange(year, month)[1]
    df = _calcular(_clima(_date(year, month, 1), _date(year, month, ultimo), demo))
    df = _aplicar_bess(df, n_contenedores)         # la bateria sigue cargada entre dias
    dias, gen, dem, vert, defi, cob, ver, soc_fin, ent, alm, exc = (
        [], [], [], [], [], [], [], [], [], [], [])
    for dia, g in df.groupby(df["hora"].dt.day):
        k = _kpi(g)
        ev = evaluar_dia(g, k)
        dias.append(int(dia))
        gen.append(round(k["generada_MWh"], 1))
        dem.append(round(k["demanda_MWh"], 1))
        vert.append(round(k["vertido_MWh"], 1))
        defi.append(round(k["deficit_MWh"], 1))
        cob.append(ev["cobertura_pct"])
        ver.append(ev["veredicto"])
        soc_fin.append(round(float(g["bess_soc_mwh"].iloc[-1]), 1))
        ent.append(round(k["descargado_MWh"], 1))
        alm.append(round(k["almacenado_MWh"], 1))
        # excedente del dia = lo que se guardo + lo que se vertio
        exc.append(round(k["almacenado_MWh"] + k["vertido_MWh"], 1))
    return {"dias": dias, "gen_mwh": gen, "dem_mwh": dem,
            "vertido_mwh": vert, "deficit_mwh": defi,
            "cobertura_pct": cob, "veredicto": ver, "soc_fin_mwh": soc_fin,
            "entregado_mwh": ent, "almacenado_mwh": alm, "excedente_mwh": exc,
            "n_contenedores": n_contenedores}
