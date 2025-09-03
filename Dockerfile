# --- Base image ---
FROM python:3.9-slim

# --- Directorio de trabajo ---
WORKDIR /app

# --- Instalar dependencias ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copiar app ---
COPY app.py .

# --- Exponer puerto de Streamlit ---
EXPOSE 8501

# --- Arranque ---
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]