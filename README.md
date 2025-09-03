# Conciliación Bancaria (1 a 1 por fecha)

App de Streamlit para conciliar un extracto bancario contra un Excel del sistema interno.
- **Extracto**: una sola columna de importes con signo (positivos = ingresos, negativos = egresos).
- **Sistema**: columnas **Debe** y **Haber** (o una columna única, si tu layout lo requiere).
- **Match 1↔1**: por importe con signo (regla Debe→+monto, Haber→−monto) y fecha más cercana.

## Requisitos
- Python 3.10+
- `pip install -r requirements.txt`

## Ejecutar
```bash
streamlit run app.py