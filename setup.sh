#!/bin/bash
echo "--- Re-configurando Entorno de Audio para OBSclaw ---"

# 1. Intentar instalar dependencias críticas de sistema
echo "[1/3] Instalando dependencias de audio del sistema..."
sudo apt-get update
sudo apt-get install -y python3.13-venv portaudio19-dev libasound2-dev python3-pyaudio

# 2. Eliminar venv antiguo si existe y está roto
rm -rf venv

# 3. Crear el entorno virtual
echo "[2/3] Creando entorno virtual..."
python3 -m venv venv

if [ ! -f "venv/bin/activate" ]; then
    echo "❌ Error: No se pudo crear el venv. Intentando con --break-system-packages como último recurso..."
    # Si falla el venv, instalamos las librerías necesarias con el flag de forzado
    pip install obsws-python SpeechRecognition PyAudio --break-system-packages
else
    # Si el venv funcionó, instalamos normal
    source venv/bin/activate
    pip install --upgrade pip
    pip install obsws-python SpeechRecognition PyAudio
    echo "[3/3] Instalación completada en el entorno virtual."
fi

echo "----------------------------------------------------"
echo "¡Listo! Si el venv funcionó, ejecuta:"
echo "source venv/bin/activate && python3 main.py"
echo ""
echo "Si el venv falló pero forzamos la instalación, ejecuta directamente:"
echo "python3 main.py"
echo "----------------------------------------------------"
