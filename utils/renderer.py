# Давайте дополним ваш рендерер для работы с мешами через Pygame. Основная задача — преобразовать 3D вершины в 2D экранные координаты и отрисовать треугольники.

# ### 1. **Класс рендерера (renderer.py)**
# ```python
import pygame
import numpy as np
from settings import *

def calculate_triangle_normal(v1, v2, v3):
<<<<<<< Updated upstream
    # Преобразуем вершины в векторы glm
    a = glm.vec3(v1)
    b = glm.vec3(v2)
    c = glm.vec3(v3)
=======
    """
    Calculates the normal vector of a triangle defined by three vertices.
    The normal is perpendicular to the triangle's surface and is used for culling and lighting.
    Args:
        v1, v2, v3: Tuple or list-like representing 3D vertex coordinates (e.g., (x, y, z)).
    Returns:
        A normalized glm.vec3 representing the triangle's normal.
    """
    print(f'DEBUG: v1 type: {type(v1)}, value: {v1}')
    # Explicitly convert vertex components to float before passing to glm.vec3
    # This is to ensure that glm.vec3 receives standard Python float types,
    # avoiding potential issues if components are, for example, numpy.float32 or other numeric types
    # that might not be directly compatible or could cause unexpected behavior with some glm versions/operations.
    v1_converted = (float(v1[0]), float(v1[1]), float(v1[2]))
    v2_converted = (float(v2[0]), float(v2[1]), float(v2[2]))
    v3_converted = (float(v3[0]), float(v3[1]), float(v3[2]))

    a = glm.vec3(v1_converted) # Convert to glm vectors for vector math
    b = glm.vec3(v2_converted)
    c = glm.vec3(v3_converted)
>>>>>>> Stashed changes
    
    # Вычисляем векторы сторон
    edge1 = b - a
    edge2 = c - a
    
    # Векторное произведение
    normal = glm.cross(edge1, edge2)
    
    # Нормализуем результат
    return glm.normalize(normal)

def is_front_facing(normal, camera_pos, triangle_center):
    # Вектор от центра треугольника к камере
    view_dir = glm.normalize(glm.vec3(camera_pos) - triangle_center)
    
    # Скалярное произведение нормали и направления взгляда
    return glm.dot(normal, view_dir) > 0


#Объекты должны добавляться в очередь на рендеринг с помощью макс числа потоков. Позже обрабатываться с помощью макс числа потоков, а потом отрисовываться. +Backwad Culling +Frustrum Culling +Z буффер +яркость от того, на сколько треугольник повёрнут на камеру.
class Renderer:
    def __init__(self, app):
        self.app = app
        self.screen = app.window
        self.printed = False
        try:
            self.camera = app.camera
        except:
<<<<<<< Updated upstream
            self.camera = app.player

    def project_vertex(self, vertex):
        """Преобразует 3D вершину в 2D экранные координаты."""
        # 1. Применяем видовую матрицу
        view_space = self.camera.get_view_matrix() @ glm.vec4(*vertex, 1.0)
