# Ubicacion: Uribia, La Guajira
LATITUDE = 11.7139
LONGITUDE = -72.2666
TIMEZONE = "America/Bogota"

# Fisica del aire y del terreno
R_AIRE = 287.058      # J/(kg*K), aire seco
Z_REF = 10.0          # m, altura a la que se mide el viento
Z0 = 0.03             # m, rugosidad del terreno

# Turbina
HUB_HEIGHT = 100.0    # m, altura del buje
ROTOR_DIAMETER = 97.0 # m
CP = 0.42             # coeficiente aerodinamico
RATED_KW = 2100.0     # kW por turbina
V_CUT_IN = 3.5        # m/s
V_CUT_OUT = 25.0      # m/s

# Parque
N_TURBINES = 41

# Consumo de energia de TODA La Guajira (UPME / XM), en GWh
# Formato: anio: (GWh, horas que cubre el dato)
CONSUMO_GUAJIRA = {
    2021: (751.1, 8760),
    2022: (833.7, 8760),
    2023: (996.15, 8760),
    2024: (552.94, 8784),   # enero a diciembre (anio bisiesto)
}

# Criterios para decidir si un dia es "funcional"
UMBRAL_FUNCIONAL_PCT = 45.0   # cobertura minima de la demanda para "FUNCIONAL"
UMBRAL_PARCIAL_PCT = 30.0     # cobertura minima para "PARCIAL"
HORAS_UTILES_MIN = 18         # horas minimas con generacion para "FUNCIONAL"
