# This module implements a 3D renderer using Pygame for 2D display.
# It features a multithreaded geometry processing pipeline that includes:
# - Frustum Culling: Discards triangles outside the camera's view.
# - Backface Culling: Discards triangles facing away from the camera.
# - Brightness Calculation: Adjusts triangle color based on orientation to the camera.
# - Vertex Projection: Transforms 3D vertices to 2D screen coordinates.
# - Painter's Algorithm: Sorts triangles by depth to ensure correct draw order.
# The rendering tasks for individual triangles are processed in parallel using a ThreadPoolExecutor.

import pygame
import numpy as np
import glm # For vector and matrix operations
import os # For accessing CPU count
from concurrent.futures import ThreadPoolExecutor # For multithreading
from settings import * # Imports settings like WIN_RES (window resolution) and N_THREADS

# Attempt to get N_THREADS from settings, with a fallback if not defined there.
try:
    from settings import N_THREADS
except ImportError:
    N_THREADS = os.cpu_count() or 4 # Default to number of CPUs or 4 as a fallback

def calculate_triangle_normal(v1, v2, v3):
    """
    Calculates the normal vector of a triangle defined by three vertices.
    The normal is perpendicular to the triangle's surface and is used for culling and lighting.
    Args:
        v1, v2, v3: Tuple or list-like representing 3D vertex coordinates (e.g., (x, y, z)).
    Returns:
        A normalized glm.vec3 representing the triangle's normal.
    """
    a = glm.vec3(v1) # Convert to glm vectors for vector math
    b = glm.vec3(v2)
    c = glm.vec3(v3)
    
    # Calculate two edges of the triangle
    edge1 = b - a
    edge2 = c - a
    
    # The cross product of two edges gives a vector perpendicular to the triangle's plane
    normal = glm.cross(edge1, edge2)
    
    # Normalize the normal vector to make it a unit vector
    return glm.normalize(normal)

def is_front_facing(normal, camera_pos, triangle_center):
    """
    Determines the orientation of a triangle relative to the camera.
    Args:
        normal (glm.vec3): The normalized normal vector of the triangle.
        camera_pos (glm.vec3): The 3D position of the camera.
        triangle_center (glm.vec3): The 3D position of the triangle's center.
    Returns:
        float: The dot product of the triangle's normal and the view direction.
               A positive value indicates the triangle is front-facing.
               This value is also used for basic brightness calculation.
    """
    # Calculate the vector from the triangle's center to the camera
    view_dir = glm.normalize(glm.vec3(camera_pos) - triangle_center)
    
    # Calculate the dot product of the normal and the view direction.
    # If positive, the triangle's normal is pointing towards the camera (front-facing).
    # If zero, it's edge-on. If negative, it's back-facing.
    return glm.dot(normal, view_dir)


