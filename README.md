# Sistema de Evaluación Energética y Factibilidad Eólica - Parque Windpeshi (Uribia, La Guajira)

Sistema de adquisición de datos climáticos, simulación aerodinámica y balance energético diario del Parque Eólico Windpeshi (41 turbinas) frente al consumo de La Guajira, con una página web para consultar cualquier día y mes.

## 1. Visión General del Proyecto

El Parque Eólico Windpeshi aprovecha los vientos Alisios del noreste en la península de La Guajira, una de las zonas con mayor densidad de potencia eólica del continente.

El proyecto responde a dos preguntas de ingeniería:

1. **Recurso eólico diario:** ¿Cuánta energía genera el parque en una jornada con el viento real de ese día?
2. **Balance frente a la demanda:** ¿Qué porcentaje del consumo de La Guajira cubre esa generación y el día se puede considerar FUNCIONAL, PARCIAL o NO FUNCIONAL?

## 2. Arquitectura del Sistema

```
PIPELIN-PARQUE-WINDPESHI/
├── api.py                   # Servidor web (FastAPI): endpoints /api/dia y /api/mes
├── static/
│   └── index.html           # Página web con tarjetas y gráficas (Chart.js)
├── config/
│   └── settings.py          # Ubicación, física del aire, turbina, parque, consumo y umbrales
├── src/
│   ├── energy_balance.py    # Balance diario/mensual: run_balance, run_month, evaluar_dia
│   ├── daq/                 # Ingesta de datos climáticos (versión anterior del pipeline)
│   └── domain/
│       ├── wind_physics.py  # Física del viento (versión anterior del pipeline)
│       └── demand_model.py  # Perfiles de demanda (versión anterior del pipeline)
└── README.md
```

El cálculo que usa la página web está en `src/energy_balance.py` y lee todos sus parámetros de `config/settings.py`. Las carpetas `daq` y `domain` pertenecen al pipeline anterior y hoy no las usa la página.

## 3. Parámetros del parque (`config/settings.py`)

| Parámetro | Valor |
|---|---|
| Ubicación | Uribia, La Guajira (11.7139, -72.2666), zona horaria America/Bogota |
| Número de turbinas | 41 |
| Potencia nominal por turbina | 2.100 kW (2,1 MW) |
| Potencia total del parque | 86,1 MW |
| Diámetro del rotor | 97 m |
| Altura del buje | 100 m |
| Coeficiente aerodinámico (Cp) | 0,42 |
| Velocidad de arranque (cut-in) | 3,5 m/s |
| Velocidad de corte (cut-out) | 25 m/s |
| Altura de medición del viento | 10 m |
| Rugosidad del terreno (z0) | 0,03 m |

Energía máxima del parque en un día: 41 x 2,1 MW x 24 h = **2.066 MWh**.

## 4. Fundamentos de Física e Ingeniería

### 4.1. Densidad real del aire

Se calcula hora a hora con la ecuación de los gases ideales:

```
rho = (P x 100) / (R_aire x (T + 273,15))
```

con P en hPa, T en °C y R_aire = 287,058 J/(kg·K).

### 4.2. Viento a la altura del buje (ley logarítmica)

```
v(100) = v(10) x ln(100 / z0) / ln(10 / z0)
```

### 4.3. Potencia de una turbina

```
P = 0,5 x rho x A x v^3 x Cp        (en kW, con A = pi x (97/2)^2)
```

- Si `v < 3,5 m/s` o `v >= 25 m/s`: P = 0.
- Si el valor calculado supera 2.100 kW: se limita a la potencia nominal.
- Potencia del parque = potencia de una turbina x 41. No se modelan pérdidas por estela.

### 4.4. Demanda

La demanda es el consumo anual de **toda La Guajira** (UPME / XM) repartido en partes iguales entre las horas del año (demanda plana de 24 horas):

```
demanda (kW) = consumo anual (GWh) x 1.000.000 / horas que cubre el dato
```

| Año | Consumo (GWh) | Horas |
|---|---|---|
| 2021 | 751,1 | 8.760 |
| 2022 | 833,7 | 8.760 |
| 2023 | 996,15 | 8.760 |
| 2024 | 552,94 | 8.784 (enero a diciembre) |

Para años sin dato (2025, 2026) se usa el último año completo, hoy 2024: unos 63 MW promedio, o 1.511 MWh por día.

> Pendiente: confirmar en la fuente (UPME / XM) el dato de 2024.

### 4.5. Métricas diarias

- **Cobertura (%)** = 100 x (1 - déficit / demanda).
- **Horas con generación:** horas del día con potencia mayor que cero.
- **Horas a potencia nominal:** horas con el parque a su potencia máxima.
- **Factor de capacidad (%)** = energía generada / (41 x 2,1 MW x horas).
- **Déficit (MWh):** energía de la demanda que el parque no cubre.

### 4.6. Criterio de veredicto

| Veredicto | Condición |
|---|---|
| FUNCIONAL | Cobertura >= 45 % y al menos 18 horas con generación |
| PARCIAL | Cobertura >= 30 % (y no cumple FUNCIONAL) |
| NO FUNCIONAL | Cobertura < 30 % |

## 5. Datos climáticos

- **Modo real:** viento a 10 m, temperatura y presión de [Open-Meteo](https://open-meteo.com/) (sin clave).
- **Modo demo (`?demo=true`):** no usa internet. Genera viento inventado, solo para probar la página. No sirve para sacar conclusiones.

## 6. Instalación y puesta en marcha

Requisitos: Python 3.10 o superior.

```bash
python -m venv venv
.\venv\Scripts\activate
pip install pandas numpy requests fastapi uvicorn
python -m uvicorn api:app --reload
```

Luego abre en el navegador:

- Datos reales: `http://127.0.0.1:8000`
- Modo demo: `http://127.0.0.1:8000/?demo=true`

## 7. API

| Endpoint | Parámetros | Respuesta |
|---|---|---|
| `GET /api/dia` | `date=AAAA-MM-DD`, `demo` (opcional) | Curva de 24 horas, energía del día y evaluación (veredicto, cobertura, horas, viento medio, factor de capacidad, déficit) |
| `GET /api/mes` | `date=AAAA-MM-DD`, `demo` (opcional) | Días del mes, generación diaria y demanda diaria (MWh) |

## 8. Limitaciones conocidas

- La demanda es plana en las 24 horas.
- No hay pérdidas por estela, disponibilidad de turbinas ni pérdidas eléctricas.
- El viento sale de un modelo de reanálisis a 10 m y se extrapola a 100 m con una sola rugosidad.
- El modo demo usa viento inventado.

## 9. Datos de localidades con telemetría (IPSE, marzo 2024)

En La Guajira solo aparecen Cabo de la Vela (44,8 MWh en el mes) y Nazareth (34,1 MWh), ambas en Uribia. Suman unos 2,5 MWh por día, unas 800 veces menos que lo que puede generar el parque, por eso no se usan como demanda. Su posible uso es tomar la forma horaria de la curva de carga.

## 10. Trabajo futuro

- Repartir la demanda por horas con una curva de carga realista.
- Verificar el consumo 2024 y agregar 2025.
- Calcular cuántas turbinas harían falta para cubrir una demanda dada.
- Reconectar el CLI (`main.py`) con el nuevo `energy_balance.py`.