=======
            self.camera = app.player # Fallback if app.camera is not defined
        
        # List to store processed triangles (depth, screen_coords, color) for Painter's Algorithm
        self.triangles_to_render = [] 
        
        # Counter for limiting debug prints of projected triangles per frame
        self.debug_triangles_printed_this_frame = 0
        # Counter for limiting debug prints of vertices within the first printed triangle
        self.debug_vertices_printed_this_triangle = 0
        
        # --- Multithreading Disabled ---
        # Counter for limiting debug prints of projected triangles per frame
        self.debug_triangles_printed_this_frame = 0
        # Counter for limiting debug prints of vertices within the first printed triangle
        self.debug_vertices_printed_this_triangle = 0
        
        # --- Multithreading Disabled ---
        # ThreadPoolExecutor for parallelizing triangle processing tasks
        # self.thread_pool = ThreadPoolExecutor(max_workers=N_THREADS)
        # self.thread_pool = ThreadPoolExecutor(max_workers=N_THREADS)
        
        # List to store Future objects from tasks submitted to the thread pool for the current frame
        # self.futures_list = []
        # --- Multithreading Disabled ---
        # self.futures_list = []
        # --- Multithreading Disabled ---

    @staticmethod
    def _project_vertex_static(vertex, view_matrix, projection_matrix, win_res, do_debug_print): # Added do_debug_print flag
    def _project_vertex_static(vertex, view_matrix, projection_matrix, win_res, do_debug_print): # Added do_debug_print flag
        """
        Static method to project a 3D vertex to 2D screen coordinates.
        Being static allows it to be called by threads without needing access to the Renderer's 'self' instance,
        or if 'self' were passed, it would simplify dependency management for this specific projection task.
        Args:
            vertex (tuple): The 3D coordinates of the vertex (x, y, z).
            view_matrix (glm.mat4): The camera's view matrix.
            projection_matrix (glm.mat4): The projection matrix.
            win_res (tuple): The window resolution (width, height) from settings (WIN_RES).
            do_debug_print (bool): Flag to enable printing of debug information for this vertex.
            do_debug_print (bool): Flag to enable printing of debug information for this vertex.
        Returns:
            tuple: The 2D screen coordinates (x, y), or None if projection is not possible (e.g. w is zero).
        """
        # Transform vertex to view space, then to clip space
        view_space = view_matrix @ glm.vec4(*vertex, 1.0)
        clip_space = projection_matrix @ view_space

        if do_debug_print:
            print(f"DEBUG _project_vertex_static: Vertex {vertex}, " +
                  f"ViewSpace ({view_space.x:.2f}, {view_space.y:.2f}, {view_space.z:.2f}, {view_space.w:.2f}), " +
                  f"ClipSpace ({clip_space.x:.2f}, {clip_space.y:.2f}, {clip_space.z:.2f}, {clip_space.w:.2f})")
>>>>>>> Stashed changes
        
        # 2. Применяем проекционную матрицу
        clip_space = self.app.projection_matrix @ view_space
        
        # 3. Перспективное деление
        if clip_space.w != 0:
            ndc = clip_space / clip_space.w
        else:
            return None
        
<<<<<<< Updated upstream
        # 4. Преобразование в экранные координаты
        x = (ndc.x + 1) * (WIN_RES[0] / 2)
        y = (1 - (ndc.y + 1) / 2) * WIN_RES[1]
        #print(f"Vertex {vertex} -> NDC ({ndc.x:.2f}, {ndc.y:.2f}) -> Screen ({x}, {y})")
        return (x, y)

    def render_mesh(self, vertex_data, color):
        stride = 6  # 3 координаты позиции + 3 цвета на вершину
