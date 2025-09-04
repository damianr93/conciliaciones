# Conciliacion Bancaria (1 a 1 por fecha)

Aplicacion de Streamlit para conciliar un extracto bancario contra un Excel del sistema interno.
- Extracto: una sola columna de importes con signo (positivos = ingresos, negativos = egresos).
- Sistema: columnas Debe y Haber (o una columna unica, si tu layout lo requiere).
- Match 1 a 1: por importe con signo (regla Debe = +monto, Haber = -monto) y fecha mas cercana.

## Requisitos (desarrollo local)
- Python 3.10+
- `pip install -r requirements.txt`

## Ejecutar local
```bash
streamlit run app.py
```

## Ejecutar con Docker

Requisitos:
- Docker Desktop para Windows 11 (WSL 2 habilitado)

Pasos:
- Construir y levantar en segundo plano:
  - `docker compose up -d`
- Abrir la app en el navegador: `http://localhost:8501`

El archivo `docker-compose.yml` expone el puerto 8501 y define la politica `restart: unless-stopped` para que el contenedor se reinicie automaticamente cuando Docker inicie.

## Arranque automatico en Windows 11

Para que la app se levante sola tras reiniciar Windows, usa ambas opciones:
- En Docker Desktop: Settings → General → habilita "Start Docker Desktop when you log in".
- Usa la politica de reinicio del contenedor: ya configurada como `restart: unless-stopped` en `docker-compose.yml`.

Con esto, cuando Windows inicie y Docker Desktop arranque, el contenedor se iniciara solo en segundo plano.

Opcional (mayor control con Programador de tareas):
- Crea una tarea que ejecute, al iniciar sesion, en la carpeta del proyecto:
  - `docker compose up -d`
- Configura un retardo de 15–30 segundos para dar tiempo a que Docker Desktop este listo.

