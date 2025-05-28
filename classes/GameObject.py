# GameObject.py
import glm
# from settings import * # Обычно GameObject не нужны глобальные настройки напрямую,
                        # но если нужны (например, для доступа к APP инстансу через settings), можно раскомментировать.
                        # Однако, лучше передавать app явно.

# Импорт Mesh. Убедись, что путь к файлу mesh.py корректен относительно GameObject.py
# Если mesh.py в той же папке:
# from mesh import Mesh
# Если mesh.py в подпапке 'meshes':
from meshes.mesh import Mesh
# Если структура проекта другая, скорректируй импорт.

class GameObject:
    def __init__(self, 
                 app,  # Ссылка на главный класс приложения/движка (Engine)
                 obj_filename: str, # Имя .obj файла для загрузки меша
                 # Параметры трансформации объекта
                 position: glm.vec3 = glm.vec3(0.0, 0.0, 0.0), 
                 rotation: glm.vec3 = glm.vec3(0.0, 0.0, 0.0),  # Углы Эйлера в градусах (Yaw, Pitch, Roll - Y, X, Z)
                 scale: glm.vec3 = glm.vec3(1.0, 1.0, 1.0),
                 # Цвет по умолчанию для меша, если в .obj файле нет информации о цвете
                 # или если load_obj_file использует его как основной цвет.
                 default_mesh_color: tuple = (0.8, 0.8, 0.8) # (R, G, B) от 0.0 до 1.0
                ):
        """
        Конструктор GameObject.

        :param app: Ссылка на экземпляр главного класса приложения (Engine).
        :param obj_filename: Имя .obj файла для загрузки 3D модели.
        :param position: Начальная позиция объекта в мировых координатах (glm.vec3).
        :param rotation: Начальное вращение объекта в градусах (углы Эйлера Y, X, Z) (glm.vec3).
        :param scale: Начальный масштаб объекта (glm.vec3).
        :param default_mesh_color: Цвет по умолчанию для меша (кортеж RGB, 0.0-1.0).
        """
        self.app = app  # Сохраняем ссылку на приложение/движок
        self.obj_filename = obj_filename # Имя файла модели

        # --- Трансформации ---
        # Храним как объекты glm.vec3 для удобства работы с ними
        self.position = glm.vec3(position)
        self.rotation = glm.vec3(rotation)  # Ожидается, что это углы в градусах
        self.scale = glm.vec3(scale)

        # --- Меш ---
        # Создаем экземпляр меша для этого объекта.
        # Mesh отвечает за загрузку данных вершин и их передачу в рендерер.
        try:
            self.mesh = Mesh(self.app, 
                             obj_filename=self.obj_filename, 
                             default_color_tuple=default_mesh_color)
        except Exception as e:
            print(f"Error creating Mesh for GameObject ('{obj_filename}'): {e}")
            # В случае ошибки создания меша, можно присвоить None или "пустой" меш,
            # чтобы избежать падения всего приложения, но объект не будет видим.
            self.mesh = None 
            # Или можно перебросить исключение, если объект критичен:
            # raise

        # --- Уникальный ID объекта ---
        # Используется для кэширования в C++ рендерере.
        # id(self) возвращает уникальный идентификатор объекта Python в памяти.
        self.game_object_id = id(self)

        # --- Пользовательская инициализация ---
        # Вызываем метод start() для дополнительной настройки, специфичной для этого GameObject.
        # Этот метод может быть переопределен в дочерних классах.
        if self.mesh: # Вызываем start только если меш успешно создан
            self.start()
        else:
            print(f"GameObject '{obj_filename}' could not execute start() due to mesh creation failure.")


    def start(self):
        """
        Метод для пользовательской инициализации объекта.
        Вызывается один раз после создания GameObject и его меша.
        Может быть переопределен в дочерних классах для добавления специфической логики.
        Например, установка начальных параметров, создание дочерних объектов и т.д.
        """
        # Пример:
        # print(f"GameObject '{self.obj_filename}' (ID: {self.game_object_id}) started.")
        pass

    def update(self, delta_time: float):
        """
        Метод для обновления состояния объекта каждый кадр.
        Вызывается из основного цикла обновления сцены.
        Может быть переопределен в дочерних классах.

        :param delta_time: Время, прошедшее с предыдущего кадра, в секундах.
        """
        # Пример логики обновления:
        # self.rotation.y += 30.0 * delta_time  # Вращение на 30 градусов в секунду вокруг Y
        # self.rotation.y %= 360.0             # Ограничение угла от 0 до 360
        
        # if self.position.y < 0:
        #     self.position.y = 0 
        pass

    def render(self):
        """
        Передает данные для рендеринга меша этого объекта в основной рендерер.
        Вызывается из цикла рендеринга сцены.
        """
        if self.mesh: # Рендерим только если меш существует
            # Меш сам вызовет self.app.renderer.render_mesh(...)
            self.mesh.render(
                game_object_id=self.game_object_id,
                position=self.position,
                rotation=self.rotation,  # Передаем углы в градусах, C++ ожидает их
                scale=self.scale
            )
        # else:
            # Если меш не был создан, объект просто не будет отрендерен.
            # Можно добавить логирование, если это неожиданная ситуация.
            # print(f"GameObject '{self.obj_filename}' has no mesh to render.")


    # --- Дополнительные полезные методы (примеры) ---

    def set_position(self, x: float, y: float, z: float):
        """Устанавливает позицию объекта."""
        self.position = glm.vec3(x, y, z)

    def translate(self, dx: float, dy: float, dz: float):
        """Смещает позицию объекта."""
        self.position += glm.vec3(dx, dy, dz)

    def set_rotation_degrees(self, yaw: float, pitch: float, roll: float):
        """Устанавливает вращение объекта в градусах (Y, X, Z)."""
        self.rotation = glm.vec3(yaw, pitch, roll)

    def rotate_degrees(self, d_yaw: float, d_pitch: float, d_roll: float):
        """Изменяет вращение объекта в градусах."""
        self.rotation += glm.vec3(d_yaw, d_pitch, d_roll)
        # Можно добавить нормализацию углов, если нужно (например, self.rotation.y %= 360.0)

    def set_scale(self, sx: float, sy: float, sz: float):
        """Устанавливает масштаб объекта."""
        self.scale = glm.vec3(sx, sy, sz)

    def look_at(self, target_position: glm.vec3, world_up: glm.vec3 = glm.vec3(0, 1, 0)):
        """
        Изменяет вращение объекта так, чтобы он "смотрел" на указанную цель.
        ВНИМАНИЕ: Эта функция может быть сложной для корректной реализации с углами Эйлера
        и может привести к gimbal lock. Обычно для этого используются матрицы или кватернионы.
        Этот пример очень упрощен и может не работать идеально во всех случаях.
        Для полноценного look_at лучше управлять матрицей объекта напрямую или использовать кватернионы.
        """
        # Это очень упрощенная версия, которая не будет работать так, как полноценный look_at
        # для установки self.rotation. Для настоящего look_at, нужно было бы
        # вычислить матрицу вида и извлечь из нее углы Эйлера, что подвержено проблемам.
        # Либо, если C++ сторона принимает матрицу модели, то лучше вычислить ее здесь.
        print("Warning: GameObject.look_at() is a placeholder and may not function as expected for Euler angles.")
        direction = glm.normalize(target_position - self.position)
        # Далее сложная часть: конвертация направления в углы Эйлера (yaw, pitch, roll)
        # Это нетривиально и подвержено gimbal lock.
        # Простой pitch и yaw можно попробовать так:
        # self.rotation.x = glm.degrees(math.asin(-direction.y)) # Pitch
        # self.rotation.y = glm.degrees(math.atan2(direction.x, direction.z)) # Yaw
        # Roll останется неопределенным или 0.
        pass