from datetime import date

import numpy as np

from config import settings as S


def industrial_demand_kw(power_kw=20000.0, hours=18, start_hour=6):
    """Demanda de una planta industrial: consume `power_kw` durante `hours`
    horas seguidas, empezando a `start_hour`. El resto del día no consume."""
    demanda = np.zeros(24)
    for i in range(hours):
        demanda[(start_hour + i) % 24] = power_kw
    return demanda


def guajira_demand_kw(year=None):
    """Demanda de 24 horas de toda La Guajira = promedio del AÑO PASADO.
    (El parámetro `year` se ignora; queda solo para no romper el resto del código.)"""
    anio = date.today().year - 1                 # año pasado (en 2026 -> 2025)
    if anio not in S.CONSUMO_GUAJIRA:
        anio = max(S.CONSUMO_GUAJIRA)            # sin dato: usa el año más reciente
    gwh, horas = S.CONSUMO_GUAJIRA[anio]
    potencia_media_kw = gwh * 1_000_000 / horas  # GWh -> kWh, luego / horas = kW
    return np.full(24, potencia_media_kw)
