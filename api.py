from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from src.energy_balance import run_balance, run_month, evaluar_dia

app = FastAPI()
CARPETA_STATIC = Path(__file__).resolve().parent / "static"


@app.get("/")
def inicio():
    return FileResponse(CARPETA_STATIC / "index.html")


@app.get("/api/dia")
def api_dia(date: str, demo: bool = False):
    try:
        df, k = run_balance(date, demo=demo)
    except Exception as e:
        raise HTTPException(502, f"No se pudo obtener el clima: {e}")
    return {
        "horas": df["hora"].dt.hour.tolist(),
        "gen_mw": (df["p_generada_kw"] / 1000).round(2).tolist(),
        "dem_mw": (df["p_demanda_kw"] / 1000).round(2).tolist(),
        "gen_mwh": round(k["generada_MWh"], 1),
        "dem_mwh": round(k["demanda_MWh"], 1),
        "evaluacion": evaluar_dia(df, k),
    }


@app.get("/api/mes")
def api_mes(date: str, demo: bool = False):
    d = datetime.strptime(date, "%Y-%m-%d")
    try:
        return run_month(d.year, d.month, demo=demo)
    except Exception as e:
        raise HTTPException(502, f"No se pudo obtener el clima: {e}")