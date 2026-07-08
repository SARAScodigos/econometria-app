## La estacionalidad 
* Se toma desde `2002-01 a 2022-12` es decir la ventana *full* en [settings.py](src/config/settings.py)

## La estacionariedad (ADF y KPSS)
* Tomado desde `Muestra pre-COVID: 2002-2020:02` y en tamaño completo `2002-01 a 2022-12` 

┌────────┬─────────────────────────────────────┬───────────────────────┐
│ Prueba │                 H0                  │ Rechazar H0 significa │
├────────┼─────────────────────────────────────┼───────────────────────┤
│ ADF    │ Hay raíz unitaria (no estacionaria) │ Es estacionaria       │
├────────┼─────────────────────────────────────┼───────────────────────┤
│ KPSS   │ Es estacionaria                     │ NO es estacionaria    │
└────────┴─────────────────────────────────────┴───────────────────────┘
Se necesita que todas sean Estacionarias antes de pasar al modelo. 

## Transformaciones/diferencias
* Vol_total, Mora_total, PBI, Tasa_Ref Al menos las generales que van al VARX