=======
        # Convert NDC to screen coordinates
        # NDC range from -1 to 1. Screen coordinates usually from (0,0) top-left to (width, height).
        x = (ndc.x + 1) * (win_res[0] / 2)
        y = (1 - (ndc.y + 1) / 2) * win_res[1] # Y is often inverted: (1 - ndc.y) or (1 - (ndc.y+1)/2)
        # The old per-vertex print for NDC and Screen was here, now handled by do_debug_print focusing on ViewSpace and ClipSpace
        # The old per-vertex print for NDC and Screen was here, now handled by do_debug_print focusing on ViewSpace and ClipSpace
        return (x, y)

    def process_triangle_data(self, v1_3d, v2_3d, v3_3d, base_color, 
                              view_matrix, projection_matrix, camera_position, win_res_tuple):
        """
        Core unit of work for threads. Processes a single triangle through the rendering pipeline:
        Frustum Culling, Normal Calculation, Backface Culling, Brightness Calculation,
        Depth Calculation, and Vertex Projection.

        Args:
            v1_3d, v2_3d, v3_3d (tuple): 3D coordinates of the triangle's vertices.
            base_color (tuple): The original (R, G, B) color of the triangle.
            view_matrix (glm.mat4): Current camera view matrix.
            projection_matrix (glm.mat4): Current projection matrix.
            camera_position (glm.vec3): Current camera position in 3D space.
            win_res_tuple (tuple): Window resolution (width, height), same as WIN_RES.

        Returns:
            A tuple (avg_depth, screen_triangle_coords, final_color) if the triangle is visible
            and processed successfully, otherwise None (if culled).
        """

        # Reset per-triangle vertex print counter at the start of processing a new triangle
        self.debug_vertices_printed_this_triangle = 0

        # --- DEBUG: Frustum Culling Disabled ---
        # # 1. FRUSTUM CULLING: Check if the triangle is outside the camera's viewing volume.
        # # Transform vertices to clip space (homogeneous coordinates)
        # v1_clip = projection_matrix @ view_matrix @ glm.vec4(*v1_3d, 1.0)
        # v2_clip = projection_matrix @ view_matrix @ glm.vec4(*v2_3d, 1.0)
        # v3_clip = projection_matrix @ view_matrix @ glm.vec4(*v3_3d, 1.0)
        # clip_vertices = [v1_clip, v2_clip, v3_clip]
        # 
        # if (all(cv.x < -cv.w for cv in clip_vertices) or
        #     all(cv.x >  cv.w for cv in clip_vertices) or
        #     all(cv.y < -cv.w for cv in clip_vertices) or
        #     all(cv.y >  cv.w for cv in clip_vertices) or
        #     all(cv.z < -cv.w for cv in clip_vertices) or
        #     all(cv.z >  cv.w for cv in clip_vertices)):
        #     return None # Culled by frustum
        # --- END DEBUG: Frustum Culling Disabled ---
        # Reset per-triangle vertex print counter at the start of processing a new triangle
        self.debug_vertices_printed_this_triangle = 0

        # --- DEBUG: Frustum Culling Disabled ---
        # # 1. FRUSTUM CULLING: Check if the triangle is outside the camera's viewing volume.
        # # Transform vertices to clip space (homogeneous coordinates)
        # v1_clip = projection_matrix @ view_matrix @ glm.vec4(*v1_3d, 1.0)
        # v2_clip = projection_matrix @ view_matrix @ glm.vec4(*v2_3d, 1.0)
        # v3_clip = projection_matrix @ view_matrix @ glm.vec4(*v3_3d, 1.0)
        # clip_vertices = [v1_clip, v2_clip, v3_clip]
        # 
        # if (all(cv.x < -cv.w for cv in clip_vertices) or
        #     all(cv.x >  cv.w for cv in clip_vertices) or
        #     all(cv.y < -cv.w for cv in clip_vertices) or
        #     all(cv.y >  cv.w for cv in clip_vertices) or
        #     all(cv.z < -cv.w for cv in clip_vertices) or
        #     all(cv.z >  cv.w for cv in clip_vertices)):
        #     return None # Culled by frustum
        # --- END DEBUG: Frustum Culling Disabled ---

        # 2. NORMAL CALCULATION (Still needed for is_front_facing if not fully disabling its logic)
        # normal = calculate_triangle_normal(v1_3d, v2_3d, v3_3d) 
        # 2. NORMAL CALCULATION (Still needed for is_front_facing if not fully disabling its logic)
        # normal = calculate_triangle_normal(v1_3d, v2_3d, v3_3d) 
        
        # 3. TRIANGLE CENTER (Still needed for is_front_facing if not fully disabling its logic)
        # triangle_center = glm.vec3(
        #     (v1_3d[0] + v2_3d[0] + v3_3d[0]) / 3,
        #     (v1_3d[1] + v2_3d[1] + v3_3d[1]) / 3,
        #     (v1_3d[2] + v2_3d[2] + v3_3d[2]) / 3
        # )
        # 3. TRIANGLE CENTER (Still needed for is_front_facing if not fully disabling its logic)
        # triangle_center = glm.vec3(
        #     (v1_3d[0] + v2_3d[0] + v3_3d[0]) / 3,
        #     (v1_3d[1] + v2_3d[1] + v3_3d[1]) / 3,
        #     (v1_3d[2] + v2_3d[2] + v3_3d[2]) / 3
        # )
        
        # --- DEBUG: Backface Culling Disabled ---
        # # 4. BACKFACE CULLING / BRIGHTNESS DOT PRODUCT
        # dot_product = is_front_facing(normal, camera_position, triangle_center)
        # if dot_product <= 0: # Also culls if dot_product is 0 (triangle is edge-on)
        #     return None # Culled by backface
        # --- END DEBUG: Backface Culling Disabled ---
        # --- DEBUG: Backface Culling Disabled ---
        # # 4. BACKFACE CULLING / BRIGHTNESS DOT PRODUCT
        # dot_product = is_front_facing(normal, camera_position, triangle_center)
        # if dot_product <= 0: # Also culls if dot_product is 0 (triangle is edge-on)
        #     return None # Culled by backface
        # --- END DEBUG: Backface Culling Disabled ---

        # --- DEBUG: Brightness Calculation Disabled / Fixed Color ---
        # # 5. BRIGHTNESS CALCULATION
        # brightness_factor = max(0, min(1, dot_product)) # dot_product would need to be calculated if this was active
        final_color = (0, 255, 0) # Fixed bright green color
        # --- END DEBUG: Brightness Calculation Disabled ---

        # --- DEBUG: Painter's Algorithm Disabled ---
        # # 6. VIEW SPACE DEPTH CALCULATION (Still needed for Painter's Algorithm)
        # v1_view = view_matrix @ glm.vec4(*v1_3d, 1.0)
        # v2_view = view_matrix @ glm.vec4(*v2_3d, 1.0)
        # v3_view = view_matrix @ glm.vec4(*v3_3d, 1.0)
        # avg_depth = (v1_view.z + v2_view.z + v3_view.z) / 3.0
        # --- END DEBUG: Painter's Algorithm Disabled ---
        # --- DEBUG: Brightness Calculation Disabled / Fixed Color ---
        # # 5. BRIGHTNESS CALCULATION
        # brightness_factor = max(0, min(1, dot_product)) # dot_product would need to be calculated if this was active
        final_color = (0, 255, 0) # Fixed bright green color
        # --- END DEBUG: Brightness Calculation Disabled ---

        # --- DEBUG: Painter's Algorithm Disabled ---
        # # 6. VIEW SPACE DEPTH CALCULATION (Still needed for Painter's Algorithm)
        # v1_view = view_matrix @ glm.vec4(*v1_3d, 1.0)
        # v2_view = view_matrix @ glm.vec4(*v2_3d, 1.0)
        # v3_view = view_matrix @ glm.vec4(*v3_3d, 1.0)
        # avg_depth = (v1_view.z + v2_view.z + v3_view.z) / 3.0
        # --- END DEBUG: Painter's Algorithm Disabled ---

        # 7. VERTEX PROJECTION TO SCREEN SPACE
        # Using the static helper method for projection
        # Vertex 1
        do_print_v1 = self.debug_triangles_printed_this_frame < 1 and self.debug_vertices_printed_this_triangle < 3
        screen_v1 = Renderer._project_vertex_static(v1_3d, view_matrix, projection_matrix, win_res_tuple, do_print_v1)
        if do_print_v1:
            self.debug_vertices_printed_this_triangle += 1
        
        # Vertex 2
        do_print_v2 = self.debug_triangles_printed_this_frame < 1 and self.debug_vertices_printed_this_triangle < 3
        screen_v2 = Renderer._project_vertex_static(v2_3d, view_matrix, projection_matrix, win_res_tuple, do_print_v2)
        if do_print_v2:
            self.debug_vertices_printed_this_triangle += 1

        # Vertex 3
        do_print_v3 = self.debug_triangles_printed_this_frame < 1 and self.debug_vertices_printed_this_triangle < 3
        screen_v3 = Renderer._project_vertex_static(v3_3d, view_matrix, projection_matrix, win_res_tuple, do_print_v3)
        if do_print_v3:
            self.debug_vertices_printed_this_triangle += 1
        # Vertex 1
        do_print_v1 = self.debug_triangles_printed_this_frame < 1 and self.debug_vertices_printed_this_triangle < 3
        screen_v1 = Renderer._project_vertex_static(v1_3d, view_matrix, projection_matrix, win_res_tuple, do_print_v1)
        if do_print_v1:
            self.debug_vertices_printed_this_triangle += 1
        
        # Vertex 2
        do_print_v2 = self.debug_triangles_printed_this_frame < 1 and self.debug_vertices_printed_this_triangle < 3
        screen_v2 = Renderer._project_vertex_static(v2_3d, view_matrix, projection_matrix, win_res_tuple, do_print_v2)
        if do_print_v2:
            self.debug_vertices_printed_this_triangle += 1

        # Vertex 3
        do_print_v3 = self.debug_triangles_printed_this_frame < 1 and self.debug_vertices_printed_this_triangle < 3
        screen_v3 = Renderer._project_vertex_static(v3_3d, view_matrix, projection_matrix, win_res_tuple, do_print_v3)
        if do_print_v3:
            self.debug_vertices_printed_this_triangle += 1

        if screen_v1 and screen_v2 and screen_v3:
            screen_triangle_coords = [screen_v1, screen_v2, screen_v3]
            # Debug print for the screen coordinates of the first successfully projected triangle of a frame
            if self.debug_triangles_printed_this_frame < 1:
                print(f"DEBUG: Projected screen_coords for first fully projected triangle: {screen_triangle_coords}")
                # self.debug_triangles_printed_this_frame += 1 # This counter is now incremented after drawing in render_mesh or after attempting to draw
            # Return tuple: (screen coordinates, final calculated color). Depth is not returned.
            return screen_triangle_coords, final_color
        
        # If any vertex failed projection, and we were debugging this triangle's vertices,
        # ensure we still count it as "attempted" for frame debug count.
        # This logic for incrementing debug_triangles_printed_this_frame will be handled in render_mesh
        # after attempting to draw or after processing the first triangle.
        return None, None # Return None for both if projection fails
            # Debug print for the screen coordinates of the first successfully projected triangle of a frame
            if self.debug_triangles_printed_this_frame < 1:
                print(f"DEBUG: Projected screen_coords for first fully projected triangle: {screen_triangle_coords}")
                # self.debug_triangles_printed_this_frame += 1 # This counter is now incremented after drawing in render_mesh or after attempting to draw
            # Return tuple: (screen coordinates, final calculated color). Depth is not returned.
            return screen_triangle_coords, final_color
        
        # If any vertex failed projection, and we were debugging this triangle's vertices,
        # ensure we still count it as "attempted" for frame debug count.
        # This logic for incrementing debug_triangles_printed_this_frame will be handled in render_mesh
        # after attempting to draw or after processing the first triangle.
        return None, None # Return None for both if projection fails


    def render_mesh(self, vertex_data, color, stride): # Added stride parameter
        # stride: The number of float components per vertex in vertex_data.
        # Example: if vertex_data is [pos(3f), normal(3f), color(3f)], stride is 9.
        # The first 3 floats of each vertex data block are assumed to be its x, y, z position.

    def render_mesh(self, vertex_data, color, stride): # Added stride parameter
        # stride: The number of float components per vertex in vertex_data.
        # Example: if vertex_data is [pos(3f), normal(3f), color(3f)], stride is 9.
        # The first 3 floats of each vertex data block are assumed to be its x, y, z position.

        # Pre-fetch matrices and camera position that are constant for all triangles in this mesh
        view_matrix = self.camera.get_view_matrix()
        projection_matrix = self.app.projection_matrix # Assuming this is relatively static or updated per frame
        camera_position = self.camera.position
        
        first_triangle_processed_for_debug_increment = False

        first_triangle_processed_for_debug_increment = False

