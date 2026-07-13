# Objetivos del repositorio y modelos VARX
1. Objetivo general (OBG): Analizar la relación dinámica entre el volumen de préstamos y la tasa de morosidad en las Cajas Municipales de Ahorro y Crédito del Perú ante el shock del COVID-19, en un escenario sin medidas de alivio o rescate gubernamental.
2. Objetivo específico 1: Estimar la evolución temporal entre el volumen de préstamos y la tasa de morosidad en las Cajas Municipales de Ahorro y Crédito del Perú ante el shock del COVID-19, en un escenario sin medidas de alivio o rescate por parte del gobierno.
3. Objetivo específico 2: Identificar la respuesta diferenciada ante el shock del COVID-19 según el tipo de crédito: consumo, hipotecarios, comerciales y microcréditos de las CMAC.

# Limpieza y preparacion de datos.
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


# Proceso de modelamiento VARX en diferencias


**Variables Definidas** $\rightarrow$ **Elección Provisional de Rezagos** $\rightarrow$ **Construcción de Regresores** $\rightarrow$ **Estimación de Coeficientes** $\rightarrow$ **Comparación (AIC/BIC)**

* tras aplicar [lag_selecction.py](src/model/lag_selection.py) se ecnontró en la ventana *full* un valor de BIC =1 y AIC = 1 como rezagos optimos (solo mes) en promedio, pero con el calculo de rezagos a nivel de sistema, cruzando covarianzas fueron:
|BIC mean|AIC mean|BIC sistema|AIC sistema| 
|---|---|---|---|
|1|1|1|12|

* Ahora estimar el VARX y obtener sus indicadores usar [varx.py](src/model/varx.py)
$$\text{Selección de rezago} \rightarrow \text{Estimación final} \rightarrow \text{Diagnóstico (Estabilidad, autocorrelación, normalidad, heterecedasticidad)} \rightarrow \text{Validación (estimacion fue correcta?)} \rightarrow \text{Contrafactual (probar escenarios)}$$
* Para los valores en niveles de los tres escenarios (real, estimado y estimado sin ayuda) correr: [general_no_ayuda.py](src/scenarios/general_no_ayuda.py)
## Autocorrelación test de Ljung-Box
Se aplicó la prueba Ljung-Box hasta 12 rezagos con *p=1*
            eq    lb_stat    lb_pvalue
D_ln_Vol_total 111.996546 2.408627e-18
  D_Mora_total  17.838703 1.206765e-01

Ahora 
*p(elegido) = 12*
Estable (|eig|<1): True | max|eig|=0.9825
Ljung-Box (lag 12):
            eq  lb_stat  lb_pvalue
D_ln_Vol_total 9.475651   0.661856
  D_Mora_total 2.696790   0.997332

```El numero de rezagos p es mejor en el valor p=12 según AIC sistema y Ljung-Box```

## Jarque Bera (Normalidad de residuos)


## Estabilidad del modelo con AR
* Estable (|eig|<1): True 

## Varianza de los residuos Heterocedasticidad HC1/HC3
* Varianza de los errores no es constante. *Signficancia de los coeficientes*

La prueba de heterocedasticidad sugiere que la varianza de los residuos no es constante entre observaciones. Esto no cambia los coeficientes estimados por OLS del VARX, pero sí puede afectar los errores estándar, los estadísticos t y los p-valores. Por ello, la interpretación de significancia debe hacerse con errores estándar robustos. En este modelo se emplea HC3 porque es una corrección más conservadora ante heterocedasticidad y resulta adecuada cuando se trabaja con muestras moderadas y muchos regresores, como ocurre con un VARX de 12 rezagos. En consecuencia, los coeficientes se mantienen, pero la inferencia se reporta usando `std_err_robust`, `t_robust` y `pvalue_robust`.

## Causalidad de Granger explicacion de una variable a traves de otra

# Extraccion de coeficientes del modelo

## Coefientes y significancia
* HC3 como existía variabilidad en los coeficientes fue necesario aplicar esta corrreccion dando que ninguna variable fuese significativa al momento de predecir 

## Validacion de predicciones del modelo
* Ver los resultados de [Validation.py](src/scenarios/validation.py) en los outputs [validacion resultados](outputs/resultados_validacion.xlsx). El modelo predijo correctamente segun las metricas de MAE MAPE para las series en niveles. Se emplea dos ventanas de validacion, una pre covid y otra tomando el covid y lo siguiente. 