class Renderer:
    """
    Handles all 3D rendering operations, including managing a thread pool
    for parallel processing of triangle geometry.
    """
    def __init__(self, app):
        self.app = app  # Reference to the main application instance
        self.screen = app.window # Pygame screen surface for drawing
        self.printed = False # (Legacy or debug flag, consider removal if unused)
        try:
            self.camera = app.camera # Main camera used for rendering
        except:
            self.camera = app.player # Fallback if app.camera is not defined
        
        # List to store processed triangles (depth, screen_coords, color) for Painter's Algorithm
        self.triangles_to_render = [] 
        
        # ThreadPoolExecutor for parallelizing triangle processing tasks
        self.thread_pool = ThreadPoolExecutor(max_workers=N_THREADS)
        
        # List to store Future objects from tasks submitted to the thread pool for the current frame
        self.futures_list = []

    @staticmethod
    def _project_vertex_static(vertex, view_matrix, projection_matrix, win_res):
        """
        Static method to project a 3D vertex to 2D screen coordinates.
        Being static allows it to be called by threads without needing access to the Renderer's 'self' instance,
        or if 'self' were passed, it would simplify dependency management for this specific projection task.
        Args:
            vertex (tuple): The 3D coordinates of the vertex (x, y, z).
            view_matrix (glm.mat4): The camera's view matrix.
            projection_matrix (glm.mat4): The projection matrix.
            win_res (tuple): The window resolution (width, height) from settings (WIN_RES).
        Returns:
            tuple: The 2D screen coordinates (x, y), or None if projection is not possible (e.g. w is zero).
        """
        # Transform vertex to view space, then to clip space
        view_space = view_matrix @ glm.vec4(*vertex, 1.0)
        clip_space = projection_matrix @ view_space
        
        # Perform perspective division (Normalize Device Coordinates - NDC)
        if clip_space.w != 0: # Avoid division by zero; w can be zero for points at camera's focal point or behind if w is negative
            ndc = clip_space / clip_space.w
        else:
            return None # Vertex cannot be projected (e.g., exactly at camera's position or behind near plane in some projections)
        
        # Convert NDC to screen coordinates
        # NDC range from -1 to 1. Screen coordinates usually from (0,0) top-left to (width, height).
        x = (ndc.x + 1) * (win_res[0] / 2)
        y = (1 - (ndc.y + 1) / 2) * win_res[1] # Y is often inverted: (1 - ndc.y) or (1 - (ndc.y+1)/2)
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

        # 1. FRUSTUM CULLING: Check if the triangle is outside the camera's viewing volume.
        # Transform vertices to clip space (homogeneous coordinates)
        v1_clip = projection_matrix @ view_matrix @ glm.vec4(*v1_3d, 1.0)
        v2_clip = projection_matrix @ view_matrix @ glm.vec4(*v2_3d, 1.0)
        v3_clip = projection_matrix @ view_matrix @ glm.vec4(*v3_3d, 1.0)
        clip_vertices = [v1_clip, v2_clip, v3_clip]

        if (all(cv.x < -cv.w for cv in clip_vertices) or
            all(cv.x >  cv.w for cv in clip_vertices) or
            all(cv.y < -cv.w for cv in clip_vertices) or
            all(cv.y >  cv.w for cv in clip_vertices) or
            all(cv.z < -cv.w for cv in clip_vertices) or
            all(cv.z >  cv.w for cv in clip_vertices)):
            return None # Culled by frustum

        # 2. NORMAL CALCULATION
        normal = calculate_triangle_normal(v1_3d, v2_3d, v3_3d)
        
        # 3. TRIANGLE CENTER
        triangle_center = glm.vec3(
            (v1_3d[0] + v2_3d[0] + v3_3d[0]) / 3,
            (v1_3d[1] + v2_3d[1] + v3_3d[1]) / 3,
            (v1_3d[2] + v2_3d[2] + v3_3d[2]) / 3
        )
        
        # 4. BACKFACE CULLING / BRIGHTNESS DOT PRODUCT
        dot_product = is_front_facing(normal, camera_position, triangle_center)
        if dot_product <= 0: # Also culls if dot_product is 0 (triangle is edge-on)
            return None # Culled by backface

        # 5. BRIGHTNESS CALCULATION
        brightness_factor = max(0, min(1, dot_product))
        final_color = (
            max(0, min(255, int(base_color[0] * brightness_factor))),
            max(0, min(255, int(base_color[1] * brightness_factor))),
            max(0, min(255, int(base_color[2] * brightness_factor)))
        )

        # 6. VIEW SPACE DEPTH CALCULATION
        v1_view = view_matrix @ glm.vec4(*v1_3d, 1.0)
        v2_view = view_matrix @ glm.vec4(*v2_3d, 1.0)
        v3_view = view_matrix @ glm.vec4(*v3_3d, 1.0)
        avg_depth = (v1_view.z + v2_view.z + v3_view.z) / 3.0

        # 7. VERTEX PROJECTION TO SCREEN SPACE
        # Using the static helper method for projection
        screen_v1 = Renderer._project_vertex_static(v1_3d, view_matrix, projection_matrix, win_res_tuple)
        screen_v2 = Renderer._project_vertex_static(v2_3d, view_matrix, projection_matrix, win_res_tuple)
        screen_v3 = Renderer._project_vertex_static(v3_3d, view_matrix, projection_matrix, win_res_tuple)

        if screen_v1 and screen_v2 and screen_v3:
            screen_triangle_coords = [screen_v1, screen_v2, screen_v3]
            return (avg_depth, screen_triangle_coords, final_color)
        return None


    def render_mesh(self, vertex_data, color):
        stride = 6  # 3 координаты позиции + 3 цвета на вершину
        # Pre-fetch matrices and camera position that are constant for all triangles in this mesh
        view_matrix = self.camera.get_view_matrix()
        projection_matrix = self.app.projection_matrix # Assuming this is relatively static or updated per frame
        camera_position = self.camera.position
        
        for i in range(0, len(vertex_data), stride*3):  # 3 вершины на треугольник
            triangle_vertices_3d = []
            for j in range(3):
                idx = i + j * stride
                if idx + 5 >= len(vertex_data):
                    break 
                x = vertex_data[idx]
                y = vertex_data[idx+1]
                z = vertex_data[idx+2]
                triangle_vertices_3d.append((x, y, z))

            if len(triangle_vertices_3d) == 3:
                v1_3d, v2_3d, v3_3d = triangle_vertices_3d[0], triangle_vertices_3d[1], triangle_vertices_3d[2]
                
                # Submit to thread pool
                future = self.thread_pool.submit(
                    self.process_triangle_data, 
                    v1_3d, v2_3d, v3_3d, 
                    color, # base_color for this mesh
                    view_matrix, 
                    projection_matrix, 
                    camera_position,
                    WIN_RES # Pass WIN_RES tuple
                )
                self.futures_list.append(future)

    def render(self):
        """Основной метод рендеринга (очистка экрана и рендер всех объектов)."""
        self.screen.fill((0, 0, 0)) # Clear screen
        
        # Clear lists for the new frame
        self.triangles_to_render = [] 
        self.futures_list = []

        # Dispatch all rendering tasks for all meshes/objects
        # This part needs to be adapted based on how objects are managed and rendered.
        # For example, if you have a list of objects:
        # for obj in self.app.scene.objects:
        #     self.render_mesh(obj.vertex_data, obj.color)
        # For now, this method assumes render_mesh has been called elsewhere to populate self.futures_list.
        # The main application loop should call render_mesh for each object before calling render().
        # Or, render() itself should iterate through objects and call render_mesh.
        # Let's assume for now that render_mesh calls are made by the app's main loop before render()

        # Collect results from threads
        for future in self.futures_list:
            result = future.result() # This will block until the future is complete
            if result:
                self.triangles_to_render.append(result)

        # Sort triangles by depth (farthest first)
        self.triangles_to_render.sort(key=lambda x: x[0], reverse=True)

        # Draw sorted triangles
        for depth, screen_coords, tri_color in self.triangles_to_render:
            pygame.draw.polygon(self.screen, tri_color, screen_coords, 1) 

        # self.triangles_to_render is already cleared at the beginning of the next call to render()
        # self.futures_list is also cleared at the beginning.

    def destroy(self):
        """Shutdown the thread pool."""
        self.thread_pool.shutdown(wait=True)