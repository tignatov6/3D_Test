# main.py
import glm
# import math # math не используется напрямую здесь, glm.radians и т.д. покрывают это
from settings import * # WIN_RES, FULLSCREEN, BG_COLOR, FOV_DEG, NEAR, FAR, TEST (ASPECT_RATIO будет динамическим)
import pygame as pg
from scene import Scene 
from player import Player # Player должен быть адаптирован под SDL-ввод
import multiprocessing # Для multiprocessing.freeze_support()
import sys 
import gc # Для gc.disable() и manage_gc()
import time # Для manage_gc()
import os # Для возможной настройки путей при сборке в .exe
import ctypes


# --- SDL Константы (примерные значения, сверьтесь с SDL документацией/заголовками) ---
# Из SDL_video.h или SDL_events.h (для SDL_WindowEventID)
SDL_WINDOWEVENT_NONE = 0
SDL_WINDOWEVENT_SHOWN = 1
SDL_WINDOWEVENT_HIDDEN = 2
SDL_WINDOWEVENT_EXPOSED = 3
SDL_WINDOWEVENT_MOVED = 4
SDL_WINDOWEVENT_RESIZED = 5        # Размер изменен API (SDL_SetWindowSize)
SDL_WINDOWEVENT_SIZE_CHANGED = 6   # Размер изменен (часто пользователем)
SDL_WINDOWEVENT_MINIMIZED = 7
SDL_WINDOWEVENT_MAXIMIZED = 8
SDL_WINDOWEVENT_RESTORED = 9
SDL_WINDOWEVENT_ENTER = 10         # Мышь вошла в окно
SDL_WINDOWEVENT_LEAVE = 11         # Мышь покинула окно
SDL_WINDOWEVENT_FOCUS_GAINED = 12
SDL_WINDOWEVENT_FOCUS_LOST = 13
SDL_WINDOWEVENT_CLOSE = 14         # Окно просит закрыться (X, Alt+F4)
SDL_WINDOWEVENT_TAKE_FOCUS = 15
SDL_WINDOWEVENT_HIT_TEST = 16

# Для SDL_Scancode (используется в player.py, но для примера можно и здесь)
SDL_SCANCODE_ESCAPE = 41
# ... и другие нужные скан-коды ...

# --- Установка DPI Awareness (для корректного разрешения на Windows с масштабированием) ---
try:
    # Windows 8.1 и новее
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
    print("INFO: SetProcessDpiAwareness(2) called successfully (Per-Monitor DPI Aware v2).")
except AttributeError:
    # Windows Vista, 7, 8 (менее точное, но лучше, чем ничего)
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        print("INFO: SetProcessDPIAware() called successfully (System DPI Aware).")
    except AttributeError:
        print("WARNING: Could not set DPI awareness. Resolution might be affected by OS scaling.")
except Exception as e:
    print(f"WARNING: Error setting DPI awareness: {e}")
# ----------------------------------------------------------------------------------------

# --- Настройка для сборки в .exe (PyInstaller и др.) ---
def get_base_path():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.abspath(".")

BASE_PATH = get_base_path()

# --- Профайлер ---
PROFILER_ENABLED = True 
if PROFILER_ENABLED:
    try:
        from utils.profiler import report as profiler_report, get_profiler
        main_profiler = get_profiler(__name__) 
        print("Profiler enabled and loaded.")
    except ImportError:
        profiler_report = lambda: print("Profiler report function not found.")
        def profiler_dummy_decorator(func): return func
        main_profiler = profiler_dummy_decorator
        print("Warning: Profiler (utils.profiler) not found. Using dummy profiler.")
else:
    profiler_report = lambda: None 
    def profiler_dummy_decorator(func): return func
    main_profiler = profiler_dummy_decorator
    print("Profiler disabled by PROFILER_ENABLED flag.")

# --- Выбор Рендерера ---
# Renderer будет ожидать другие аргументы в конструкторе
if not TEST:
    try:
        from utils.renderer import Renderer 
    except ImportError as e:
        print(f"CRITICAL: Failed to import main Renderer from utils.renderer: {e}")
        sys.exit(1)
else: 
    try:
        from utils.renderer_test import Renderer # Если есть тестовая версия
    except ImportError as e:
        print(f"CRITICAL: Failed to import test Renderer from utils.renderer_test: {e}")
        sys.exit(1)


