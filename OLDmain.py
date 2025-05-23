import glm
import math
from settings import *
from classes.EasyPygame import *
import pygame

# Инициализация камеры
class Camera:
    def __init__(self):
        self.position = glm.vec3(0, 0, 0)
        self.front = glm.vec3(0, 0, 1)
        self.up = glm.vec3(0, 1, 0)
        self.yaw = -90.0
        self.pitch = 0.0
        self.sensitivity = 0.1
        self.update_vectors()
    
    def update_vectors(self):
        # Пересчет направления взгляда
        front = glm.vec3()
        front.x = math.cos(glm.radians(self.yaw)) * math.cos(glm.radians(self.pitch))
        front.y = math.sin(glm.radians(self.pitch))
        front.z = math.sin(glm.radians(self.yaw)) * math.cos(glm.radians(self.pitch))
        self.front = glm.normalize(front)
        
        # Пересчет правого вектора и вектора "вверх"
        self.right = glm.normalize(glm.cross(self.front, glm.vec3(0, 1, 0)))
        self.up = glm.normalize(glm.cross(self.right, self.front))

    def get_view_matrix(self):
        return glm.lookAt(self.position, self.position + self.front, self.up)

# Создание камеры
camera = Camera()

def create_projection_matrix():
    return glm.perspective(glm.radians(FOV_DEG), ASPECT_RATIO, NEAR, FAR)

projection_matrix = create_projection_matrix()

def world_to_screen(point):
    # Преобразование в координаты камеры
    point_4d = glm.vec4(*point, 1.0)
    
    # Применение матриц
    view_space = camera.get_view_matrix() * point_4d
    clip_space = projection_matrix * view_space
    
    # Перспективное деление
    if clip_space.w != 0:
        ndc_space = glm.vec3(clip_space) / clip_space.w
    else:
        return (0, 0)
    
    # Преобразование в экранные координаты
    x = (ndc_space.x + 1) * (WIN_RES[0] / 2)
    y = (1 - (ndc_space.y + 1) / 2) * WIN_RES[1]
    return (int(x), int(y))

# Вершины треугольника
triangle_3d = [
    glm.vec3(2, 3, 5),
    glm.vec3(1, 4, 6),
    glm.vec3(3, 2, 10)
]

# Инициализация игры
game = EasyGame(WIN_RES)
pygame.mouse.set_visible(False)
pygame.event.set_grab(True)

# Главный цикл
running = True
while running:
    running = game.processEvents()
    
    # Обработка ввода мыши
    mouse_dx, mouse_dy = pygame.mouse.get_rel()
    camera.yaw += mouse_dx * camera.sensitivity
    camera.pitch -= mouse_dy * camera.sensitivity
    
    # Ограничение углов
    camera.pitch = max(-89.0, min(89.0, camera.pitch))
    
    # Обновление векторов камеры
    camera.update_vectors()
    
    # Отрисовка
    game.window.fill((0, 0, 0))
    screen_coords = []
    
    for point in triangle_3d:
        screen = world_to_screen(point)
        screen_coords.append(screen)
    
    pygame.draw.polygon(game.window, (255, 0, 0), screen_coords)
    pygame.display.set_caption(f'3D Camera (FPS: {1/game.delta_time:.0f})')
    pygame.display.flip()