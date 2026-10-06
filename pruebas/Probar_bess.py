import csv
import sys
from pathlib import Path

# Para que encuentre src/ y config/ en la carpeta principal del proyecto
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.energy_balance import run_month  # noqa: E402

ANIO, MES = 2026, 10          # mes a simular
CONTENEDORES = [0, 1, 2, 3, 4, 5, 6, 7, 8]

filas = []
anterior = None

print("cont | vertido MWh | cobertura % | MWh evitados por contenedor extra")
for n in CONTENEDORES:
    m = run_month(ANIO, MES, demo=True, n_contenedores=n)
    vertido = sum(m["vertido_mwh"])
    cobertura = 100 * (1 - sum(m["deficit_mwh"]) / sum(m["dem_mwh"]))

    evitado_por_contenedor = ""
    if anterior is not None:
        evitado_por_contenedor = round((anterior[1] - vertido) / (n - anterior[0]), 1)

    print(n, round(vertido), round(cobertura, 1), evitado_por_contenedor, sep=" | ")
    filas.append([n, round(vertido, 1), round(cobertura, 1), evitado_por_contenedor])
    anterior = (n, vertido)

# Guarda la tabla para usarla en el informe (se abre con Excel)
salida = Path(__file__).resolve().parent / "resultado_bess.csv"
with open(salida, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["contenedores", "vertido_MWh", "cobertura_pct", "MWh_evitados_por_contenedor_extra"])
    w.writerows(filas)

print(f"\nTabla guardada en: {salida}")