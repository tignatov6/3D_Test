from settings import *
from meshes.base_mesh import BaseMesh
from meshes.obj_loader import load_obj_file


class Mesh(BaseMesh):
    def __init__(self, app, obj_filename, color=(0.8, 0.8, 0.8)):
        super().__init__()

        self.app = app
        #self.ctx = app.ctx
        #self.program = app.shader_program.quad

        self.obj_filename = obj_filename # Сохраняем имя файла
        self.model_color = color # Сохраняем цвет для модели

        self.vbo_format = '3f 3f 3f'
        self.attrs = ('in_position', 'in_normal', 'in_color')
        self.vertex_data = self.get_vertex_data()
        print(self.vertex_data)
        print(f"Загружено вершин: {len(self.vertex_data) // 6}")  # 36
        #self.vao = self.get_vao()

    def get_vertex_data(self):
        # Используем наш загрузчик
        vertex_data = load_obj_file(self.obj_filename, default_color=self.model_color)
        print(f"Loaded vertex data for {self.obj_filename}: {vertex_data.shape}")
        # Если загрузчик вернул пустой массив (например, файл не найден),
        # можно вернуть какие-то данные по умолчанию или выбросить исключение
        if vertex_data.size == 0:
            print(f"Предупреждение: Не удалось загрузить данные для {self.obj_filename}. Используется пустой VBO.")
            # Можно вернуть, например, данные для маленькой точки, чтобы не было ошибки в OpenGL
            # return np.array([0,0,0, 1,1,1], dtype='float32') 
            return np.array([], dtype='float32') # Или просто пустой

        return vertex_data

    def render(self):
        # Вызываем рендерер
        self.app.renderer.render_mesh(self.vertex_data, self.model_color)