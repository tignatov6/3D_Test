# Давайте дополним ваш рендерер для работы с мешами через Pygame. Основная задача — преобразовать 3D вершины в 2D экранные координаты и отрисовать треугольники.

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
        self.screen.fill((0, 0, 0))