>>>>>>> Stashed changes
        for i in range(0, len(vertex_data), stride*3):  # 3 вершины на треугольник
            triangle = []
            for j in range(3):
<<<<<<< Updated upstream
                idx = i + j * stride
                if idx + 5 >= len(vertex_data):  # Проверка выхода за границы
                    break
                x = vertex_data[idx]
                y = vertex_data[idx+1]
                z = vertex_data[idx+2]
                # TODO: Backwad culling
                screen_pos = self.project_vertex((x, y, z))
                if screen_pos:
                    triangle.append(screen_pos)
            if len(triangle) == 3:
                pygame.draw.polygon(self.screen, (255, 255, 255), triangle, 1)  # Белый цвет для теста

    def render(self):
        """Основной метод рендеринга (очистка экрана и рендер всех объектов)."""
        self.screen.fill((0, 0, 0))
=======
                idx = i + j * stride # Calculate start index of the current vertex's data block
                
                # Ensure there are enough elements for at least the position (3 floats)
                # The full stride might be larger (e.g., including normals, UVs, colors), 
                # but we only need x, y, z for process_triangle_data.
                if idx + 2 >= len(vertex_data): # Check if x, y, z can be accessed
                    break 
                x = vertex_data[idx] # Position x
                y = vertex_data[idx+1]
                z = vertex_data[idx+2]
                triangle_vertices_3d.append((x, y, z))

            if len(triangle_vertices_3d) == 3:
                v1_3d, v2_3d, v3_3d = triangle_vertices_3d[0], triangle_vertices_3d[1], triangle_vertices_3d[2]
                
                # --- Multithreading Disabled: Direct call to process_triangle_data ---
                # --- Painter's Algorithm Disabled: Immediate Draw ---
                screen_coords, tri_color = self.process_triangle_data(
                    v1_3d, v2_3d, v3_3d,
                # --- Multithreading Disabled: Direct call to process_triangle_data ---
                # --- Painter's Algorithm Disabled: Immediate Draw ---
                screen_coords, tri_color = self.process_triangle_data(
                    v1_3d, v2_3d, v3_3d,
                    color, # base_color for this mesh
                    view_matrix,
                    projection_matrix,
                    view_matrix,
                    projection_matrix,
                    camera_position,
                    WIN_RES # Pass WIN_RES tuple
                )
                
                if screen_coords and tri_color:
                    pygame.draw.polygon(self.screen, tri_color, screen_coords, 0)
                    # Increment debug counter only after the first successful draw attempt of the frame.
                    # The vertex-level debug prints are handled within process_triangle_data.
                    # This specific screen_coords print is for the *whole triangle*.
                    if not first_triangle_processed_for_debug_increment and self.debug_triangles_printed_this_frame < 1:
                        # This condition ensures we only increment debug_triangles_printed_this_frame ONCE per frame,
                        # triggered by the first triangle of any mesh that gets drawn or attempts detailed vertex prints.
                        # The actual print of screen_coords is in process_triangle_data.
                        self.debug_triangles_printed_this_frame += 1 
                        first_triangle_processed_for_debug_increment = True 
                elif not first_triangle_processed_for_debug_increment and self.debug_triangles_printed_this_frame < 1 and self.debug_vertices_printed_this_triangle > 0 :
                    # If vertex debug prints happened for this triangle but it wasn't drawn (e.g. projection failed for one vertex)
                    # still count this as the "first debugged triangle" for the frame.
                    self.debug_triangles_printed_this_frame += 1
                    first_triangle_processed_for_debug_increment = True

                
                if screen_coords and tri_color:
                    pygame.draw.polygon(self.screen, tri_color, screen_coords, 0)
                    # Increment debug counter only after the first successful draw attempt of the frame.
                    # The vertex-level debug prints are handled within process_triangle_data.
                    # This specific screen_coords print is for the *whole triangle*.
                    if not first_triangle_processed_for_debug_increment and self.debug_triangles_printed_this_frame < 1:
                        # This condition ensures we only increment debug_triangles_printed_this_frame ONCE per frame,
                        # triggered by the first triangle of any mesh that gets drawn or attempts detailed vertex prints.
                        # The actual print of screen_coords is in process_triangle_data.
                        self.debug_triangles_printed_this_frame += 1 
                        first_triangle_processed_for_debug_increment = True 
                elif not first_triangle_processed_for_debug_increment and self.debug_triangles_printed_this_frame < 1 and self.debug_vertices_printed_this_triangle > 0 :
                    # If vertex debug prints happened for this triangle but it wasn't drawn (e.g. projection failed for one vertex)
                    # still count this as the "first debugged triangle" for the frame.
                    self.debug_triangles_printed_this_frame += 1
                    first_triangle_processed_for_debug_increment = True


    def render(self):
        """Основной метод рендеринга (очистка экрана и рендер всех объектов)."""
        self.screen.fill((0, 0, 0)) # Clear screen
        
        # Reset the debug print counter for triangles at the start of each frame
        self.debug_triangles_printed_this_frame = 0
        # Note: self.debug_vertices_printed_this_triangle is reset within process_triangle_data

        # Clear lists for the new frame. self.triangles_to_render is not used for drawing in this mode.
        # Reset the debug print counter for triangles at the start of each frame
        self.debug_triangles_printed_this_frame = 0
        # Note: self.debug_vertices_printed_this_triangle is reset within process_triangle_data

        # Clear lists for the new frame. self.triangles_to_render is not used for drawing in this mode.
        self.triangles_to_render = [] 
        # self.futures_list = [] # Not used in synchronous mode

        # CRITICAL DESIGN POINT (Synchronous context with Immediate Draw):
        # The main application loop should call a method that eventually calls `self.render_mesh()` for all objects.
        # For example, app.render() -> scene.render() -> mesh.render() -> renderer.render_mesh().
        # Drawing now happens directly within `render_mesh`.
        # This `render()` method primarily handles screen clearing and setup.

        # --- Painter's Algorithm Disabled ---
        # No sorting or drawing from self.triangles_to_render needed here.
        # # Sort triangles by depth (farthest first)
        # self.triangles_to_render.sort(key=lambda x: x[0], reverse=True)
        #
        # # Draw sorted triangles
        # for depth, screen_coords, tri_color in self.triangles_to_render:
        #     pygame.draw.polygon(self.screen, tri_color, screen_coords, 1) 
        # --- END Painter's Algorithm Disabled ---

        # self.triangles_to_render is cleared, but not used for drawing.
        # self.futures_list is not used.

    def destroy(self):
        """Shutdown the thread pool (if it were active)."""
        # --- Multithreading Disabled ---
        # if hasattr(self, 'thread_pool') and self.thread_pool is not None:
        #     self.thread_pool.shutdown(wait=True)
        # --- Multithreading Disabled ---
        pass # Method can be kept for API compatibility, but does nothing now.



    #Initial OLD code:
'''# Давайте дополним ваш рендерер для работы с мешами через Pygame. Основная задача — преобразовать 3D вершины в 2D экранные координаты и отрисовать треугольники.

# ### 1. **Класс рендерера (renderer.py)**
# ```python
import pygame
import numpy as np
from settings import *

def calculate_triangle_normal(v1, v2, v3):
    # Преобразуем вершины в векторы glm
    a = glm.vec3(v1)
    b = glm.vec3(v2)
    c = glm.vec3(v3)
    
    # Вычисляем векторы сторон
    edge1 = b - a
    edge2 = c - a
    
    # Векторное произведение
    normal = glm.cross(edge1, edge2)
    
    # Нормализуем результат
    return glm.normalize(normal)

def is_front_facing(normal, camera_pos, triangle_center):
    # Вектор от центра треугольника к камере
    view_dir = glm.normalize(glm.vec3(camera_pos) - triangle_center)
    
    # Скалярное произведение нормали и направления взгляда
    return glm.dot(normal, view_dir) > 0


#Объекты должны добавляться в очередь на рендеринг с помощью макс числа потоков. Позже обрабатываться с помощью макс числа потоков, а потом отрисовываться. +Backwad Culling +Frustrum Culling +Z буффер +яркость от того, на сколько треугольник повёрнут на камеру.
class Renderer:
    def __init__(self, app):
        self.app = app
        self.screen = app.window
        self.printed = False
        try:
            self.camera = app.camera
        except:
            self.camera = app.player

    def project_vertex(self, vertex):
        """Преобразует 3D вершину в 2D экранные координаты."""
        # 1. Применяем видовую матрицу
        view_space = self.camera.get_view_matrix() @ glm.vec4(*vertex, 1.0)
        
        # 2. Применяем проекционную матрицу
        clip_space = self.app.projection_matrix @ view_space
        
        # 3. Перспективное деление
        if clip_space.w != 0:
            ndc = clip_space / clip_space.w
        else:
            return None
        
        # 4. Преобразование в экранные координаты
        x = (ndc.x + 1) * (WIN_RES[0] / 2)
        y = (1 - (ndc.y + 1) / 2) * WIN_RES[1]
        #print(f"Vertex {vertex} -> NDC ({ndc.x:.2f}, {ndc.y:.2f}) -> Screen ({x}, {y})")
        return (x, y)

    def render_mesh(self, vertex_data, color):
        stride = 6  # 3 координаты позиции + 3 цвета на вершину
        for i in range(0, len(vertex_data), stride*3):  # 3 вершины на треугольник
            triangle = []
            for j in range(3):
                idx = i + j * stride
                if idx + 5 >= len(vertex_data):  # Проверка выхода за границы
                    break
                x = vertex_data[idx]
                y = vertex_data[idx+1]
                z = vertex_data[idx+2]
                # TODO: Backwad culling
                screen_pos = self.project_vertex((x, y, z))
                if screen_pos:
                    triangle.append(screen_pos)
            if len(triangle) == 3:
                pygame.draw.polygon(self.screen, (255, 255, 255), triangle, 1)  # Белый цвет для теста

    def render(self):
        """Основной метод рендеринга (очистка экрана и рендер всех объектов)."""
        self.screen.fill((0, 0, 0))'''
>>>>>>> Stashed changes
