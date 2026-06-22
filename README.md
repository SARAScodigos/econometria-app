# Aplicación Econométrica UDEP

Este repositorio contiene un conjunto de scripts econométricos que estiman modelos VARX, calculan escenarios base, contrafactuales con choques de COVID, y generan gráficos (Niveles y Diferencias) del impacto macroeconómico y financiero.

Ahora incluye una Interfaz Gráfica de Usuario (GUI) construida en PyQt6 que permite ejecutar todas las operaciones sin interactuar con la línea de comandos.

## Estructura del Proyecto

```
econometria-app/
├── data/                       # Archivos de entrada (e.g. Data estacionaria.xlsx)
├── outputs/                    # Resultados generados (CSVs, PNGs)
├── src/
│   ├── core/                   # Scripts econométricos y lógica
│   └── gui/                    # Código de la interfaz gráfica
├── main.py                     # Archivo principal para iniciar la aplicación
└── README.md                   # Este documento
```

## Requisitos

Instalar las librerías necesarias con Python >= 3.8:

```bash
pip install pandas numpy statsmodels matplotlib openpyxl PyQt6
```

## Ejecución

1. Coloca tu archivo de datos en la carpeta `data/` con el nombre `Data estacionaria.xlsx`.
2. Para lanzar la aplicación con interfaz gráfica, ejecuta:

```bash
python main.py
```

## Uso de la Interfaz

La aplicación se divide en 4 secciones:
1. **Datos y Pruebas**: Permite verificar la estacionalidad de las series del archivo de datos.
2. **Estimaciones y Baseline**: Corre los modelos pre-COVID y genera las predicciones AR.
3. **Escenarios y Contrafactuales**: Computa escenarios base, choque financiero (K=2) y contrafactuales dependientes/independientes.
4. **Gráficos**: Genera los PNGs correspondientes dentro de la carpeta `outputs/`.
