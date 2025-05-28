# test_cpp_module.py

import numpy as np
import glm # Ваш PyGLM
import sys
import os
import time # Импортируем модуль time

try:
    import cpp_renderer_core
    CPP_MODULE_LOADED = True
    print(f"--- Модуль cpp_renderer_core успешно загружен! ({cpp_renderer_core.__file__}) ---")
except ImportError as e:
    print(f"--- ОШИБКА: Не удалось импортировать модуль cpp_renderer_core: {e} ---")
    print("--- Убедитесь, что вы скомпилировали модуль командой: python setup.py build_ext --inplace ---")
    CPP_MODULE_LOADED = False
    sys.exit(1)


def calculate_triangle_normal_python_reference(v1_glm: glm.vec3, v2_glm: glm.vec3, v3_glm: glm.vec3) -> glm.vec3:
    """Эталонная Python-реализация для сравнения."""
    edge1 = v2_glm - v1_glm
    edge2 = v3_glm - v1_glm
    normal_vec = glm.cross(edge1, edge2)
    len_sq = glm.dot(normal_vec, normal_vec)
    if len_sq < 1e-18:
        return glm.vec3(0.0, 0.0, 1.0)
    return normal_vec / glm.sqrt(len_sq)


def run_tests():
    """Запускает все тесты для C++ модуля, включая замеры времени."""
    print("\n--- Начало тестирования функций из cpp_renderer_core ---")

    # Параметры для замера времени
    NUM_ITERATIONS_FOR_TIMING = 100000  # Количество вызовов для усреднения времени

    # Тест 1: calculate_triangle_normal_cpp
    print("\nТестирование: calculate_triangle_normal_cpp")
    test_cases_vec3 = [
        {
            "name": "Простой ортогональный треугольник",
            "v1": glm.vec3(0, 0, 0),
            "v2": glm.vec3(1, 0, 0),
            "v3": glm.vec3(0, 1, 0),
        },
        {
            "name": "Другой ортогональный треугольник",
            "v1": glm.vec3(0, 0, 0),
            "v2": glm.vec3(0, 1, 0),
            "v3": glm.vec3(1, 0, 0),
        },
        {
            "name": "Вырожденный треугольник",
            "v1": glm.vec3(0, 0, 0),
            "v2": glm.vec3(1, 1, 1),
            "v3": glm.vec3(2, 2, 2),
        },
        {
            "name": "Треугольник с другими координатами",
            "v1": glm.vec3(1, 2, 3),
            "v2": glm.vec3(4, 5, 6),
            "v3": glm.vec3(7, 8, 10),
        }
    ]

    all_tests_passed_normal = True
    test_count_normal = 0

    # Используем один тестовый случай для замера времени
    timing_test_case_normal = test_cases_vec3[0]
    v1_glm_timing = timing_test_case_normal["v1"]
    v2_glm_timing = timing_test_case_normal["v2"]
    v3_glm_timing = timing_test_case_normal["v3"]

    print(f"\n  Замер времени для calculate_triangle_normal ({NUM_ITERATIONS_FOR_TIMING} итераций):")

    # Замер времени для Python версии
    # В этом цикле мы вызываем Python функцию с объектами PyGLM
    start_time_py = time.perf_counter()
    for _ in range(NUM_ITERATIONS_FOR_TIMING):
        _ = calculate_triangle_normal_python_reference(v1_glm_timing, v2_glm_timing, v3_glm_timing)
    end_time_py = time.perf_counter()
    time_py_normal = (end_time_py - start_time_py) * 1000 # в миллисекундах
    print(f"    Python (эталон): {time_py_normal:.4f} ms (вызовы PyGLM)")

    # Подготовка NumPy массивов ЗА ПРЕДЕЛАМИ цикла замера для C++
    v1_np_prepared_for_cpp = np.array([v1_glm_timing.x, v1_glm_timing.y, v1_glm_timing.z], dtype=np.float32)
    v2_np_prepared_for_cpp = np.array([v2_glm_timing.x, v2_glm_timing.y, v2_glm_timing.z], dtype=np.float32)
    v3_np_prepared_for_cpp = np.array([v3_glm_timing.x, v3_glm_timing.y, v3_glm_timing.z], dtype=np.float32)

    # Замер времени для C++ версии
    # В этом цикле мы передаем уже созданные NumPy массивы в C++ функцию
    start_time_cpp = time.perf_counter()
    for _ in range(NUM_ITERATIONS_FOR_TIMING):
        _ = cpp_renderer_core.calculate_triangle_normal_cpp(v1_np_prepared_for_cpp, v2_np_prepared_for_cpp, v3_np_prepared_for_cpp)
    end_time_cpp = time.perf_counter()
    time_cpp_normal = (end_time_cpp - start_time_cpp) * 1000 # в миллисекундах
    print(f"    C++ (тест):      {time_cpp_normal:.4f} ms (с передачей NumPy извне цикла)")

    if time_cpp_normal > 0 and time_py_normal > 0 :
        speedup_normal = time_py_normal / time_cpp_normal
        print(f"    Ускорение C++ по сравнению с Python: {speedup_normal:.2f}x")
    else:
        print("    Не удалось рассчитать ускорение (время выполнения слишком мало или равно нулю).")


    print("\n  Проверка корректности результатов:")
    for test_case in test_cases_vec3:
        test_count_normal += 1
        print(f"\n    Тест корректности #{test_count_normal}: {test_case['name']}")
        v1_glm = test_case["v1"]
        v2_glm = test_case["v2"]
        v3_glm = test_case["v3"]

        v1_np = np.array([v1_glm.x, v1_glm.y, v1_glm.z], dtype=np.float32)
        v2_np = np.array([v2_glm.x, v2_glm.y, v2_glm.z], dtype=np.float32)
        v3_np = np.array([v3_glm.x, v3_glm.y, v3_glm.z], dtype=np.float32)

        try:
            result_cpp_np = cpp_renderer_core.calculate_triangle_normal_cpp(v1_np, v2_np, v3_np)
            result_cpp_glm = glm.vec3(result_cpp_np[0], result_cpp_np[1], result_cpp_np[2])
            expected_normal_glm = calculate_triangle_normal_python_reference(v1_glm, v2_glm, v3_glm)

            print(f"      Python (эталон) результат: {expected_normal_glm}")
            print(f"      C++ (тест) результат:      {result_cpp_glm}")

            epsilon = 1e-6
            if glm.all(glm.epsilonEqual(result_cpp_glm, expected_normal_glm, epsilon)):
                print(f"      РЕЗУЛЬТАТ: ПРОЙДЕН (точность {epsilon})")
            else:
                print(f"      РЕЗУЛЬТАТ: ПРОВАЛЕН")
                print(f"        Разница: {result_cpp_glm - expected_normal_glm}")
                all_tests_passed_normal = False
        except Exception as e:
            print(f"      ОШИБКА ВЫПОЛНЕНИЯ ТЕСТА КОРРЕКТНОСТИ: {e}")
            all_tests_passed_normal = False

    if all_tests_passed_normal:
        print("\n--- Все тесты корректности для calculate_triangle_normal_cpp ПРОЙДЕНЫ УСПЕШНО! ---")
    else:
        print("\n--- НЕКОТОРЫЕ ТЕСТЫ корректности для calculate_triangle_normal_cpp ПРОВАЛЕНЫ. ---")

    # Сюда можно будет добавить тесты и замеры для is_front_facing и других функций

    print("\n--- Тестирование функций из cpp_renderer_core ЗАВЕРШЕНО ---")
    return all_tests_passed_normal


if __name__ == "__main__":
    if CPP_MODULE_LOADED:
        if run_tests():
            print("\nИтоговый результат: ВСЕ ТЕСТЫ ПРОЙДЕНЫ.")
        else:
            print("\nИтоговый результат: ЕСТЬ ПРОВАЛЕННЫЕ ТЕСТЫ.")
    else:
        print("Тесты не могут быть запущены, так как модуль cpp_renderer_core не загружен.")