class Engine:
    @main_profiler
    def __init__(self, requested_size=WIN_RES, requested_fullscreen=FULLSCREEN, initial_bg_color_glm=BG_COLOR):
        try:
            pg.init() # Инициализируем Pygame для таймеров, джойстика, аудио и т.д.
                      # Модуль display не будет использоваться для создания основного окна.
        except Exception as e:
            print(f"CRITICAL: Pygame initialization failed: {e}")
            sys.exit(1)
        
        # --- Окно Pygame больше не создается здесь ---
        self.window = None # Явно указываем, что окно Pygame не управляется Engine напрямую
        
        self.requested_win_width = int(requested_size.x)
        self.requested_win_height = int(requested_size.y)
        self.fullscreen_requested = requested_fullscreen
        self.initial_bg_color = initial_bg_color_glm

        # Фактические размеры окна будут установлены Renderer'ом
        self.current_win_width = self.requested_win_width
        self.current_win_height = self.requested_win_height
        
        self.clock = pg.time.Clock()
        self.delta_time = 0.001 # Инициализируем малой величиной

        self.total_frames = 0
        self.total_time = 0.0
        
        # Атрибуты для хранения состояния ввода от SDL
        self.pressed_keys_sdl_state = None 
        self.sdl_events = [] 
        
        self.is_running = True

        self.a = 0
        self.b = 0
        
        # --- Управление сборщиком мусора ---
        self.enable_gc_management = True 
        if self.enable_gc_management:
            gc.disable() 
            self.frame_counter_gc = 0
            self.gc_time_gen0 = 0.0
            self.gc_time_gen1 = 0.0
            self.gc_time_gen2 = 0.0
            self.INTERVAL_GEN0 = 60    
            self.INTERVAL_GEN1 = 1800  
            self.INTERVAL_GEN2 = 7200  
            print("Manual Garbage Collection enabled.")
        else:
            gc.enable() 
            print("Automatic Garbage Collection enabled.")

        # --- Инициализация компонентов движка ---
        try:
            self.on_init() 
        except Exception as e_on_init:
            print(f"CRITICAL: Error during Engine.on_init(): {e_on_init}")
            import traceback
            traceback.print_exc()
            self.cleanup_and_exit()

    @main_profiler
    def on_init(self):
        """Инициализация игровых объектов и рендерера."""
        self.player = Player(self) # Player должен быть адаптирован к self.delta_time и SDL вводу
        
        # Renderer создаст окно SDL и вернет его фактические размеры
        # Передаем Engine instance (self), запрашиваемые параметры окна и цвет фона
        self.renderer = Renderer(self, 
                                 self.requested_win_width, 
                                 self.requested_win_height, 
                                 self.fullscreen_requested,
                                 "3D Engine (SDL)", # Начальный заголовок окна
                                 self.initial_bg_color
                                )
        
        # self.current_win_width и self.current_win_height должны быть обновлены Renderer'ом
        # через self.update_resolution_dependent_settings в его __init__

        # Настройка мыши через Renderer (SDL)
        if self.renderer:
            self.renderer.set_relative_mouse_mode(True) # Для first-person камеры
            self.renderer.set_mouse_visible(False)
            # self.renderer.set_window_grab(True) # Опционально, если нужно жесткое удержание
        else:
            print("CRITICAL: Renderer not available in on_init for mouse/window setup.")
            self.cleanup_and_exit(1)


        self.scene = Scene(self) # Scene может использовать self.renderer для добавления объектов
        
        # projection_matrix создается/обновляется в update_resolution_dependent_settings,
        # который вызывается из Renderer.__init__ после определения фактических размеров окна.
        # На случай, если что-то пошло не так, можно создать дефолтную:
        if not hasattr(self, 'projection_matrix'):
            print("Warning: Projection matrix not set by Renderer. Creating default.")
            current_aspect_ratio = self.current_win_width / self.current_win_height if self.current_win_height > 0 else (WIN_RES.x / WIN_RES.y if WIN_RES.y > 0 else 1.0)
            self.projection_matrix = self.create_projection_matrix(current_aspect_ratio) 
        
        print("Engine components initialized.")
        
    def create_projection_matrix(self, aspect_ratio_val):
        """Создает проекционную матрицу на основе текущих настроек FOV, соотношения сторон и плоскостей отсечения."""
        try:
            # FOV_DEG, NEAR, FAR берутся из settings.py
            return glm.perspective(glm.radians(FOV_DEG), aspect_ratio_val, NEAR, FAR)
        except Exception as e:
            print(f"Error creating projection matrix with aspect ratio {aspect_ratio_val}: {e}")
            return glm.mat4(1.0) # Возвращаем единичную матрицу в случае ошибки

    def update_resolution_dependent_settings(self, new_width, new_height):
        """Вызывается Renderer'ом при инициализации или изменении размера окна SDL."""
        print(f"Engine: Updating resolution-dependent settings to {new_width}x{new_height}")
        self.current_win_width = new_width
        self.current_win_height = new_height

        if self.current_win_height > 0:
            current_aspect_ratio = self.current_win_width / self.current_win_height
        else:
            # Fallback, если высота некорректна
            current_aspect_ratio = self.requested_win_width / self.requested_win_height if self.requested_win_height > 0 else 1.0
            print(f"Warning: Invalid new_height ({new_height}). Using fallback aspect ratio: {current_aspect_ratio}")

        self.projection_matrix = self.create_projection_matrix(current_aspect_ratio)
        print(f"Engine: Recreated projection matrix with new aspect ratio: {current_aspect_ratio:.2f}")
        
        # Если есть другие компоненты, зависящие от разрешения (например, UI элементы, рассчитывающие свои позиции),
        # их нужно обновить здесь.

    def calculate_session_stats(self):
        if self.total_time > 0:
            average_fps = self.total_frames / self.total_time
            print(f"Средний FPS: {average_fps:.2f}")
            print(f"Общее время сессии: {self.total_time:.2f} секунд")
        else:
            print("Сессия ещё не начата.")

    @main_profiler
    def update(self):
        self.player.update() # Player.update теперь в основном обновляет векторы камеры
        self.scene.update() 

        self.delta_time = self.clock.tick(MAX_FPS if 'MAX_FPS' in globals() else 0) / 1000.0 
        
        if(DEBUG_SESSION_FPS):
            self.total_frames += 1
            self.total_time += self.delta_time
        
        # Обновление заголовка окна FPS удалено по запросу.
        self.a += self.clock.get_fps()
        self.b += 1
        d = 128
        if self.b >= d:
            if self.renderer:
                self.renderer.set_window_title(f'{self.a/d:.0f} FPS')
                self.a = 0
                self.b = 0
        
    @main_profiler
    def render(self):
        if not self.renderer: 
            print("Error: Renderer not available in Engine.render()")
            return

        # Подготовка C++ стороны рендерера (передача матриц и флагов)
        if hasattr(self.renderer, 'prepare_for_new_frame') and callable(self.renderer.prepare_for_new_frame):
            self.renderer.prepare_for_new_frame()
        else:
            print("ERROR: renderer.prepare_for_new_frame() is not available!")
            self.is_running = False 
            return

        # Рендеринг сцены (передача объектов в C++ для накопления треугольников)
        self.scene.render() 

        # Фактический вызов C++ функции для отрисовки накопленных треугольников через SDL
        if hasattr(self.renderer, 'render') and callable(self.renderer.render):
            self.renderer.render() 
        else:
            print("ERROR: renderer.render() is not available!")
            self.is_running = False
            return
        
        # --- РИСОВАНИЕ UI СРЕДСТВАМИ PYGAME УДАЛЕНО ---
        # pg.display.flip() также не нужен, SDL управляет отображением.

    @main_profiler
    def handle_events(self):
        if not self.renderer:
            # Базовая обработка выхода, если рендерер недоступен
            for event in pg.event.get(): # pg.event.get() для не-оконных событий Pygame
                if event.type == pg.QUIT:
                    self.is_running = False
            return

        # Получаем события и состояние клавиатуры от SDL через Renderer
        self.sdl_events = self.renderer.poll_sdl_events()
        self.pressed_keys_sdl_state = self.renderer.get_keyboard_state() 

        # Передаем ввод игроку (Player должен иметь метод handle_input_sdl)
        if hasattr(self.player, 'handle_input_sdl'): 
            self.player.handle_input_sdl(self.sdl_events, self.pressed_keys_sdl_state, self.delta_time)
        
        # Обработка системных событий SDL (выход, изменение размера окна и т.д.)
        for event_data in self.sdl_events: # sdl_events - это список словарей
            event_type = event_data.get('type')
            if event_type == 'QUIT':
                self.is_running = False
                break
            if event_type == 'KEYDOWN':
                # SDL_SCANCODE_ESCAPE = 41 (пример, лучше иметь константы)
                if event_data.get('scancode') == 41: # SDL_SCANCODE_ESCAPE
                    self.is_running = False
                    break
            if event_type == 'WINDOWEVENT':
                if event_data.get('event_id') == SDL_WINDOWEVENT_RESIZED or \
                   event_data.get('event_id') == SDL_WINDOWEVENT_SIZE_CHANGED:
                    new_w = event_data.get('data1', self.current_win_width)
                    new_h = event_data.get('data2', self.current_win_height)
                    if new_w != self.current_win_width or new_h != self.current_win_height:
                        print(f"Engine: Detected SDL WINDOWEVENT_SIZE_CHANGED/RESIZED to {new_w}x{new_h}")
                        self.update_resolution_dependent_settings(new_w, new_h)
        
        # Дополнительно обрабатываем события Pygame, не связанные с окном (джойстик, аудио и т.д.)
        for event in pg.event.get():
            if event.type == pg.QUIT: # Общее событие Pygame QUIT на всякий случай
                self.is_running = False
            # Здесь можно добавить обработку других событий Pygame
            # if hasattr(self.player, 'handle_other_pygame_event'):
            #    self.player.handle_other_pygame_event(event, self.delta_time)

    @main_profiler
    def manage_gc(self):
        if not self.enable_gc_management:
            return
        self.frame_counter_gc +=1
        collected_this_frame = False
        if self.frame_counter_gc % self.INTERVAL_GEN0 == 0:
            start_time = time.perf_counter()
            gc.collect(0)
            self.gc_time_gen0 = (time.perf_counter() - start_time) * 1000
            collected_this_frame = True
        if self.frame_counter_gc % self.INTERVAL_GEN1 == 0 and not collected_this_frame:
            start_time = time.perf_counter()
            gc.collect(1) 
            self.gc_time_gen1 = (time.perf_counter() - start_time) * 1000
            collected_this_frame = True
        if self.frame_counter_gc % self.INTERVAL_GEN2 == 0 and not collected_this_frame:
            start_time = time.perf_counter()
            gc.collect(2) 
            self.gc_time_gen2 = (time.perf_counter() - start_time) * 1000
        if self.frame_counter_gc > max(self.INTERVAL_GEN0, self.INTERVAL_GEN1, self.INTERVAL_GEN2) * 10:
             self.frame_counter_gc = 0

    def cleanup_and_exit(self, exit_code=0): # Изменено на exit_code=0 по умолчанию для чистого выхода
        """Централизованная функция для очистки и выхода."""
        if(DEBUG_SESSION_FPS):
            self.calculate_session_stats()
        print("Engine attempting cleanup and exit...")
        # cleanup_cpp_renderer вызывается через atexit в Renderer,
        # поэтому здесь его вызывать не обязательно, если atexit надежен.
        pg.quit() # Завершаем работу Pygame модулей (важно для аудио, джойстика и т.д.)
        sys.exit(exit_code)

    @main_profiler
    def run(self):
        try:
            while self.is_running:
                self.handle_events()
                self.update()
                self.render()
                if self.enable_gc_management: self.manage_gc()
        
        except KeyboardInterrupt: 
            print("\nKeyboardInterrupt caught. Exiting gracefully...")
            self.is_running = False 
        except Exception as e_main_loop:
            print(f"CRITICAL ERROR in main loop: {e_main_loop}")
            import traceback
            traceback.print_exc()
            self.is_running = False 
        finally:
            if PROFILER_ENABLED and callable(profiler_report):
                try:
                    profiler_report()
                except Exception as e_profiler:
                    print(f"Error generating profiler report: {e_profiler}")
            
            # Выход с кодом 0, если is_running все еще True (нормальное завершение цикла, например, по ESC)
            # или 1, если is_running стал False из-за ошибки или KeyboardInterrupt.
            # Однако, если KeyboardInterrupt или ошибка в цикле, is_running уже будет False.
            self.cleanup_and_exit(0 if self.is_running else 1) 

if __name__ == '__main__':
    if sys.platform.startswith('win'):
         multiprocessing.freeze_support()
    
    try:     
        app = Engine(requested_size=WIN_RES, 
                     requested_fullscreen=FULLSCREEN, 
                     initial_bg_color_glm=BG_COLOR)
        app.run()
    except SystemExit as e: # SystemExit не является ошибкой, которую нужно логировать как "CRITICAL"
        # sys.exit() бросает SystemExit, поэтому ловим его, чтобы не печатать лишнее сообщение
        # и позволяем приложению завершиться с кодом, который был передан в sys.exit()
        if e.code is None or e.code == 0:
             pass # Чистый выход
        else:
             print(f"Application exited with code: {e.code}")
             # Если нужно, можно перевыбросить или выйти с тем же кодом
             # sys.exit(e.code) 
    except Exception as e_app_init_run:
        print(f"CRITICAL ERROR during Engine initialization or run: {e_app_init_run}")
        import traceback
        traceback.print_exc()
        if pg.get_init():
            pg.quit()
        sys.exit(1)