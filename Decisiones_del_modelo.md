## La estacionalidad *(Prueba F de dummies regresion OLS)*

* Se toma desde `2002-01 a 2022-12` es decir la ventana *full* en [settings.py](src/config/settings.py)
* En la series Morosidad total y microcreditos se tuvo que aplicar Ajuste de regresion con OLS mediante [deseasonalize.py][src/seasonality/deseasonalize.py]


## La estacionariedad (ADF y KPSS)

* Tomado desde `Muestra pre-COVID: 2002-2020:02` y en tamaño completo `2002-01 a 2022-12`
┌────────┬─────────────────────────────────────┬───────────────────────┐
│ Prueba │                 H0                  │ Rechazar H0 significa │
├────────┼─────────────────────────────────────┼───────────────────────┤
│ ADF    │ Hay raíz unitaria (no estacionaria) │ Es estacionaria       │
├────────┼─────────────────────────────────────┼───────────────────────┤
│ KPSS   │ Es estacionaria                     │ NO es estacionaria    │
└────────┴─────────────────────────────────────┴───────────────────────┘
* Se necesita que todas sean Estacionarias antes de pasar al modelo. Para comprobarlo emplear 

## Transformaciones/diferencias

* Vol_total, Mora_total, PBI, Tasa_Ref Al menos las generales que van al VARX
[unit_roots.py](src/unit_roots/unit_roots.py)
V_Total y V_microcreditos no pasan el test. Su tranformacion se trata [tranformation_v_total.py](src/unit_roots/tranformation_v_total.py) Los resultados fueron ideales para una ventana Pre_covid con constante + tendencia (media variable predecible) *para el OB 1* 
* Para el OB General es mejor Full + tendencia. 
* Para V_microcreditos emplear estacionariedad constante mas tendencia, para *Full* y para *Pre-Covid* Eso ayuda al ob3

## Cointegracion Johansen. 
Explorar los niveles correspondientes para las endógenas [cointegracion.py](src/cointegration/johansen.py)
* D_ln_Vol_total estacionaria con tendencia *johansen con --det-order 1* Alli recién se pudo determinar la cointegración
* D_Mora_total estacionaria con constante

``` Los resultados indicaron No cointegración para las variables I(1), entonces tenemos camino libre para aplicar VARX en dierencias. ```






