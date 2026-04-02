✦ OBSclaw 🦞 - El Realizador Virtual Inteligente para OBS

  OBSclaw es un script de automatización en Python diseñado para que los creadores de contenido
  puedan centrarse en comunicar mientras la IA se encarga de la realización de vídeo. Utiliza los
  vúmetros de OBS y reconocimiento de voz para cambiar de escena de forma profesional y fluida, como
  si tuvieras a un realizador de TV trabajando para ti.

  ✨ Características Principales

   * 🧠 Cerebro Híbrido (Ojos y Oídos): No solo escucha el volumen de los micros para cambiar de
     cámara al instante, sino que integra Reconocimiento de Voz Real para ejecutar comandos
     complejos.
   * 🎙️ Comandos de Voz "Entrenables": El sistema entiende el contexto. Si dices "vamos a
     publicidad", OBSclaw cambia automáticamente a la escena de anuncios y pausa la automatización.
   * 🛡️ Lógica de Grado Profesional:
       * Attack Time: Ignora ruidos breves (estornudos, golpes) para evitar cortes en falso.
       * Histéresis: Evita el "parpadeo" constante de cámaras entre oradores para una transición
         suave.
       * Prioridad de Host: Si el presentador interrumpe, el sistema le da prioridad absoluta de
         cámara.
       * Variación de Monólogos: Si alguien habla demasiado tiempo, el sistema rota planos
         automáticamente para mantener el ritmo visual.
   * 📍 Marcas de Tiempo Automáticas: Crea marcadores en la pista de vídeo cuando detecta cambios de
     ritmo o picos de interés para facilitar la edición de clips.
   * 💬 Interacción Inteligente: Lanza comentarios del chat o preguntas con comandos de voz.
   * 📟 Interfaz CLI Moderna: Calibración de umbrales y monitoreo en tiempo real gracias a la
     librería Rich.

  🛠️ Requisitos Técnicos

   * Python 3.10 o superior.
   * OBS Studio con el plugin obs-websocket (https://github.com/obsproject/obs-websocket) habilitado
     (incluido por defecto en versiones recientes de OBS).
   * Configuración de audio en OBS con fuentes independientes (o modo 1 micro adaptable).

  🚀 Instalación y Uso

   1. Clonar el repositorio:

   1     git clone https://github.com/davduran/obsclaw.git
   2     cd obsclaw

   2. Instalar dependencias:
   1     pip install -r requirements.txt

   3. Configuración:
      Edita el archivo obsclaw_config.json para definir tus nombres de escenas de OBS, fuentes de
  audio y comandos de voz personalizados.

   4. Ejecutar:
   1     python main.py

  ⚙️ Configuración Personalizada

  OBSclaw es altamente modular. Puedes ajustar los siguientes parámetros en el archivo de
  configuración:
   * threshold: Sensibilidad del micro.
   * switch_delay: Tiempo de espera entre cambios.
   * voice_commands: Diccionario de frases clave y sus escenas asociadas.

  🤝 Contribuciones

  ¡Este proyecto es Open Source y acaba de nacer! Las contribuciones son más que bienvenidas:
   * Reporta errores abriendo un Issue.
   * Propón mejoras o nuevas funciones mediante Pull Requests.
   * Dale una estrella (⭐️) al repositorio si te resulta útil para tus directos.

  ---
  Creado con 🦞 por davduran | #OBSclaw #Python #Streaming
