from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from src.energy_balance import run_balance, run_month, evaluar_dia

app = FastAPI()
CARPETA_STATIC = Path(__file__).resolve().parent / "static"


@app.get("/")
def inicio():
    return FileResponse(CARPETA_STATIC / "index.html")


@app.get("/api/dia")
def api_dia(date: str, demo: bool = False,
            n_contenedores: int = Query(0, ge=0, le=200)):
    try:
        df, k = run_balance(date, demo=demo, n_contenedores=n_contenedores)
    except Exception as e:
        raise HTTPException(502, f"No se pudo obtener el clima: {e}")
    return {
        "horas": df["hora"].dt.hour.tolist(),
        "gen_mw": (df["p_generada_kw"] / 1000).round(2).tolist(),
        "dem_mw": (df["p_demanda_kw"] / 1000).round(2).tolist(),
        "gen_mwh": round(k["generada_MWh"], 1),
        "dem_mwh": round(k["demanda_MWh"], 1),
        "evaluacion": evaluar_dia(df, k),
        "bess": {
            "n_contenedores": n_contenedores,
            "soc_mwh": df["bess_soc_mwh"].round(2).tolist(),
            "carga_mwh": df["bess_carga_mwh"].round(2).tolist(),
            "descarga_mwh": df["bess_descarga_mwh"].round(2).tolist(),
            "vertido_mwh": round(k["vertido_MWh"], 1),
            "almacenado_mwh": round(k["almacenado_MWh"], 1),
            "descargado_mwh": round(k["descargado_MWh"], 1),
        },
    }


@app.get("/api/mes")
def api_mes(date: str, demo: bool = False,
            n_contenedores: int = Query(0, ge=0, le=200)):
    d = datetime.strptime(date, "%Y-%m-%d")
    try:
        return run_month(d.year, d.month, demo=demo, n_contenedores=n_contenedores)
    except Exception as e:
        raise HTTPException(502, f"No se pudo obtener el clima: {e}")


@app.get("/api/comparar-mes")
def api_comparar_mes(date: str, demo: bool = False,
                     n_contenedores: int = Query(10, ge=1, le=200)):
    d = datetime.strptime(date, "%Y-%m-%d")
    try:
        sin = run_month(d.year, d.month, demo=demo, n_contenedores=0)
        con = run_month(d.year, d.month, demo=demo, n_contenedores=n_contenedores)
    except Exception as e:
        raise HTTPException(502, f"No se pudo obtener el clima: {e}")

    orden = {"NO FUNCIONAL": 0, "PARCIAL": 1, "FUNCIONAL": 2}
    dias = []
    for i, dia in enumerate(sin["dias"]):
        mejora = orden[con["veredicto"][i]] > orden[sin["veredicto"][i]]
        dias.append({
            "dia": dia,
            "cobertura_sin": sin["cobertura_pct"][i],
            "cobertura_con": con["cobertura_pct"][i],
            "veredicto_sin": sin["veredicto"][i],
            "veredicto_con": con["veredicto"][i],
            "soc_fin_mwh": con["soc_fin_mwh"][i],
            "bess_ayuda": mejora,
        })
    return {"n_contenedores": n_contenedores,
            "dias_que_mejoran": sum(x["bess_ayuda"] for x in dias),
            "dias": dias}
