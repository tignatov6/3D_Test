# obj_loader.py
import numpy as np

def load_obj_file(filename, default_color=(0.5, 0.5, 0.5)):
    """
    Загружает геометрию из .obj файла.
    Поддерживает только вершины (v) и грани (f).
    Грани могут быть треугольниками или четырехугольниками (автоматически триангулируются).
    Не поддерживает текстурные координаты (vt) или нормали (vn) в этой базовой версии.
    Каждой вершине присваивается default_color.

    Возвращает:
        numpy.array: Массив данных вершин в формате [x,y,z, r,g,b, x,y,z, r,g,b, ...], dtype='float32'
                     или пустой массив в случае ошибки.
    """
    vertices_raw = []  # Список для хранения координат вершин (v)
    final_vertex_data = [] # Список для хранения итоговых данных (pos + color)

    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                command = parts[0]

                if command == 'v':
                    # Координаты вершины
                    vertices_raw.append(list(map(float, parts[1:4])))
                elif command == 'f':
                    # Определение грани
                    # Форматы граней: f v1 v2 v3 ...
                    #                f v1/vt1 v2/vt2 v3/vt3 ...
                    #                f v1/vt1/vn1 v2/vt2/vn2 v3/vt3/vn3 ...
                    #                f v1//vn1 v2//vn2 v3//vn3 ...
                    # Мы будем парсить только индексы вершин (v)
                    
                    face_vertex_indices = []
                    for part in parts[1:]:
                        # Берем только индекс вершины (до первого '/')
                        v_index = int(part.split('/')[0])
                        # OBJ файлы используют 1-based indexing, Python 0-based
                        face_vertex_indices.append(v_index - 1)
                    
                    # Простая триангуляция для полигонов (например, квадов)
                    # Если грань f v0 v1 v2 v3, создаем треугольники (v0,v1,v2) и (v0,v2,v3)
                    if len(face_vertex_indices) >= 3:
                        # Первый треугольник
                        idx0, idx1, idx2 = face_vertex_indices[0], face_vertex_indices[1], face_vertex_indices[2]
                        
                        final_vertex_data.extend(vertices_raw[idx0])
                        final_vertex_data.extend(default_color)
                        final_vertex_data.extend(vertices_raw[idx1])
                        final_vertex_data.extend(default_color)
                        final_vertex_data.extend(vertices_raw[idx2])
                        final_vertex_data.extend(default_color)

                        # Если это квад (или больше), добавляем еще треугольники (fan triangulation)
                        for i in range(3, len(face_vertex_indices)):
                            idx_prev = face_vertex_indices[i-1]
                            idx_curr = face_vertex_indices[i]
                            
                            # Треугольник (v0, v_prev, v_curr)
                            final_vertex_data.extend(vertices_raw[idx0]) # v0
                            final_vertex_data.extend(default_color)
                            final_vertex_data.extend(vertices_raw[idx_prev]) # v_prev
                            final_vertex_data.extend(default_color)
                            final_vertex_data.extend(vertices_raw[idx_curr]) # v_curr
                            final_vertex_data.extend(default_color)
                            
    except FileNotFoundError:
        print(f"Ошибка: Файл '{filename}' не найден.")
        return np.array([], dtype='float32')
    except Exception as e:
        print(f"Ошибка при парсинге OBJ файла '{filename}': {e}")
        return np.array([], dtype='float32')

    if not final_vertex_data:
        print(f"Предупреждение: Не найдено данных о вершинах/гранях в файле '{filename}' или формат не поддерживается.")
        return np.array([], dtype='float32')
        
    return np.array(final_vertex_data, dtype='float32')

if __name__ == '__main__':
    # Пример использования (создайте простой test.obj для проверки)
    # Пример test.obj:
    """
    # Cube
    v 1.0 1.0 -1.0
    v 1.0 -1.0 -1.0
    v 1.0 1.0 1.0
    v 1.0 -1.0 1.0
    v -1.0 1.0 -1.0
    v -1.0 -1.0 -1.0
    v -1.0 1.0 1.0
    v -1.0 -1.0 1.0

    f 1 2 4 3
    f 3 4 8 7
    f 7 8 6 5
    f 5 6 2 1
    f 5 7 3 1 # Лицевая сторона (Z+)
    f 2 6 8 4 # Задняя сторона (Z-)
    """
    # Создайте файл 'test_cube.obj' с содержимым выше
    # with open('test_cube.obj', 'w') as f_obj:
    #     f_obj.write("v 1.0 1.0 -1.0\nv 1.0 -1.0 -1.0\nv 1.0 1.0 1.0\nv 1.0 -1.0 1.0\n")
    #     f_obj.write("v -1.0 1.0 -1.0\nv -1.0 -1.0 -1.0\nv -1.0 1.0 1.0\nv -1.0 -1.0 1.0\n")
    #     f_obj.write("f 1 2 4 3\nf 3 4 8 7\nf 7 8 6 5\nf 5 6 2 1\nf 5 7 3 1\nf 2 6 8 4\n")

    vertex_data = load_obj_file('test_cube.obj', default_color=(1.0, 0.0, 0.0))
    if vertex_data.size > 0:
        print(f"Загружено {vertex_data.size // 6} вершин.") # Каждая вершина это 3(pos) + 3(color) = 6 float
        print("Первые 3 вершины (pos+color):")
        print(vertex_data[:18].reshape(-1,6)) # 3 вершины * (3 float pos + 3 float color) = 18
    else:
        print("Данные не загружены.")

    # Пример с треугольником
    # with open('test_triangle.obj', 'w') as f_obj:
    #     f_obj.write("v 0.0 0.5 0.0\nv -0.5 -0.5 0.0\nv 0.5 -0.5 0.0\n")
    #     f_obj.write("f 1 2 3\n")
    # vertex_data_tri = load_obj_file('test_triangle.obj', default_color=(0.0, 1.0, 0.0))
    # if vertex_data_tri.size > 0:
    #     print(f"\nЗагружено {vertex_data_tri.size // 6} вершин для треугольника.")
    #     print(vertex_data_tri)