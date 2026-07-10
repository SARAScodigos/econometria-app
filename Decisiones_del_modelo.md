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

* tras aplicar [lag_selecction.py](src/model/lag_selection.py) se ecnontró en la ventana *full* un valor de BIC =1 y AIC = 1 como rezagos optimos (solo mes)
|BIC mean|AIC mean|BIC sistema|AIC sistema| 
|-|---|-|-|
|1|1|1|12|

* Ahora estimar el VARX con [varx.py](src/model/varx.py)
$$\text{Selección de rezago} \rightarrow \text{Estimación final} \rightarrow \text{Diagnóstico (Estabilidad, autocorrelación, normalidad, heterecedasticidad)} \rightarrow \text{Validación (estimacion fue correcta?)} \rightarrow \text{Contrafactual (probar escenarios)}$$

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

## Varianza de los residuos Heterocedasticidad 


## Causalidad de Granger explicacion de una variable a traves de otra








