import obsws_python as obs
import time
import threading
import random
import logging
import json
import os
import signal
import sys

# Importaciones opcionales para UI Awesome
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.live import Live
    from rich.progress import BarColumn, Progress, TextColumn
    from rich import print as rprint
    rich_available = True
    console = Console()
except ImportError:
    rich_available = False

# Importación opcional para reconocimiento de voz
try:
    import speech_recognition as sr
except ImportError:
    sr = None

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# --- CONFIGURACIÓN ESTÉTICA (ANSI COLORS) ---
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# --- LOGGING CUSTOM ---
class CustomFormatter(logging.Formatter):
    format_str = "%(asctime)s | %(levelname)-7s | %(message)s"
    FORMATS = {
        logging.DEBUG: Colors.OKCYAN + format_str + Colors.ENDC,
        logging.INFO: Colors.OKGREEN + format_str + Colors.ENDC,
        logging.WARNING: Colors.WARNING + format_str + Colors.ENDC,
        logging.ERROR: Colors.FAIL + format_str + Colors.ENDC,
        logging.CRITICAL: Colors.BOLD + Colors.FAIL + format_str + Colors.ENDC
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)

logger = logging.getLogger("OBSclaw")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
if not logger.handlers:
    logger.addHandler(ch)

# --- MANEJO DE CONFIGURACIÓN EXTERNA ---
class Config:
    def __init__(self, filename="obsclaw_config.json"):
        self.filename = filename
        # Valores por defecto de conexión
        self.host = "localhost"
        self.port = 4455
        self.password = "demate8945"
        
        # --- Lógica de Realización Avanzada ---
        self.voice_threshold = 0.03       # Umbral mínimo de volumen (vúmetro)
        self.attack_time = 0.3            # (NUEVO) Segundos que debe durar el sonido para considerarse voz (evita cortes por tos/golpes)
        self.min_cut_cooldown = 2.0       # Tiempo mínimo de permanencia en un plano (evita parpadeo)
        self.voice_hold_time = 1.0        # Histéresis: tiempo de aguante tras dejar de hablar
        self.host_priority = False        # (NUEVO) Si es True, el Host pisa la cámara del invitado. Si es False, van a plano General.
        self.monologue_time = 20.0        # (NUEVO) Segundos de monólogo antes de variar a plano general para dar ritmo visual
        self.silence_timeout = 5.0        # Segundos de silencio total antes de volver a plano general
        self.lower_third_duration = 5.0   # Duración del rótulo en pantalla
        
        # --- Filtros ---
        self.ignored_audio_sources = ["audio del escritorio", "desktop audio"] # (NUEVO) Ignorar fuentes de sistema
        
        # Diccionario de comandos vocales "entrenados"
        self.commands = {
            "intro": ["empezamos", "comenzamos", "arrancamos", "hola a todos", "bienvenidos", "en directo"],
            "ads": ["publicidad", "mensajes", "pausa comercial", "patrocinadores"],
            "back": ["estamos de vuelta", "continuamos", "regresamos", "seguimos"],
            "outro": ["hasta aquí", "próximo capítulo", "nos vemos", "despedimos", "hasta la próxima"]
        }
        
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.__dict__.update(data)
                logger.info(f"Configuración cargada desde {self.filename}")
            except Exception as e:
                logger.error(f"Error cargando config: {e}")
        else:
            self.save()
            
    def save(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                data = {k: v for k, v in self.__dict__.items() if k != 'filename'}
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info(f"Archivo de configuración guardado: {self.filename}")
        except Exception as e:
            logger.error(f"Error guardando config: {e}")

# --- NÚCLEO DEL DIRECTOR (REALIZADOR INTELIGENTE) ---
class VoiceListener(threading.Thread):
    def __init__(self, callback, language="es-ES"):
        super().__init__()
        self.callback = callback
        self.language = language
        self.running = False
        self.daemon = True
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 400 
        self.recognizer.dynamic_energy_threshold = True

    def run(self):
        if not sr: return
        try:
            with sr.Microphone() as source:
                logger.info(f"🎤 {Colors.OKBLUE}Micrófono inicializado. Escuchando en {self.language}...{Colors.ENDC}")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.running = True
                while self.running:
                    try:
                        audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=8)
                        text = self.recognizer.recognize_google(audio, language=self.language)
                        if text: self.callback(text)
                    except (sr.WaitTimeoutError, sr.UnknownValueError): continue
                    except sr.RequestError as e:
                        logger.error(f"Error en el servicio de reconocimiento: {e}")
                        time.sleep(2)
                    except Exception as e: logger.debug(f"Error en hilo de voz: {e}")
        except Exception as e:
            logger.error(f"No se pudo acceder al micrófono: {e}")

    def stop(self):
        self.running = False

