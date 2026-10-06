import numpy as np
from config import settings as S


def air_density(pressure_hpa, temp_c):
    """Densidad real del aire: rho = P / (R * T)."""
    return (np.asarray(pressure_hpa) * 100.0) / (S.R_AIRE * (np.asarray(temp_c) + 273.15))


def wind_at_hub(v_ref):
    """Sube el viento de 10 m a la altura del buje (ley logarítmica)."""
    return np.asarray(v_ref) * np.log(S.HUB_HEIGHT / S.Z0) / np.log(S.Z_REF / S.Z0)


def rotor_area():
    return np.pi * (S.ROTOR_DIAMETER / 2.0) ** 2


def turbine_power_kw(v, rho):
    """Potencia de UNA turbina en kW."""
    v = np.asarray(v, dtype=float)
    rho = np.asarray(rho, dtype=float)
    p = 0.5 * rho * rotor_area() * v**3 * S.CP / 1000.0   # zona cúbica
    p = np.minimum(p, S.RATED_KW)                          # tope: potencia nominal
    p = np.where(v < S.V_CUT_IN, 0.0, p)                   # muy poco viento
    p = np.where(v > S.V_CUT_OUT, 0.0, p)                  # demasiado viento: freno
    return p


def park_power_kw(v, rho):
    """Potencia de todo el parque: 41 turbinas."""
    return S.N_TURBINES * turbine_power_kw(v, rho)

