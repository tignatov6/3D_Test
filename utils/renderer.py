# renderer.py
import pygame # Pygame все еще может использоваться для других целей (например, pg.time.Clock в Engine)
import numpy as np
from settings import * # Загружаем все настройки (FOV_DEG, NEAR, FAR и т.д. нужны для prepare_for_new_frame)
import glm
import sys 
import atexit # Для вызова cleanup_cpp_renderer при выходе
# import time # time не используется напрямую в этом файле

# --- Попытка импорта C++ модуля ---
try:
    import cpp_renderer_core
    CPP_MODULE_LOADED = True
    print(f"--- Модуль cpp_renderer_core успешно загружен! ({cpp_renderer_core.__file__}) ---")
except ImportError as e:
    print(f"--- КРИТИЧЕСКАЯ ОШИБКА: Не удалось импортировать модуль cpp_renderer_core: {e} ---")
    print("--- Убедитесь, что вы скомпилировали модуль командой: python setup.py build_ext --inplace ---")
    print("--- Также проверьте, что все зависимости C++ модуля (например, SDL2.dll) доступны. ---")
    print("--- Работа приложения будет прекращена. ---")
    CPP_MODULE_LOADED = False
    sys.exit(1) # Критическая ошибка, выходим

# Профайлер, если используется
try:
    from utils.profiler import get_profiler
    profiler = get_profiler(__name__)
except ImportError:
    def profiler_dummy_decorator(func): return func # Заглушка
    profiler = profiler_dummy_decorator 
    print("Warning: Profiler (utils.profiler) not found for renderer.py. Using dummy profiler.")