class OBSclawDirector:
    def __init__(self, config: Config):
        self.config = config
        self.client = None
        self.event_client = None
        self.voice_thread = None
        self.all_scenes = []
        self.audio_sources = []
        self.mapped_scenes = {"host": None, "guest": None, "wide": None, "ads": None, "outro": None}
        self.last_change_time = 0
        self.auto_mode = False
        self.manual_override = False
        self.mic_levels = {}
        self.mic_active_start = {}
        self.last_spoken_time = {"host": 0, "guest": 0}
        self.monologue_start_time = 0
        self.last_command_log = []
        self.last_heard_log = []
        self.lower_third_active = False

    def connect(self):
        try:
            logger.info("Conectando con OBS WebSocket...")
            self.client = obs.ReqClient(host=self.config.host, port=self.config.port, password=self.config.password)
            subs = obs.subs.Subs.INPUTVOLUMEMETERS
            self.event_client = obs.EventClient(host=self.config.host, port=self.config.port, password=self.config.password, subs=subs)
            self.event_client.callback.register(self.on_input_volume_meters)
            self.refresh_scenes()
            self.discover_audio_sources()
            self.auto_map_scenes()
            if sr:
                self.voice_thread = VoiceListener(self.process_transcript)
                self.voice_thread.start()
            else:
                logger.warning("Reconocimiento de voz desactivado.")
            logger.info(Colors.OKGREEN + "Director conectado y listo." + Colors.ENDC)
            return True
        except Exception as e:
            logger.error(f"Error de conexión: {e}")
            return False

    def disconnect(self):
        try:
            if self.voice_thread: self.voice_thread.stop()
            if self.event_client: self.event_client.disconnect()
            if self.client: self.client.disconnect()
        except: pass

    def refresh_scenes(self):
        if not self.client: return []
        response = self.client.get_scene_list()
        self.all_scenes = [scene['sceneName'] for scene in response.scenes]
        self.mapped_scenes = {"intro": None, "host": None, "guest": None, "wide": None, "ads": None, "outro": None}
        return self.all_scenes

    def auto_map_scenes(self):
        for scene in self.all_scenes:
            scene_lower = scene.lower()
            if any(k in scene_lower for k in ["inicio", "intro", "comienzo", "start"]): self.mapped_scenes["intro"] = scene
            elif any(k in scene_lower for k in ["host", "principal", "camara 1"]): self.mapped_scenes["host"] = scene
            elif any(k in scene_lower for k in ["invitado", "guest", "camara 2"]): self.mapped_scenes["guest"] = scene
            elif any(k in scene_lower for k in ["general", "wide", "ambos"]): self.mapped_scenes["wide"] = scene
            elif any(k in scene_lower for k in ["publi", "ads"]): self.mapped_scenes["ads"] = scene
            elif any(k in scene_lower for k in ["fin", "outro"]): self.mapped_scenes["outro"] = scene
        self.print_dashboard()

    def print_dashboard(self):
        if rich_available:
            table = Table(title="[bold cyan]OBSclaw - MAPEO DE ESCENAS EN OBS[/bold cyan]", border_style="bright_blue", expand=True)
            table.add_column("Acción", style="bold magenta", justify="right")
            table.add_column("Escena en OBS", style="white")
            table.add_column("Estado", justify="center")
            
            for key, value in self.mapped_scenes.items():
                status = "[bold green]DETECTADA[/bold green]" if value else "[bold red]FALTA[/bold red]"
                scene_display = value if value else "[italic red]No encontrada (revisa nombres en OBS)[/italic red]"
                table.add_row(key.upper(), scene_display, status)
            
            console.print(Panel(table, title="[bold white]DASHBOARD PRINCIPAL[/bold white]", border_style="cyan"))
        else:
            print(f"\n{Colors.HEADER}{Colors.BOLD}╔════════════════════════════════════════════════╗")
            print(f"║       OBSclaw - MAPEO DE ESCENAS EN OBS        ║")
            print(f"╚════════════════════════════════════════════════╝{Colors.ENDC}")
            for key, value in self.mapped_scenes.items():
                status = f"{Colors.OKGREEN}{value}{Colors.ENDC}" if value else f"{Colors.FAIL}NO DETECTADA{Colors.ENDC}"
                print(f"  {Colors.BOLD}▶ {key.upper().ljust(8)}:{Colors.ENDC} {status}")
            print(f"{Colors.HEADER}──────────────────────────────────────────────────{Colors.ENDC}\n")

    def discover_audio_sources(self):
        if not self.client: return []
        try:
            response = self.client.get_input_list()
            self.audio_sources = []
            for i in response.inputs:
                name = i['inputName']
                kind = i['inputKind'].lower()
                if name.lower() in [ign.lower() for ign in self.config.ignored_audio_sources]:
                    continue
                if "capture" in kind or "mic" in name.lower():
                    self.audio_sources.append(name)
            return self.audio_sources
        except: return []

    def on_input_volume_meters(self, data):
        if hasattr(data, 'inputs'):
            for input_data in data.inputs:
                name = input_data.get('inputName')
                levels = input_data.get('inputLevelsMul')
                if name and levels:
                    self.mic_levels[name] = max([ch[1] for ch in levels if len(ch)>1] or [0.0])

    def get_mic_status(self, source_name):
        if not self.client: return False
        try:
            if self.client.get_input_mute(source_name).input_muted:
                self.mic_active_start[source_name] = 0
                return False
                
            level = self.mic_levels.get(source_name, 0.0)
            if level > self.config.voice_threshold:
                if self.mic_active_start.get(source_name, 0) == 0:
                    self.mic_active_start[source_name] = time.time()
                
                if (time.time() - self.mic_active_start[source_name]) >= self.config.attack_time:
                    return True
            else:
                self.mic_active_start[source_name] = 0
                
            return False
        except: return False

    def trigger_lower_third(self, source_name="Rotulo_Invitado"):
        if self.lower_third_active: return
        try:
            self.lower_third_active = True
            scene = self.client.get_current_program_scene().current_program_scene_name
            items = self.client.get_scene_item_list(scene).scene_items
            item_id = next((i['sceneItemId'] for i in items if i['sourceName'] == source_name), None)
            if item_id:
                self.client.set_scene_item_enabled(scene, item_id, True)
                time.sleep(self.config.lower_third_duration)
                self.client.set_scene_item_enabled(scene, item_id, False)
        except: pass
        finally: self.lower_third_active = False

    def process_transcript(self, text, speaker_id=None):
        text_lower = text.lower()
        self.last_heard_log.insert(0, f"[{time.strftime('%H:%M:%S')}] '{text}'")
        self.last_heard_log = self.last_heard_log[:5]
        found_cmd = next((k for k, p in self.config.commands.items() if any(kw in text_lower for kw in p)), None)
        if found_cmd:
            self.last_command_log.insert(0, f"[{time.strftime('%H:%M:%S')}] {found_cmd.upper()}: '{text}'")
            self.last_command_log = self.last_command_log[:3]
            
            logger.warning(f"🎙️  {Colors.BOLD}{Colors.OKGREEN}COMANDO DETECTADO:{Colors.ENDC} {found_cmd.upper()} ({text})")

            if found_cmd == "intro":
                self.manual_override = False
                target = self.mapped_scenes["intro"] or self.mapped_scenes["wide"]
                if target: 
                    self.client.set_current_program_scene(target)
                    logger.info(f"🚀 Iniciando show en escena: {target}")
            elif found_cmd == "ads" and self.mapped_scenes["ads"]:
                self.client.set_current_program_scene(self.mapped_scenes["ads"])
                self.manual_override = True
                logger.info("⏸️  Realizador en PAUSA (Modo Publicidad)")
            elif found_cmd == "back":
                self.manual_override = False
                if self.mapped_scenes["wide"]: 
                    self.client.set_current_program_scene(self.mapped_scenes["wide"])
                    logger.info("▶️  Realizador REANUDADO (Vuelta al show)")
            elif found_cmd == "outro" and self.mapped_scenes["outro"]:
                self.client.set_current_program_scene(self.mapped_scenes["outro"])
                self.manual_override = True
                logger.info("🏁 Fin del programa detectado")

    def execute_camera_cut(self, target_scene, reason=""):
        if not target_scene:
            return # Evitar error 300 si la escena no existe

        try:
            current = self.client.get_current_program_scene().current_program_scene_name
            if target_scene != current and (time.time() - self.last_change_time) > self.config.min_cut_cooldown:
                self.client.set_current_program_scene(target_scene)
                self.last_change_time = time.time()
                logger.info(f"🎥 {Colors.OKCYAN}CORTE A:{Colors.ENDC} {target_scene} ({reason})")
        except Exception as e:
            logger.error(f"Error al ejecutar corte de cámara: {e}")

    def run_test_mode(self):
        """Modo de monitoreo interactivo con UI avanzada (Rich)."""
        if not self.audio_sources:
            logger.error("No hay fuentes de audio para testear.")
            return

        self.auto_mode = True
        import select
        
        if not rich_available:
            # Fallback mejorado para que no se pierda información aunque no esté rich
            while self.auto_mode:
                try:
                    if select.select([sys.stdin], [], [], 0)[0]:
                        key = sys.stdin.read(1).lower()
                        if key == '+': self.config.voice_threshold += 0.005; self.config.save()
                        elif key == '-': self.config.voice_threshold -= 0.005; self.config.save()
                        elif key == '1': self.process_transcript("comando publicidad")
                        elif key == '2': self.process_transcript("estamos de vuelta")
                        elif key == '3': self.process_transcript("hasta luego")
                        elif key == 'l': threading.Thread(target=self.trigger_lower_third).start()

                    curr = self.client.get_current_program_scene().current_program_scene_name if self.client else "?"
                    sys.stdout.write("\033[H\033[J")
                    print(f"{Colors.HEADER}--- MODO TEST (SIN RICH) ---{Colors.ENDC}")
                    print(f"ESCENA: {Colors.OKBLUE}{curr}{Colors.ENDC} | UMBRAL: {self.config.voice_threshold:.3f}")
                    print("-" * 50)
                    for mic in self.audio_sources:
                        lvl = self.mic_levels.get(mic, 0.0)
                        color = Colors.OKGREEN if lvl > self.config.voice_threshold else Colors.WARNING
                        bar = '█' * int(min(lvl * 40, 20))
                        print(f"  {mic.ljust(15)} | {color}{bar.ljust(20)}{Colors.ENDC} {lvl:.4f}")
                    
                    print(f"\n{Colors.BOLD}ÚLTIMO ESCUCHADO:{Colors.ENDC}")
                    for heard in self.last_heard_log[:2]: print(f"  {heard}")
                    
                    print(f"\n{Colors.BOLD}ÚLTIMOS COMANDOS:{Colors.ENDC}")
                    for cmd in self.last_command_log[:2]: print(f"  {Colors.OKGREEN}✔ {cmd}{Colors.ENDC}")
                    
                    print("\n" + "-" * 50)
                    print("[+ / -] Umbral | [1,2,3] Escenas | [L] Rótulo | Ctrl+C Salir")
                    time.sleep(0.1)
                except KeyboardInterrupt: self.auto_mode = False
            return

        # --- VERSIÓN RICH (AWESOME) ---
        def generate_test_layout():
            curr_scene = "???"
            try: curr_scene = self.client.get_current_program_scene().current_program_scene_name
            except: pass

            # 1. Tabla de Niveles
            table = Table(show_header=True, header_style="bold magenta", expand=True, border_style="cyan")
            table.add_column("Micrófono", style="dim", width=20)
            table.add_column("Nivel", justify="right")
            table.add_column("Vúmetro", justify="center")
            table.add_column("Detección", justify="center")

            for mic in self.audio_sources:
                lvl = self.mic_levels.get(mic, 0.0)
                thresh = self.config.voice_threshold
                perc = (lvl / thresh) * 100 if thresh > 0 else 0
                bar_len = 20
                filled = int(min(lvl * 10, 1.0) * bar_len)
                bar = "[bold green]█[/bold green]" * filled + "[dim white]░[/dim white]" * (bar_len - filled)
                status = "[bold green]● VOZ[/bold green]" if lvl > thresh else "[dim yellow]○ RUIDO[/dim yellow]"
                table.add_row(mic, f"{lvl:.4f}\n({perc:3.0f}%)", bar, status)

            # 2. Logs
            logs = Table.grid(expand=True)
            for msg in self.last_heard_log[:3]: logs.add_row(f"[cyan]📢 {msg}[/cyan]")
            cmds = Table.grid(expand=True)
            for cmd in self.last_command_log[:2]: cmds.add_row(f"[bold green]✔ {cmd}[/bold green]")

            from rich.layout import Layout
            l = Layout()
            l.split_column(
                Layout(Panel(table, title=f"[bold white]LABORATORIO[/bold white] | Escena: [yellow]{curr_scene}[/yellow] | Umbral: [cyan]{self.config.voice_threshold:.3f}[/cyan]", border_style="bright_blue"), ratio=2),
                Layout(name="lower", ratio=1)
            )
            l["lower"].split_row(
                Layout(Panel(logs, title="[bold cyan]OÍDO[/bold cyan]", border_style="cyan")),
                Layout(Panel(cmds, title="[bold green]COMANDOS[/bold green]", border_style="green"))
            )
            return l

        try:
            with Live(generate_test_layout(), refresh_per_second=10, screen=True) as live:
                while self.auto_mode:
                    if select.select([sys.stdin], [], [], 0)[0]:
                        key = sys.stdin.read(1).lower()
                        if key == '+': self.config.voice_threshold += 0.005; self.config.save()
                        elif key == '-': self.config.voice_threshold -= 0.005; self.config.save()
                        elif key == '1': self.process_transcript("comando publicidad")
                        elif key == '2': self.process_transcript("estamos de vuelta")
                        elif key == '3': self.process_transcript("hasta luego")
                        elif key == 'l': threading.Thread(target=self.trigger_lower_third).start()
                    live.update(generate_test_layout())
                    time.sleep(0.05)
        except KeyboardInterrupt:
            self.auto_mode = False
            print("\nSaliendo del monitor...")

    def run_podcast_loop(self):
        self.auto_mode = True
        if len(self.audio_sources) == 0:
            logger.error("No se han detectado fuentes de audio en OBS. Revisa la configuración.")
            return

        try:
            # --- CASO 1: UN SOLO MICRO (Modo Realizador Dinámico) ---
            if len(self.audio_sources) == 1:
                mic = self.audio_sources[0]
                logger.info(f"🎬 {Colors.OKBLUE}Iniciando Modo Micro Único ('{mic}'){Colors.ENDC}")
                logger.info("El realizador rotará cámaras automáticamente mientras detecte voz.")
                
                # Escenas que el director puede usar para variar el plano
                cam_scenes = [s for k, s in self.mapped_scenes.items() if s and k in ["host", "guest", "wide"]]
                if not cam_scenes:
                    logger.error("No tienes escenas de 'host', 'guest' o 'wide' mapeadas. Abortando.")
                    return

                last_cut_time = 0
                any_last_spoken = 0
                
                while self.auto_mode:
                    if not self.manual_override:
                        now = time.time()
                        is_speaking = self.get_mic_status(mic)
                        
                        if is_speaking:
                            any_last_spoken = now
                            # Si ha pasado el tiempo de monólogo o es el primer corte
                            if (now - last_cut_time) > self.config.monologue_time:
                                current = self.client.get_current_program_scene().current_program_scene_name
                                choices = [s for s in cam_scenes if s != current]
                                target = random.choice(choices) if choices else cam_scenes[0]
                                self.execute_camera_cut(target, "Ritmo visual (1 Micro)")
                                last_cut_time = now
                        else:
                            # Silencio prolongado -> Volver a General
                            if (now - any_last_spoken) > self.config.silence_timeout:
                                if self.mapped_scenes["wide"]:
                                    self.execute_camera_cut(self.mapped_scenes["wide"], "Silencio")
                    time.sleep(0.1)

            # --- CASO 2: MÚLTIPLES MICROS (Modo Multipista Inteligente) ---
            else:
                host_mic, guest_mic = self.audio_sources[0], self.audio_sources[1]
                logger.info(f"🎬 {Colors.OKGREEN}Iniciando Modo Multipista (Host: {host_mic} | Guest: {guest_mic}){Colors.ENDC}")
                
                # Estado de monólogo
                monologue_speaker = None
                monologue_start_time = 0
                
                while self.auto_mode:
                    if not self.manual_override:
                        now = time.time()
                        h_active, g_active = self.get_mic_status(host_mic), self.get_mic_status(guest_mic)
                        
                        if h_active: self.last_spoken_time["host"] = now
                        if g_active: self.last_spoken_time["guest"] = now
                        
                        h_s = (now - self.last_spoken_time["host"]) < self.config.voice_hold_time
                        g_s = (now - self.last_spoken_time["guest"]) < self.config.voice_hold_time
                        
                        # Gestión de Silencio Prolongado
                        if not h_s and not g_s:
                            time_since_last_word = now - max(self.last_spoken_time.values())
                            if time_since_last_word > self.config.silence_timeout:
                                self.execute_camera_cut(self.mapped_scenes["wide"], "Silencio prolongado")
                            monologue_speaker = None
                            time.sleep(0.1)
                            continue

                        # Lógica Principal de Cámaras
                        if h_s and g_s:
                            monologue_speaker = None # Se rompe el monólogo
                            if self.config.host_priority:
                                self.execute_camera_cut(self.mapped_scenes["host"], "Ambos (Prioridad Host)")
                            else:
                                self.execute_camera_cut(self.mapped_scenes["wide"], "Ambos hablan")
                        elif h_s:
                            if monologue_speaker != "host":
                                monologue_speaker = "host"
                                monologue_start_time = now
                            elif (now - monologue_start_time) > self.config.monologue_time:
                                self.execute_camera_cut(self.mapped_scenes["wide"], "Variación Monólogo Host")
                                monologue_start_time = now # Reiniciar temporizador
                            else:
                                self.execute_camera_cut(self.mapped_scenes["host"], "Host")
                        elif g_s:
                            if monologue_speaker != "guest":
                                monologue_speaker = "guest"
                                monologue_start_time = now
                            elif (now - monologue_start_time) > self.config.monologue_time:
                                self.execute_camera_cut(self.mapped_scenes["wide"], "Variación Monólogo Invitado")
                                monologue_start_time = now # Reiniciar temporizador
                            else:
                                self.execute_camera_cut(self.mapped_scenes["guest"], "Guest")
                                
                    time.sleep(0.1)
        except KeyboardInterrupt:
            self.auto_mode = False
            logger.info("Realización detenida. Volviendo al menú...")

