import numpy as np

def parse_mtl(mtl_filename):
    """
    Парсит файл .mtl и извлекает информацию о материалах.
    Возвращает словарь материалов с их свойствами (например, {'Material': {'Kd': [r, g, b]}}).
    """
    materials = {}
    current_material = None
    try:
        with open(mtl_filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if parts[0] == 'newmtl':
                    current_material = parts[1]
                    materials[current_material] = {}
                elif parts[0] == 'Kd' and current_material is not None:
                    materials[current_material]['Kd'] = list(map(float, parts[1:4]))
    except FileNotFoundError:
        print(f"Ошибка: Файл '{mtl_filename}' не найден.")
    except Exception as e:
        print(f"Ошибка при парсинге MTL файла '{mtl_filename}': {e}")
    return materials

def load_obj_file(filename, default_color=(0.5, 0.5, 0.5)):
    """
    Загружает геометрию из .obj файла.
    Поддерживает вершины (v), нормали (vn), грани (f) и материалы из .mtl.
    Грани могут быть треугольниками или четырехугольниками (автоматически триангулируются).
    Для вершин без указанных нормалей используется default_normal = [0.0, 0.0, 1.0].
    Цвет вершин берется из материала (.mtl), если он определен, иначе используется default_color.

    Возвращает:
        numpy.array: Массив данных вершин в формате [x,y,z, r,g,b, nx,ny,nz, ...], dtype='float32'
                     или пустой массив в случае ошибки.
    """
    vertices_raw = []  # Список для хранения координат вершин (v)
    normals_raw = []   # Список для хранения нормалей (vn)
    materials = {}     # Словарь для хранения материалов из .mtl
    current_material = None
    final_vertex_data = [] # Список для хранения итоговых данных (pos + color + normal)
    default_normal = [0.0, 0.0, 1.0]

    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                command = parts[0]

                if command == 'mtllib':
                    # Загрузка файла .mtl
                    mtl_filename = parts[1]
                    materials = parse_mtl('assets/'+mtl_filename)
                elif command == 'usemtl':
                    # Установка текущего материала
                    current_material = parts[1]
                elif command == 'v':
                    # Координаты вершины
                    vertices_raw.append(list(map(float, parts[1:4])))
                elif command == 'vn':
                    # Нормали
                    normals_raw.append(list(map(float, parts[1:4])))
                elif command == 'f':
                    # Определение грани
                    face_vertices = []
                    for part in parts[1:]:
                        subparts = part.split('/')
                        v_index = int(subparts[0]) - 1
                        vn_index = None
                        if len(subparts) >= 3 and subparts[2]:
                            vn_index = int(subparts[2]) - 1
                        face_vertices.append((v_index, vn_index))

                    # Триангуляция
                    if len(face_vertices) >= 3:
                        # Первый треугольник
                        for i in [0, 1, 2]:
                            v_index, vn_index = face_vertices[i]
                            position = vertices_raw[v_index]
                            normal = normals_raw[vn_index] if vn_index is not None and vn_index < len(normals_raw) else default_normal
                            # Получение цвета из текущего материала
                            if current_material in materials and 'Kd' in materials[current_material]:
                                color = materials[current_material]['Kd']
                            else:
                                color = default_color
                            final_vertex_data.extend(position)
                            final_vertex_data.extend(color)
                            final_vertex_data.extend(normal)

                        # Дополнительные треугольники для полигонов
                        for i in range(3, len(face_vertices)):
                            for j in [0, i-1, i]:
                                v_index, vn_index = face_vertices[j]
                                position = vertices_raw[v_index]
                                normal = normals_raw[vn_index] if vn_index is not None and vn_index < len(normals_raw) else default_normal
                                # Используем тот же цвет для всех треугольников одной грани
                                if current_material in materials and 'Kd' in materials[current_material]:
                                    color = materials[current_material]['Kd']
                                else:
                                    color = default_color
                                final_vertex_data.extend(position)
                                final_vertex_data.extend(color)
                                final_vertex_data.extend(normal)

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

# Пример использования
if __name__ == '__main__':
    vertex_data = load_obj_file('test.obj', default_color=(1.0, 0.0, 0.0))
    if vertex_data.size > 0:
        num_vertices = vertex_data.size // 9
        print(f"Загружено {num_vertices} вершин.")
        print("Первые 3 вершины (pos+color+normal):")
        print(vertex_data[:27].reshape(-1,9))
    else:
        print("Данные не загружены.")