class Renderer:
    def __init__(self, app_instance, initial_width: int, initial_height: int, 
                 fullscreen_flag: bool, window_title: str, bg_color_glm: glm.vec3):
        global CPP_MODULE_LOADED
        if not CPP_MODULE_LOADED:
            # Эта проверка дублируется, но на всякий случай, если объект создается без предварительной проверки
            print("CRITICAL: cpp_renderer_core module not loaded. Renderer cannot function.")
            sys.exit(1)

        self.app = app_instance # Ссылка на главный класс Engine
        
        try:
            # Пытаемся получить камеру из app.camera или app.player
            self.camera = getattr(self.app, 'camera', getattr(self.app, 'player', None))
            if self.camera is None:
                raise AttributeError("Camera object not found in app instance (app.player or app.camera).")
        except AttributeError as e:
            print(f"CRITICAL ERROR in Renderer __init__: {e}")
            sys.exit(1)

        # Настройки, передаваемые в C++ при инициализации или для кадра
        self.clipping_setting = CLIPPING # из settings.py
        self.debug_clipping_setting = DEBUG_CLIPPING # из settings.py
        self.debug_color_clipped_list_uint8 = np.array([255, 0, 255], dtype=np.uint8) # Розовый

        self.bg_clear_color_tuple_uint8 = np.array([
            int(bg_color_glm.x * 255), 
            int(bg_color_glm.y * 255), 
            int(bg_color_glm.z * 255)
        ], dtype=np.uint8)

        self.sort_in_cpp = SORT # из settings.py
        self.small_feature_culling_enabled = SMALL_TRIANGLE_CULLING_ENABLED
        self.small_triangle_min_area = SMALL_TRIANGLE_MIN_AREA if self.small_feature_culling_enabled else 0.0

        self.max_l1_cache_size_for_cpp = MAX_L1_CACHE_SIZE_CPP
        self.max_l2_cache_size_for_cpp = MAX_L2_CACHE_SIZE_CPP
        
        self.actual_window_width = 0
        self.actual_window_height = 0

        # --- Инициализация C++ рендерера (SDL окно создается здесь) ---
        try:
            # cpp_renderer_core.initialize_cpp_renderer теперь возвращает (actual_width, actual_height)
            returned_dimensions = cpp_renderer_core.initialize_cpp_renderer(
                initial_width,
                initial_height,
                fullscreen_flag,
                window_title,
                self.max_l1_cache_size_for_cpp,
                self.max_l2_cache_size_for_cpp,
                self.bg_clear_color_tuple_uint8
            )
            self.actual_window_width = returned_dimensions[0]
            self.actual_window_height = returned_dimensions[1]
            print(f"Python Renderer: Actual SDL window dimensions from C++: {self.actual_window_width}x{self.actual_window_height}")

            # Обновляем Engine с фактическими размерами окна
            if hasattr(self.app, 'update_resolution_dependent_settings'):
                self.app.update_resolution_dependent_settings(self.actual_window_width, self.actual_window_height)
            else:
                print("Warning: app instance does not have 'update_resolution_dependent_settings' method.")
            
            print("--- C++ Renderer (SDL) initialized successfully with its own window. ---")
            # Регистрируем функцию очистки C++ ресурсов при выходе из Python
            atexit.register(self.cleanup_on_exit)

        except RuntimeError as e_init_cpp:
            print(f"--- КРИТИЧЕСКАЯ ОШИБКА при инициализации C++ рендерера: {e_init_cpp} ---")
            CPP_MODULE_LOADED = False 
            sys.exit(1) 
        except Exception as e_init_general: # Ловим другие возможные исключения
            print(f"--- НЕПРЕДВИДЕННАЯ ОШИБКА при инициализации C++ рендерера: {e_init_general} ---")
            CPP_MODULE_LOADED = False
            sys.exit(1)
            
    def cleanup_on_exit(self):
        """Вызывается автоматически при завершении работы Python для очистки C++ ресурсов."""
        if CPP_MODULE_LOADED and hasattr(cpp_renderer_core, 'cleanup_cpp_renderer'):
            try:
                print("--- Python Renderer: Initiating C++ renderer cleanup... ---")
                cpp_renderer_core.cleanup_cpp_renderer()
                print("--- Python Renderer: C++ renderer resources cleaned up. ---")
            except Exception as e:
                print(f"Error during C++ renderer cleanup from Python: {e}")
    
    @profiler
    def prepare_for_new_frame(self):
        """Готовит C++ сторону к новому кадру, передавая необходимые параметры."""
        if not CPP_MODULE_LOADED: return

        view_matrix_np = np.array(self.camera.get_view_matrix(), dtype=np.float32).flatten(order='F')
        
        # Убедимся, что self.app.projection_matrix существует и актуальна
        if not hasattr(self.app, 'projection_matrix') or self.app.projection_matrix is None:
            print("Warning: app.projection_matrix not found or is None in prepare_for_new_frame. Using identity matrix.")
            # Создаем дефолтную проекционную матрицу, если она отсутствует
            # Это может случиться, если update_resolution_dependent_settings не был вызван или не сработал корректно.
            fallback_aspect_ratio = self.actual_window_width / self.actual_window_height if self.actual_window_height > 0 else (16.0/9.0)
            projection_matrix = glm.perspective(glm.radians(FOV_DEG), fallback_aspect_ratio, NEAR, FAR)
            projection_matrix_np = np.array(projection_matrix, dtype=np.float32).flatten(order='F')
        else:
            projection_matrix_np = np.array(self.app.projection_matrix, dtype=np.float32).flatten(order='F')

        camera_pos_w_np = np.array([self.camera.position.x, self.camera.position.y, self.camera.position.z], dtype=np.float32)
        current_small_tri_thresh = self.small_triangle_min_area if self.small_feature_culling_enabled else 0.0

        try:
            cpp_renderer_core.set_frame_parameters_cpp(
                view_matrix_np,
                projection_matrix_np,
                camera_pos_w_np,
                LIGHT,  # из settings.py
                BACK_CULL, # из settings.py
                self.clipping_setting,
                self.debug_clipping_setting,
                self.debug_color_clipped_list_uint8,
                self.sort_in_cpp,
                current_small_tri_thresh
            )
        except RuntimeError as e_set_params:
            print(f"RuntimeError in set_frame_parameters_cpp: {e_set_params}")
        except Exception as e_set_params_general:
            print(f"Unexpected error in set_frame_parameters_cpp: {e_set_params_general}")

    @profiler
    def render_mesh(self, 
                    object_id: int, 
                    vertex_data_np: np.ndarray, 
                    vertex_data_format_info: dict, 
                    position: glm.vec3 = glm.vec3(0,0,0),
                    rotation: glm.vec3 = glm.vec3(0,0,0), 
                    scale: glm.vec3 = glm.vec3(1,1,1)):
        """Передает данные объекта в C++ для обработки и накопления треугольников."""
        if not CPP_MODULE_LOADED: return
        if vertex_data_np.size == 0: return 

        transform_params_list = [
            position.x, position.y, position.z,
            rotation.x, rotation.y, rotation.z, 
            scale.x, scale.y, scale.z
        ]
        transform_params_np = np.array(transform_params_list, dtype=np.float32)
        
        use_vertex_normals_setting = vertex_data_format_info.get('USE_VERTEX_NORMALS', USE_VERTEX_NORMALS) # Fallback to settings
        vertex_stride = vertex_data_format_info.get('VERTEX_DATA_STRIDE', VERTEX_DATA_STRIDE) # Fallback to settings

        try:
            # GIL будет отпущен внутри этой C++ функции, если там используется py::gil_scoped_release
            cpp_renderer_core.process_and_accumulate_object_cpp(
                object_id,
                transform_params_np,
                vertex_data_np, 
                vertex_stride,
                use_vertex_normals_setting
            )
        except RuntimeError as e_cpp_process:
            print(f"КРИТИЧЕСКАЯ ОШИБКА Runtime в C++ (process_and_accumulate) для объекта {object_id}: {e_cpp_process}")
        except Exception as e_cpp_general_process:
            print(f"ОБЩАЯ ОШИБКА при вызове C++ (process_and_accumulate) для объекта {object_id}: {e_cpp_general_process}")

    @profiler
    def render(self): 
        """Вызывает C++ функцию для рендеринга всех накопленных треугольников с использованием SDL."""
        if not CPP_MODULE_LOADED: return

        try:
            # GIL будет отпущен внутри этой C++ функции, если там используется py::gil_scoped_release
            cpp_renderer_core.render_accumulated_triangles_cpp()
        except RuntimeError as e_render_cpp:
            print(f"КРИТИЧЕСКАЯ ОШИБКА Runtime в C++ (render_accumulated_triangles_cpp): {e_render_cpp}")
        except Exception as e_render_general:
            print(f"ОБЩАЯ ОШИБКА при вызове C++ (render_accumulated_triangles_cpp): {e_render_general}")

    # --- Методы-обертки для новых C++ функций управления окном и вводом ---

    def set_window_title(self, title: str):
        if CPP_MODULE_LOADED and hasattr(cpp_renderer_core, 'set_window_title_cpp'):
            try:
                cpp_renderer_core.set_window_title_cpp(title)
            except Exception as e:
                print(f"Error calling set_window_title_cpp: {e}")
        else: self._warn_cpp_function_missing("set_window_title_cpp")


    def set_relative_mouse_mode(self, active: bool):
        if CPP_MODULE_LOADED and hasattr(cpp_renderer_core, 'set_relative_mouse_mode_cpp'):
            try:
                cpp_renderer_core.set_relative_mouse_mode_cpp(active)
            except Exception as e:
                print(f"Error calling set_relative_mouse_mode_cpp: {e}")
        else: self._warn_cpp_function_missing("set_relative_mouse_mode_cpp")

    def set_mouse_visible(self, visible: bool):
        if CPP_MODULE_LOADED and hasattr(cpp_renderer_core, 'set_mouse_visible_cpp'):
            try:
                cpp_renderer_core.set_mouse_visible_cpp(visible)
            except Exception as e:
                print(f"Error calling set_mouse_visible_cpp: {e}")
        else: self._warn_cpp_function_missing("set_mouse_visible_cpp")

    def set_window_grab(self, grab_on: bool):
        if CPP_MODULE_LOADED and hasattr(cpp_renderer_core, 'set_window_grab_cpp'):
            try:
                cpp_renderer_core.set_window_grab_cpp(grab_on)
            except Exception as e:
                print(f"Error calling set_window_grab_cpp: {e}")
        else: self._warn_cpp_function_missing("set_window_grab_cpp")
        
    def poll_sdl_events(self) -> list:
        if CPP_MODULE_LOADED and hasattr(cpp_renderer_core, 'poll_sdl_events_cpp'):
            try:
                return cpp_renderer_core.poll_sdl_events_cpp()
            except Exception as e:
                print(f"Error calling poll_sdl_events_cpp: {e}")
                return []
        else: 
            self._warn_cpp_function_missing("poll_sdl_events_cpp")
            return []

    def get_keyboard_state(self) -> bytes: # Ожидаем bytes от C++
        if CPP_MODULE_LOADED and hasattr(cpp_renderer_core, 'get_keyboard_state_cpp'):
            try:
                state = cpp_renderer_core.get_keyboard_state_cpp()
                if not isinstance(state, bytes): # Дополнительная проверка типа
                    print(f"Warning: get_keyboard_state_cpp did not return bytes, got {type(state)}")
                    return b'' # Возвращаем пустые байты в случае ошибки
                return state
            except Exception as e:
                print(f"Error calling get_keyboard_state_cpp: {e}")
                return b''
        else: 
            self._warn_cpp_function_missing("get_keyboard_state_cpp")
            return b'' # Возвращаем пустые байты, если функция отсутствует

    def get_mouse_state(self) -> tuple: # Ожидаем (x, y, button_mask)
        if CPP_MODULE_LOADED and hasattr(cpp_renderer_core, 'get_mouse_state_cpp'):
            try:
                return cpp_renderer_core.get_mouse_state_cpp()
            except Exception as e:
                print(f"Error calling get_mouse_state_cpp: {e}")
                return (0, 0, 0)
        else: 
            self._warn_cpp_function_missing("get_mouse_state_cpp")
            return (0, 0, 0) # Возвращаем дефолтные значения

    def get_relative_mouse_state(self) -> tuple: # Ожидаем (xrel, yrel)
        if CPP_MODULE_LOADED and hasattr(cpp_renderer_core, 'get_relative_mouse_state_cpp'):
            try:
                return cpp_renderer_core.get_relative_mouse_state_cpp()
            except Exception as e:
                print(f"Error calling get_relative_mouse_state_cpp: {e}")
                return (0, 0)
        else: 
            self._warn_cpp_function_missing("get_relative_mouse_state_cpp")
            return (0, 0) # Возвращаем дефолтные значения

    def _warn_cpp_function_missing(self, func_name: str):
        """Вспомогательная функция для предупреждения об отсутствующей C++ функции."""
        print(f"Warning: C++ function '{func_name}' not found in cpp_renderer_core module.")

    # --- Helper for color unpacking ---
    def _unpack_color(self, color: tuple, default_alpha: int = 255) -> tuple:
        """Unpacks an RGB or RGBA color tuple into (r, g, b, a), defaulting alpha if not present."""
        if len(color) == 3:
            return (color[0], color[1], color[2], default_alpha)
        elif len(color) == 4:
            return color
        else:
            # Fallback for invalid color tuple, though Pygame colors are usually well-formed
            print(f"Warning: Invalid color tuple received: {color}. Defaulting to black.")
            return (0, 0, 0, default_alpha)

    # --- UI Element C++ Wrappers ---
    @profiler
    def create_or_update_button(self, element_id: str, rect: pygame.Rect, text: str, 
                                bg_color: tuple, text_color: tuple, 
                                border_color: tuple | None, border_width: int, 
                                visible: bool, font_size: int): # Added font_size
        if not CPP_MODULE_LOADED or not hasattr(cpp_renderer_core, 'create_or_update_button_cpp'):
            self._warn_cpp_function_missing("create_or_update_button_cpp")
            return

        bg_r, bg_g, bg_b, bg_a = self._unpack_color(bg_color)
        txt_r, txt_g, txt_b, txt_a = self._unpack_color(text_color)
        
        if border_color and border_width > 0:
            brd_r, brd_g, brd_b, brd_a = self._unpack_color(border_color)
        else:
            brd_r, brd_g, brd_b, brd_a = (0, 0, 0, 0) # Default non-visible border
            border_width = 0 # Ensure border_width is 0 if no color

        try:
            cpp_renderer_core.create_or_update_button_cpp(
                element_id, rect.x, rect.y, rect.w, rect.h,
                text,
                bg_r, bg_g, bg_b, bg_a,
                txt_r, txt_g, txt_b, txt_a,
                brd_r, brd_g, brd_b, brd_a,
                border_width, visible,
                font_size # Pass font_size to C++
            )
        except Exception as e:
            print(f"Error calling create_or_update_button_cpp for ID {element_id}: {e}")

    @profiler
    def create_or_update_text_label(self, element_id: str, rect: pygame.Rect, text: str, 
                                    text_color: tuple, font_size: int, visible: bool):
        if not CPP_MODULE_LOADED or not hasattr(cpp_renderer_core, 'create_or_update_text_label_cpp'):
            self._warn_cpp_function_missing("create_or_update_text_label_cpp")
            return

        txt_r, txt_g, txt_b, txt_a = self._unpack_color(text_color)
        
        # C++ side uses a default font size if font_size <= 0
        effective_font_size = font_size if font_size > 0 else 0 

        try:
            cpp_renderer_core.create_or_update_text_label_cpp(
                element_id, rect.x, rect.y, rect.w, rect.h,
                text,
                txt_r, txt_g, txt_b, txt_a,
                effective_font_size, visible
            )
        except Exception as e:
            print(f"Error calling create_or_update_text_label_cpp for ID {element_id}: {e}")

    @profiler
    def create_or_update_panel(self, element_id: str, rect: pygame.Rect,
                               bg_color: tuple, border_color: tuple, # border_color теперь ожидается как кортеж
                               border_width: int, visible: bool):
        if not CPP_MODULE_LOADED or not hasattr(cpp_renderer_core, 'create_or_update_panel_cpp'):
            self._warn_cpp_function_missing("create_or_update_panel_cpp")
            return

        bg_r, bg_g, bg_b, bg_a = self._unpack_color(bg_color)
        
        # border_color уже должен быть кортежем (r,g,b,a) из Panel,
        # или (0,0,0,0) если он был None и border_width > 0.
        # Если border_width == 0, то цвет рамки не важен.
        brd_r, brd_g, brd_b, brd_a = self._unpack_color(border_color if border_width > 0 else (0,0,0,0))
        
        effective_border_width = border_width if border_color[3] > 0 else 0 # Не рисуем рамку, если она полностью прозрачна

        try:
            cpp_renderer_core.create_or_update_panel_cpp(
                element_id, rect.x, rect.y, rect.w, rect.h,
                bg_r, bg_g, bg_b, bg_a,
                brd_r, brd_g, brd_b, brd_a,
                effective_border_width, # Используем effective_border_width
                visible
            )
        except Exception as e:
            print(f"Error calling create_or_update_panel_cpp for ID {element_id}: {e}")

    @profiler
    def remove_ui_element(self, element_id: str):
        if not CPP_MODULE_LOADED or not hasattr(cpp_renderer_core, 'remove_ui_element_cpp'):
            self._warn_cpp_function_missing("remove_ui_element_cpp")
            return
        try:
            cpp_renderer_core.remove_ui_element_cpp(element_id)
        except Exception as e:
            print(f"Error calling remove_ui_element_cpp for ID {element_id}: {e}")

    @profiler
    def set_ui_element_visibility(self, element_id: str, visible: bool):
        if not CPP_MODULE_LOADED or not hasattr(cpp_renderer_core, 'set_ui_element_visibility_cpp'):
            self._warn_cpp_function_missing("set_ui_element_visibility_cpp")
            return
        try:
            cpp_renderer_core.set_ui_element_visibility_cpp(element_id, visible)
        except Exception as e:
            print(f"Error calling set_ui_element_visibility_cpp for ID {element_id}: {e}")


    def set_window_title(self, title: str):
        if CPP_MODULE_LOADED and hasattr(cpp_renderer_core, 'set_window_title_cpp'):
            try:
                cpp_renderer_core.set_window_title_cpp(title)
            except Exception as e:
                print(f"Error calling set_window_title_cpp: {e}")
        else: 
            self._warn_cpp_function_missing("set_window_title_cpp")