def signal_handler(sig, frame):
    # Ya no forzamos sys.exit aquí para permitir capturarlo en los bucles
    pass

def interactive_training(config: Config):
    print(f"\n{Colors.HEADER}{Colors.BOLD}--- MODO ENTRENAMIENTO DE COMANDOS VOCALES ---{Colors.ENDC}")
    print("Aquí puedes añadir nuevas frases o palabras clave que activarán la realización automática.")
    print("Las frases actuales están guardadas en tu archivo de configuración.\n")
    
    actions = {
        "intro": "Inicio del programa / Intro",
        "ads": "Ir a Publicidad",
        "back": "Volver de Publicidad (Plano General)",
        "outro": "Despedida / Fin del Programa"
    }
    
    for key, description in actions.items():
        print(f"{Colors.OKCYAN}▶ Acción: {description}{Colors.ENDC}")
        current_phrases = config.commands.get(key, [])
        print(f"  Frases actuales: {', '.join(current_phrases)}")
        
        while True:
            new_phrase = input(f"  Añadir nueva frase (o presiona Enter para saltar): ").strip().lower()
            if not new_phrase: break
            if new_phrase not in current_phrases:
                config.commands[key].append(new_phrase)
                print(f"  {Colors.OKGREEN}✓ '{new_phrase}' añadida correctamente.{Colors.ENDC}")
            else:
                print(f"  {Colors.WARNING}⚠ Esta frase ya existe.{Colors.ENDC}")
        print("-" * 50)
    config.save()
    print(f"{Colors.BOLD}{Colors.OKGREEN}¡Entrenamiento guardado con éxito!{Colors.ENDC}\n")

