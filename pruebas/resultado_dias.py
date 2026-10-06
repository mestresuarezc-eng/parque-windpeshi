import csv
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.energy_balance import run_month  # noqa: E402

ANIO, MES = 2026, 10
N_CONTENEDORES = 8
DEMO = True   # False para usar clima real de Open-Meteo

m = run_month(ANIO, MES, demo=DEMO, n_contenedores=N_CONTENEDORES)

print("dia | excedente | guardado | vertido | % guardado | entregado | SOC fin")
filas = []
for i, dia in enumerate(m["dias"]):
    exc = m["excedente_mwh"][i]
    alm = m["almacenado_mwh"][i]
    pct = round(100 * alm / exc, 1) if exc > 0 else ""
    fila = [dia, exc, alm, m["vertido_mwh"][i], pct,
            m["entregado_mwh"][i], m["soc_fin_mwh"][i]]
    filas.append(fila)
    print(*fila, sep=" | ")

t_exc = round(sum(m["excedente_mwh"]), 1)
t_alm = round(sum(m["almacenado_mwh"]), 1)
t_ver = round(sum(m["vertido_mwh"]), 1)
t_ent = round(sum(m["entregado_mwh"]), 1)
t_pct = round(100 * t_alm / t_exc, 1) if t_exc > 0 else ""
filas.append(["TOTAL", t_exc, t_alm, t_ver, t_pct, t_ent, ""])
print(f"\nTOTAL: excedente {t_exc} | guardado {t_alm} | vertido {t_ver} | {t_pct} % guardado")

salida = Path(__file__).resolve().parent / "resultado_dias.csv"
with open(salida, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["dia", "excedente_MWh", "guardado_MWh", "vertido_MWh",
                "pct_guardado", "entregado_MWh", "soc_fin_MWh"])
    w.writerows(filas)

print(f"Tabla guardada en: {salida}")