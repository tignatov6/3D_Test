# obj_parser.py
def parse_obj(file_path):
    vertices = []
    normals = []
    faces = []

    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            if not parts:
                continue

            try:
                # Вершины
                if parts[0] == 'v':
                    vertices.append(tuple(map(float, parts[1:4])))
                
                # Нормали
                elif parts[0] == 'vn':
                    normals.append(tuple(map(float, parts[1:4])))
                
                # Грани
                elif parts[0] == 'f':
                    face = []
                    for part in parts[1:]:
                        if part.startswith('#'):  # Пропускаем комментарии в середине строки
                            break
                        
                        indices = part.split('/')
                        # Обрабатываем только вершины и нормали (форматы: v, v//vn, v/vt/vn)
                        vertex_idx = int(indices[0]) - 1 if indices[0] else None
                        normal_idx = int(indices[2]) - 1 if len(indices) >= 3 and indices[2] else None
                        
                        if vertex_idx is None:
                            continue  # Пропускаем некорректные данные
                            
                        face.append({
                            'vertex': vertex_idx,
                            'normal': normal_idx if normal_idx is not None and normal_idx < len(normals) else None
                        })
                    
                    if face:  # Добавляем только непустые грани
                        faces.append(face)
            
            except Exception as e:
                print(f"Ошибка в строке {line_num}: '{line}'")
                print(f"Детали: {str(e)}")

    return {
        'vertices': vertices,
        'normals': normals,
        'faces': faces
    }

# Пример использования
if __name__ == "__main__":
    path = "assets/Dragon_80K.obj"
    obj_data = parse_obj(path)

    print(f"Объект: {path}, треугольников: {len(obj_data['faces'])}")
    
    # print("Вершины:")
    # for i, v in enumerate(obj_data['vertices']):
    #     print(f" {i + 1}: {v}")
    
    # print("\nНормали:")
    # for i, n in enumerate(obj_data['normals']):
    #     print(f" {i + 1}: {n}")
    
    # print("\nГрани:")
    # for i, face in enumerate(obj_data['faces']):
    #     print(f" Грань {i + 1}:")
    #     #print(face)
    #     for vert in face:
    #         #print(obj_data['vertices'])
    #         normal = obj_data['normals'][vert['normal']] if vert['normal'] is not None else "Нет"
    #         print(f"  Вершина {obj_data['vertices'][vert['vertex']]}, Нормаль: {normal}")