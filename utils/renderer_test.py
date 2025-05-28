# renderer_C.py
import pygame
import numpy as np
from settings import * # Загружаем все настройки
import random
from utils.profiler import get_profiler 
import collections
import glm
import sys 

# --- Попытка импорта C++ модуля ---
try:
    import cpp_renderer_core
    CPP_MODULE_LOADED = True
    print(f"--- Модуль cpp_renderer_core успешно загружен! ({cpp_renderer_core.__file__}) ---")
except ImportError as e:
    print(f"--- КРИТИЧЕСКАЯ ОШИБКА: Не удалось импортировать модуль cpp_renderer_core: {e} ---")
    print("--- Убедитесь, что вы скомпилировали модуль командой: python setup.py build_ext --inplace ---")
    print("--- Также проверьте, что все зависимости C++ модуля (например, DLL GLM, если она нужна) доступны. ---")
    print("--- Работа приложения будет прекращена. ---")
    CPP_MODULE_LOADED = False
    sys.exit(1) 

profiler = get_profiler(__name__)

class Renderer:
    def __init__(self, app):
        self.app = app
        self.screen = app.window
        try:
            self.camera = app.camera
        except AttributeError:
            self.camera = app.player

        self.triangles_to_draw = [] # Основной список для треугольников, готовых к отрисовке

        # --- Кэш L1 (Python-сайд, кэширует результат вызова C++ функции) ---
        self.full_render_cache = {} 
        self.max_full_cache_size = MAX_FULL_CACHE_SIZE # Из settings.py
        self.full_cache_lru = collections.OrderedDict()
        
        self.current_frame_camera_key_part = None
        self.current_frame_projection_key_part = None
        self.current_frame_other_common_flags = None

        # Настройки, используемые для ключа кэша или передаваемые в C++
        self.clipping_setting = CLIPPING
        self.debug_clipping_setting = DEBUG_CLIPPING if 'DEBUG_CLIPPING' in globals() else False
        self.debug_color_clipped_list_uint8 = [255, 0, 255] # Розовый

        self.bg_clear_color_tuple = (int(BG_COLOR.x*255), int(BG_COLOR.y*255), int(BG_COLOR.z*255))

        # Настройки для C++ ядра
        self.sort_in_cpp = SORT 
        self.small_feature_culling_enabled = True # По умолчанию True
        self.small_triangle_min_area = 1.0  # Порог площади в пикселях
        
        # Размер для внутреннего L2 кэша в C++
        # Можно использовать значение из settings.py, если оно там есть, или MAX_FULL_CACHE_SIZE
        self.max_l2_cache_size_for_cpp = getattr(sys.modules[__name__], 'MAX_L2_CACHE_SIZE', MAX_FULL_CACHE_SIZE)
        # Флаг для однократной передачи размера кэша (если C++ кэш не должен менять размер на лету)
        # В текущей C++ реализации `global_l2_cache_capacity_set` управляет этим.

    def _get_matrix_tuple(self, matrix_glm: glm.mat4) -> tuple:
        if matrix_glm is None: return None
        return tuple(tuple(matrix_glm[i]) for i in range(4))

    def _prepare_frame_cache_keys(self): # Готовит ключи для L1 кэша
        self.current_frame_camera_key_part = self._get_matrix_tuple(self.camera.get_view_matrix())
        self.current_frame_projection_key_part = self._get_matrix_tuple(self.app.projection_matrix)
        self.current_frame_other_common_flags = (
            LIGHT, BACK_CULL, self.clipping_setting,
            WIN_RES.x, WIN_RES.y, self.debug_clipping_setting,
            self.sort_in_cpp,
            self.small_feature_culling_enabled,
            self.small_triangle_min_area if self.small_feature_culling_enabled else 0.0
        )

    def _cleanup_full_render_cache(self): # L1 Cache cleanup
        while len(self.full_render_cache) > self.max_full_cache_size:
            try:
                oldest_key, _ = self.full_cache_lru.popitem(last=False)
                if oldest_key in self.full_render_cache:
                    del self.full_render_cache[oldest_key]
            except KeyError: break

    def _update_full_cache_lru(self, cache_key): # L1 Cache update
        if cache_key in self.full_cache_lru:
            self.full_cache_lru.move_to_end(cache_key, last=True)
        else:
            self.full_cache_lru[cache_key] = None
            if len(self.full_cache_lru) > self.max_full_cache_size:
                 self._cleanup_full_render_cache()

    @profiler
    def prepare_for_new_frame(self):
        self._prepare_frame_cache_keys() 
        self.triangles_to_draw = []

    @profiler
    def render_mesh(self, object_id: int, vertex_data_np: np.ndarray,
                    vertex_data_format_info: dict,
                    position: glm.vec3 = glm.vec3(0,0,0),
                    rotation: glm.vec3 = glm.vec3(0,0,0),
                    scale: glm.vec3 = glm.vec3(1,1,1)):
        if not CPP_MODULE_LOADED: return

        if self.current_frame_other_common_flags is None:
            self._prepare_frame_cache_keys()

        obj_transform_params_tuple = (position.x, position.y, position.z,
                                      rotation.x, rotation.y, rotation.z,
                                      scale.x, scale.y, scale.z)
        use_vertex_normals_setting = vertex_data_format_info['USE_VERTEX_NORMALS']
        
        specific_flags_for_l1_key = self.current_frame_other_common_flags + (use_vertex_normals_setting,)
        
        cache_key_l1 = (object_id, obj_transform_params_tuple,
                        self.current_frame_camera_key_part,
                        self.current_frame_projection_key_part,
                        specific_flags_for_l1_key)

        cached_screen_triangles = self.full_render_cache.get(cache_key_l1)
        if cached_screen_triangles is not None:
            with profiler("L1_Cache_Hit_PySide"):
                self.triangles_to_draw.extend(cached_screen_triangles)
                self._update_full_cache_lru(cache_key_l1)
            return
        
        final_triangles_for_l1_cache = []

        with profiler("Prepare_CPP_Args_FullPipeline_PySide"):
            if vertex_data_np.size == 0: 
                self.full_render_cache[cache_key_l1] = []
                self._update_full_cache_lru(cache_key_l1)
                self._cleanup_full_render_cache()
                return

            transform_params_list = [
                position.x, position.y, position.z,
                rotation.x, rotation.y, rotation.z,
                scale.x, scale.y, scale.z
            ]
            transform_params_np = np.array(transform_params_list, dtype=np.float32)
            
            view_matrix_np_col_major = np.array(self.camera.get_view_matrix(), dtype=np.float32).T
            projection_matrix_np_col_major = np.array(self.app.projection_matrix, dtype=np.float32).T
            camera_pos_w_np = np.array([self.camera.position.x, self.camera.position.y, self.camera.position.z], dtype=np.float32)
            
            current_small_triangle_threshold = self.small_triangle_min_area if self.small_feature_culling_enabled else 0.0

        with profiler("Call_CPP_Full_Pipeline_PySide"):
            try:
                cpp_side_triangles_list = cpp_renderer_core.process_object_pipeline_cpp(
                    object_id, 
                    transform_params_np,
                    vertex_data_np,     
                    vertex_data_format_info['VERTEX_DATA_STRIDE'],
                    use_vertex_normals_setting,
                    view_matrix_np_col_major,
                    projection_matrix_np_col_major,
                    camera_pos_w_np,
                    LIGHT, BACK_CULL, self.clipping_setting,
                    self.debug_clipping_setting,
                    self.debug_color_clipped_list_uint8, # Передаем Python list
                    int(WIN_RES.x), int(WIN_RES.y),
                    self.sort_in_cpp,
                    current_small_triangle_threshold,
                    self.max_l2_cache_size_for_cpp 
                )
                
                for cpp_triangle_obj in cpp_side_triangles_list:
                    screen_coords_py = cpp_triangle_obj.screen_coords
                    depth_py = cpp_triangle_obj.depth
                    color_py = cpp_triangle_obj.color
                    final_triangles_for_l1_cache.append([screen_coords_py, depth_py, color_py])

            except RuntimeError as e_cpp_runtime:
                print(f"КРИТИЧЕСКАЯ ОШИБКА Runtime в C++ ядре (pipeline) для объекта {object_id}: {e_cpp_runtime}")
                final_triangles_for_l1_cache = []
            except Exception as e_cpp_general:
                print(f"ОБЩАЯ ОШИБКА при вызове C++ ядра (pipeline) для объекта {object_id}: {e_cpp_general}")
                final_triangles_for_l1_cache = []

        with profiler("Update_L1_Cache_PySide"):
            self.full_render_cache[cache_key_l1] = final_triangles_for_l1_cache
            self._update_full_cache_lru(cache_key_l1)
            self._cleanup_full_render_cache()

        self.triangles_to_draw.extend(final_triangles_for_l1_cache)

    @profiler
    def render(self): 
        with profiler("Py_Final_Draw_Loop"):
            if SORT and not self.sort_in_cpp and self.triangles_to_draw:
                with profiler("Py_Sort_Triangles_In_Render_IfNeeded"):
                    self.triangles_to_draw.sort(key=lambda item: item[1])
            
            for triangle_data in self.triangles_to_draw:
                screen_points_py_list, _, final_color_py_tuple = triangle_data
                if len(screen_points_py_list) == 3:
                    try:
                        current_render_color = (random.randint(0,255),random.randint(0,255),random.randint(0,255)) if RANDOM_COL else final_color_py_tuple
                        pygame.draw.polygon(self.screen, current_render_color, screen_points_py_list, 0)
                    except TypeError: pass
                    except Exception: pass