if __name__ == "__main__":
    # Eliminamos el signal.signal para que KeyboardInterrupt funcione de forma estándar
    config = Config()
    director = OBSclawDirector(config)
    
    while True:
        try:
            clear_screen()
            # ASCII Art de bienvenida
            if rich_available:
                rprint(r"""[bold cyan]
   ____  ____  ____      _                 
  / __ \|  _ \/ ___|    | |                
 | |  | | |_) \___ \ ___| | __ ___      __ 
 | |  | |  _ < ___) | __| |/ _` \ \ /\ / / 
 | |__| | |_) |___) | (__| | (_| |\ V  V /  
  \____/|____/|____/ \___|_|\__,_| \_/\_/   
          PODCAST DIRECTOR AI                
[/bold cyan]""")
            else:
                print(f"\n{Colors.OKCYAN}{Colors.BOLD}")
                print(r"   ____  ____  ____      _                 ")
                print(r"  / __ \|  _ \/ ___|    | |                ")
                print(r" | |  | | |_) \___ \ ___| | __ ___      __ ")
                print(r" | |  | |  _ < ___) | __| |/ _` \ \ /\ / / ")
                print(r" | |__| | |_) |___) | (__| | (_| |\ V  V /  ")
                print(r"  \____/|____/|____/ \___|_|\__,_| \_/\_/   ")
                print(r"          PODCAST DIRECTOR AI                ")
                print(f"{Colors.ENDC}\n")

            if rich_available:
                menu_table = Table(show_header=False, box=None)
                menu_table.add_row("[bold cyan]1.[/bold cyan] Iniciar Director Automático", "[dim]Realización en vivo[/dim]")
                menu_table.add_row("[bold cyan]2.[/bold cyan] Entrenar Comandos Vocales", "[dim]Añadir frases personalizadas[/dim]")
                menu_table.add_row("[bold cyan]3.[/bold cyan] Monitor de Audio (Modo Test)", "[dim]Calibración y laboratorio[/dim]")
                menu_table.add_row("[bold cyan]4.[/bold cyan] Salir", "[dim]Cerrar OBSclaw[/dim]")
                console.print(Panel(menu_table, title="[bold white]¿QUÉ DESEAS HACER?[/bold white]", border_style="bright_blue", expand=False))
            else:
                print(f"{Colors.BOLD}¿Qué deseas hacer?{Colors.ENDC}")
                print(" 1. Iniciar el Director Automático")
                print(" 2. Entrenar Comandos Vocales")
                print(" 3. Monitor de Audio (Modo Test / Calibración)")
                print(" 4. Salir")
                
            choice = input("\nSelecciona una opción [1]: ").strip()
                
            if choice == "4":
                print("¡Hasta pronto!")
                break
                
            if choice == "2":
                interactive_training(config)
                continue
            
            if choice == "3":
                if director.connect():
                    director.run_test_mode()
                else:
                    input("\nPresiona Enter para volver al menú...")
                continue
                    
            if choice == "" or choice == "1":
                if director.connect():
                    director.run_podcast_loop()
                else:
                    input("\nPresiona Enter para volver al menú...")
                continue
        except KeyboardInterrupt:
            print("\n\nSaliendo de OBSclaw...")
            break
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            time.sleep(2)
