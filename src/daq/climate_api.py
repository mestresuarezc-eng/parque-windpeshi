import json
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from config import settings as S

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"
VARIABLES = "temperature_2m,surface_pressure,wind_speed_10m,shortwave_radiation"


def _descargar(dia):
    """Pide a Open-Meteo el clima de un día (YYYY-MM-DD)."""
    d = datetime.strptime(dia, "%Y-%m-%d").date()
    if d < date.today() - timedelta(days=5):
        url = "https://archive-api.open-meteo.com/v1/archive"   # días antiguos
    else:
        url = "https://api.open-meteo.com/v1/forecast"          # días recientes
    params = {
        "latitude": S.LATITUDE,
        "longitude": S.LONGITUDE,
        "start_date": dia,
        "end_date": dia,
        "hourly": VARIABLES,
        "wind_speed_unit": "ms",
        "timezone": S.TIMEZONE,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def _dia_de_ejemplo(dia):
    """Datos inventados para probar sin internet."""
    h = np.arange(24)
    return {"hourly": {
        "time": [f"{dia}T{x:02d}:00" for x in h],
        "temperature_2m": (28 + 5 * np.sin((h - 9) / 24 * 2 * np.pi)).tolist(),
        "surface_pressure": [1008.0] * 24,
        "wind_speed_10m": (7.5 + 2.5 * np.sin((h - 8) / 24 * 2 * np.pi)).tolist(),
        "shortwave_radiation": np.clip(900 * np.sin((h - 6) / 12 * np.pi), 0, None).tolist(),
    }}


def get_climate_day(dia, demo=False):
    """Devuelve una tabla de 24 filas con el clima de ese día."""
    if demo:
        data = _dia_de_ejemplo(dia)
    else:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        archivo = CACHE_DIR / f"climate_uribia_{dia}.json"
        if archivo.exists():
            data = json.loads(archivo.read_text(encoding="utf-8"))
        else:
            data = _descargar(dia)
            archivo.write_text(json.dumps(data), encoding="utf-8")

    h = data["hourly"]
    return pd.DataFrame({
        "hora": pd.to_datetime(h["time"]),
        "temp_c": h["temperature_2m"],
        "presion_hpa": h["surface_pressure"],
        "viento_10m": h["wind_speed_10m"],
        "ghi": h["shortwave_radiation"],
    })


def get_climate_range(inicio, fin, demo=False):
    """Clima por hora de varios días en una sola petición. Fechas YYYY-MM-DD."""
    if demo:
        marcos = []
        for d in pd.date_range(inicio, fin):
            dia = d.strftime("%Y-%m-%d")
            h = _dia_de_ejemplo(dia)["hourly"]
            factor = 1 + 0.25 * np.sin(d.day)      # el viento cambia de un día a otro
            marcos.append(pd.DataFrame({
                "hora": pd.to_datetime(h["time"]),
                "temp_c": h["temperature_2m"],
                "presion_hpa": h["surface_pressure"],
                "viento_10m": [v * factor for v in h["wind_speed_10m"]],
                "ghi": h["shortwave_radiation"],
            }))
        return pd.concat(marcos, ignore_index=True)

    fin_d = datetime.strptime(fin, "%Y-%m-%d").date()
    antiguo = fin_d < date.today() - timedelta(days=5)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    archivo = CACHE_DIR / f"climate_uribia_{inicio}_{fin}.json"

    if antiguo and archivo.exists():
        data = json.loads(archivo.read_text(encoding="utf-8"))
    else:
        url = ("https://archive-api.open-meteo.com/v1/archive" if antiguo
               else "https://api.open-meteo.com/v1/forecast")
        params = {
            "latitude": S.LATITUDE,
            "longitude": S.LONGITUDE,
            "start_date": inicio,
            "end_date": fin,
            "hourly": VARIABLES,
            "wind_speed_unit": "ms",
            "timezone": S.TIMEZONE,
        }
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        if antiguo:
            archivo.write_text(json.dumps(data), encoding="utf-8")

    h = data["hourly"]
    df = pd.DataFrame({
        "hora": pd.to_datetime(h["time"]),
        "temp_c": h["temperature_2m"],
        "presion_hpa": h["surface_pressure"],
        "viento_10m": h["wind_speed_10m"],
        "ghi": h["shortwave_radiation"],
    })
    return df.dropna(subset=["temp_c", "presion_hpa", "viento_10m"]).reset_index(drop=True)
    