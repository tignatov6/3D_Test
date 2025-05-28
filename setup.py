# setup.py
from setuptools import setup, Extension
import pybind11
import os
import platform # Для определения операционной системы и компилятора
import sys # Для sys.exit в случае критических ошибок

# -----------------------------------------------------------------------------
# >>> КОНФИГУРАЦИЯ СБОРКИ PGO (Profile-Guided Optimization) <<<
# Установите эту переменную для управления фазой PGO:
# "NONE"      : Обычная агрессивная сборка без PGO.
# "INSTRUMENT": Сборка с инструментацией для сбора данных профиля.
# "OPTIMIZE"  : Сборка с использованием ранее собранных данных профиля.
# -----------------------------------------------------------------------------
PGO_BUILD_PHASE = "NONE"  # ИЗМЕНИТЕ ЗДЕСЬ: "NONE", "INSTRUMENT", или "OPTIMIZE"
# -----------------------------------------------------------------------------

# --- Базовые пути ---
current_script_path = os.path.dirname(os.path.abspath(__file__))
vendor_dir = os.path.join(current_script_path, 'vendor')
glm_include_dir = os.path.join(vendor_dir, 'glm')
cpp_src_dir = os.path.join(current_script_path, 'cpp_src')
MODULE_NAME = 'cpp_renderer_core' # Имя вашего модуля

# Проверки существования папок (GLM, cpp_src)
if not os.path.isdir(glm_include_dir):
    print(f"CRITICAL: GLM headers not found at: '{glm_include_dir}'.")
    sys.exit("GLM configuration failed.")
if not os.path.isdir(cpp_src_dir):
    print(f"CRITICAL: C++ source directory not found at: '{cpp_src_dir}'.")
    sys.exit("C++ source directory configuration failed.")
if not os.path.exists(os.path.join(cpp_src_dir, f'{MODULE_NAME}.cpp')):
    print(f"CRITICAL: Main C++ source file '{MODULE_NAME}.cpp' not found in '{cpp_src_dir}'.")
    sys.exit("Main C++ source file missing.")

# --- PGO Configuration (на основе переменной в коде) ---
PGO_PHASE_INTERNAL = PGO_BUILD_PHASE.upper()
PGO_ENABLED = PGO_PHASE_INTERNAL in ['INSTRUMENT', 'OPTIMIZE']

pgo_profile_dir_abs = None
if PGO_ENABLED:
    PGO_DATA_DIR_NAME = 'pgo_data'
    build_dir_for_pgo = os.path.join(current_script_path, 'build') # Данные PGO будут в build/pgo_data
    pgo_profile_dir_abs = os.path.join(build_dir_for_pgo, PGO_DATA_DIR_NAME)

    if not os.path.exists(pgo_profile_dir_abs):
        try:
            os.makedirs(pgo_profile_dir_abs, exist_ok=True) # exist_ok=True на случай параллельных запусков
            print(f"Info: Создан (или уже существует) каталог для данных PGO: {pgo_profile_dir_abs}")
        except OSError as e:
            print(f"ERROR: Не удалось создать каталог для данных PGO: {pgo_profile_dir_abs}. Ошибка: {e}")
            sys.exit(f"Создание каталога для данных PGO не удалось.")
    print(f"Info: PGO_BUILD_PHASE установлен в '{PGO_PHASE_INTERNAL}'. Каталог данных профиля: {pgo_profile_dir_abs}")


# --- SDL2 Configuration ---
sdl2_cflags = []
sdl2_libs = []
sdl_config_successful = False
try:
    if platform.system() == "Windows":
        SDL2_BASE_DIR = "C:/Libs/SDL2-2.28.4"
        if not os.path.isdir(SDL2_BASE_DIR):
            print(f"ERROR: SDL2 base directory not found at '{SDL2_BASE_DIR}'.")
        else:
            SDL2_INCLUDE_DIR = os.path.join(SDL2_BASE_DIR, "include")
            python_arch = platform.architecture()[0]
            SDL2_LIB_SUBDIR = "x64" if python_arch == "64bit" else ("x86" if python_arch == "32bit" else None)
            if not SDL2_LIB_SUBDIR: print(f"ERROR: Unknown Python architecture '{python_arch}'.")
            SDL2_LIB_DIR = os.path.join(SDL2_BASE_DIR, "lib", SDL2_LIB_SUBDIR) if SDL2_LIB_SUBDIR else None
            if os.path.isdir(SDL2_INCLUDE_DIR) and SDL2_LIB_DIR and os.path.isdir(SDL2_LIB_DIR):
                sdl2_cflags = [f'/I{SDL2_INCLUDE_DIR}']
                sdl2_libs = [f'/LIBPATH:{SDL2_LIB_DIR}', 'SDL2.lib', 'SDL2main.lib']
                sdl_config_successful = True
            else:
                print("ERROR: Manual SDL2 configuration for Windows failed (include/lib dirs not found).")
    else: # Linux or macOS
        try:
            sdl2_cflags_str = os.popen('sdl2-config --cflags').read().strip()
            sdl2_libs_str = os.popen('sdl2-config --libs').read().strip()
            if sdl2_cflags_str: sdl2_cflags = sdl2_cflags_str.split()
            if sdl2_libs_str: sdl2_libs = sdl2_libs_str.split()
            if sdl2_cflags and sdl2_libs: sdl_config_successful = True
            else: print("Warning: sdl2-config output was empty.")
        except Exception as e: print(f"Warning: sdl2-config failed: {e}.")
except Exception as e:
    print(f"ERROR: An unexpected error occurred during SDL2 configuration: {e}")

if not sdl_config_successful and not os.getenv("SETUPPY_IGNORE_SDL_FAILURE"):
    print("CRITICAL: SDL2 configuration was not successful. Compilation will likely fail.")
    sys.exit("SDL2 configuration failed.")
else:
    print("Info: SDL2 configuration successful or ignored.")


# --- SDL2_ttf Configuration ---
# !!! ВНИМАНИЕ: ОТРЕДАКТИРУЙТЕ SDL2TTF_BASE_DIR В СООТВЕТСТВИИ С ВАШЕЙ УСТАНОВКОЙ SDL2_ttf !!!
sdl2_ttf_cflags = []
sdl2_ttf_libs = []
sdl_ttf_config_successful = False
try:
    if platform.system() == "Windows":
        SDL2TTF_BASE_DIR = "C:/Libs/SDL2_ttf-2.24.0" # <--- УКАЖИТЕ ВАШ ПУТЬ
        if not os.path.isdir(SDL2TTF_BASE_DIR):
            print(f"ERROR: SDL2_ttf base directory not found at '{SDL2TTF_BASE_DIR}'.")
        else:
            SDL2TTF_INCLUDE_DIR = os.path.join(SDL2TTF_BASE_DIR, "include")
            python_arch = platform.architecture()[0]
            SDL2TTF_LIB_SUBDIR = "x64" if python_arch == "64bit" else ("x86" if python_arch == "32bit" else None)
            if not SDL2TTF_LIB_SUBDIR: print(f"ERROR: Unknown Python architecture for SDL2_ttf '{python_arch}'.")
            SDL2TTF_LIB_DIR = os.path.join(SDL2TTF_BASE_DIR, "lib", SDL2TTF_LIB_SUBDIR) if SDL2TTF_LIB_SUBDIR else None
            
            ttf_header_check_path = os.path.join(SDL2TTF_INCLUDE_DIR, "SDL_ttf.h") # SDL_ttf.h обычно лежит прямо в include или include/SDL2
            if not os.path.exists(ttf_header_check_path): # Проверяем альтернативный путь SDL2/SDL_ttf.h
                 ttf_header_check_path = os.path.join(SDL2TTF_INCLUDE_DIR, "SDL2", "SDL_ttf.h")

            ttf_lib_check_path = os.path.join(SDL2TTF_LIB_DIR, "SDL2_ttf.lib") if SDL2TTF_LIB_DIR else None

            if os.path.isdir(SDL2TTF_INCLUDE_DIR) and SDL2TTF_LIB_DIR and os.path.isdir(SDL2TTF_LIB_DIR) and \
               os.path.exists(ttf_header_check_path) and (ttf_lib_check_path and os.path.exists(ttf_lib_check_path)):
                sdl2_ttf_cflags.append(f'/I{SDL2TTF_INCLUDE_DIR}')
                sdl2_ttf_libs.extend([f'/LIBPATH:{SDL2TTF_LIB_DIR}', 'SDL2_ttf.lib'])
                sdl_ttf_config_successful = True
            else:
                print("ERROR: Manual SDL2_ttf configuration for Windows failed.")
                print(f"  SDL2_ttf Include Dir: '{SDL2TTF_INCLUDE_DIR}' (exists: {os.path.isdir(SDL2TTF_INCLUDE_DIR)})")
                print(f"  SDL_ttf.h path used for check: '{ttf_header_check_path}' (exists: {os.path.exists(ttf_header_check_path)})")
                print(f"  SDL2_ttf Lib Dir: '{SDL2TTF_LIB_DIR}' (exists: {os.path.isdir(SDL2TTF_LIB_DIR) if SDL2TTF_LIB_DIR else 'N/A'})")
                print(f"  SDL2_ttf.lib path used for check: '{ttf_lib_check_path}' (exists: {os.path.exists(ttf_lib_check_path) if ttf_lib_check_path else 'N/A'})")
    else: # Linux or macOS
        try:
            sdl2_ttf_cflags_str = os.popen('pkg-config --cflags SDL2_ttf').read().strip()
            sdl2_ttf_libs_str = os.popen('pkg-config --libs SDL2_ttf').read().strip()
            if sdl2_ttf_cflags_str: sdl2_ttf_cflags.extend(sdl2_ttf_cflags_str.split())
            if sdl2_ttf_libs_str: sdl2_ttf_libs.extend(sdl2_ttf_libs_str.split())
            if sdl2_ttf_cflags and sdl2_ttf_libs: sdl_ttf_config_successful = True
            else: print("Warning: pkg-config SDL2_ttf output was empty.")
        except Exception as e: print(f"Warning: pkg-config SDL2_ttf failed: {e}.")
except Exception as e:
    print(f"ERROR: An unexpected error occurred during SDL2_ttf configuration: {e}")

if not sdl_ttf_config_successful and not os.getenv("SETUPPY_IGNORE_SDLTtf_FAILURE"):
    print("CRITICAL: SDL2_ttf configuration was not successful. Text rendering will likely fail.")
    sys.exit("SDL2_ttf configuration failed.")
else:
    print("Info: SDL2_ttf configuration successful or ignored.")


# --- SDL2_image Configuration ---
# !!! ВНИМАНИЕ: ОТРЕДАКТИРУЙТЕ SDL2IMAGE_BASE_DIR В СООТВЕТСТВИИ С ВАШЕЙ УСТАНОВКОЙ SDL2_image !!!
sdl2_image_cflags = []
sdl2_image_libs = []
sdl_image_config_successful = False
try:
    if platform.system() == "Windows":
        SDL2IMAGE_BASE_DIR = "C:/Libs/SDL2_image-2.8.8" # <--- УКАЖИТЕ ВАШ ПУТЬ
        if not os.path.isdir(SDL2IMAGE_BASE_DIR):
            print(f"ERROR: SDL2_image base directory not found at '{SDL2IMAGE_BASE_DIR}'.")
        else:
            SDL2IMAGE_INCLUDE_DIR = os.path.join(SDL2IMAGE_BASE_DIR, "include")
            python_arch = platform.architecture()[0]
            SDL2IMAGE_LIB_SUBDIR = "x64" if python_arch == "64bit" else ("x86" if python_arch == "32bit" else None)
            if not SDL2IMAGE_LIB_SUBDIR: print(f"ERROR: Unknown Python architecture for SDL2_image '{python_arch}'.")
            SDL2IMAGE_LIB_DIR = os.path.join(SDL2IMAGE_BASE_DIR, "lib", SDL2IMAGE_LIB_SUBDIR) if SDL2IMAGE_LIB_SUBDIR else None

            image_header_check_path = os.path.join(SDL2IMAGE_INCLUDE_DIR, "SDL_image.h") # SDL_image.h обычно лежит прямо в include или include/SDL2
            if not os.path.exists(image_header_check_path): # Проверяем альтернативный путь SDL2/SDL_image.h
                 image_header_check_path = os.path.join(SDL2IMAGE_INCLUDE_DIR, "SDL2", "SDL_image.h")

            image_lib_check_path = os.path.join(SDL2IMAGE_LIB_DIR, "SDL2_image.lib") if SDL2IMAGE_LIB_DIR else None

            if os.path.isdir(SDL2IMAGE_INCLUDE_DIR) and SDL2IMAGE_LIB_DIR and os.path.isdir(SDL2IMAGE_LIB_DIR) and \
               os.path.exists(image_header_check_path) and (image_lib_check_path and os.path.exists(image_lib_check_path)):
                sdl2_image_cflags.append(f'/I{SDL2IMAGE_INCLUDE_DIR}')
                sdl2_image_libs.extend([f'/LIBPATH:{SDL2IMAGE_LIB_DIR}', 'SDL2_image.lib'])
                sdl_image_config_successful = True
            else:
                print("ERROR: Manual SDL2_image configuration for Windows failed.")
                print(f"  SDL2_image Include Dir: '{SDL2IMAGE_INCLUDE_DIR}' (exists: {os.path.isdir(SDL2IMAGE_INCLUDE_DIR)})")
                print(f"  SDL_image.h path used for check: '{image_header_check_path}' (exists: {os.path.exists(image_header_check_path)})")
                print(f"  SDL2_image Lib Dir: '{SDL2IMAGE_LIB_DIR}' (exists: {os.path.isdir(SDL2IMAGE_LIB_DIR) if SDL2IMAGE_LIB_DIR else 'N/A'})")
                print(f"  SDL2_image.lib path used for check: '{image_lib_check_path}' (exists: {os.path.exists(image_lib_check_path) if image_lib_check_path else 'N/A'})")

    else: # Linux or macOS
        try:
            sdl2_image_cflags_str = os.popen('pkg-config --cflags SDL2_image').read().strip()
            sdl2_image_libs_str = os.popen('pkg-config --libs SDL2_image').read().strip()
            if sdl2_image_cflags_str: sdl2_image_cflags.extend(sdl2_image_cflags_str.split())
            if sdl2_image_libs_str: sdl2_image_libs.extend(sdl2_image_libs_str.split())
            if sdl2_image_cflags and sdl2_image_libs: sdl_image_config_successful = True
            else: print("Warning: pkg-config SDL2_image output was empty.")
        except Exception as e: print(f"Warning: pkg-config SDL2_image failed: {e}.")
except Exception as e:
    print(f"ERROR: An unexpected error occurred during SDL2_image configuration: {e}")

if not sdl_image_config_successful and not os.getenv("SETUPPY_IGNORE_SDLIMAGE_FAILURE"):
    print("CRITICAL: SDL2_image configuration was not successful. Image loading will likely fail.")
    sys.exit("SDL2_image configuration failed.")
else:
    print("Info: SDL2_image configuration successful or ignored.")

#--- Compiler and Linker Arguments ---
# Базовые агрессивные, но ПОРТАТИВНЫЕ флаги
# Убраны /arch:AVX2 и -march=native для большей портативности
base_compile_args_msvc = ['/std:c++17', '/O2', '/GL', '/openmp', '/EHsc', '/W3', '/DNDEBUG', '/MD', '/fp:fast', '/bigobj']
base_link_args_msvc = ['/LTCG', '/INCREMENTAL:NO', '/OPT:REF', '/OPT:ICF'] # Добавлены оптимизации линкера

base_compile_args_gcc_clang = ['-std=c++17', '-O3', '-Wall', '-Wextra', '-fPIC', '-fopenmp', '-DNDEBUG', '-flto', '-ffast-math']
# -mtune=generic может быть полезен, но компиляторы обычно делают хорошую работу по умолчанию для x86-64
# base_compile_args_gcc_clang.append('-mtune=generic')
base_link_args_gcc_clang = ['-fopenmp', '-flto']

final_compile_args = []
final_link_args = []
compiler_type = None

final_compile_args.extend(sdl2_cflags)
final_compile_args.extend(sdl2_ttf_cflags)
final_compile_args.extend(sdl2_image_cflags)

final_link_args.extend(sdl2_libs)
final_link_args.extend(sdl2_ttf_libs)
final_link_args.extend(sdl2_image_libs)

if PGO_ENABLED:
    print(f"\n!!! PGO АКТИВИРОВАНА: PGO_BUILD_PHASE = {PGO_PHASE_INTERNAL} !!!")
    print("!!! Процесс PGO: ИНСТРУМЕНТАЦИЯ -> ЗАПУСК ПРИЛОЖЕНИЯ -> ОПТИМИЗАЦИЯ !!!")
    print(f"!!! Данные профиля будут в/из: {pgo_profile_dir_abs} !!!")
    if PGO_PHASE_INTERNAL == 'OPTIMIZE':
        print("!!! УБЕДИТЕСЬ, ЧТО ВЫ СГЕНЕРИРОВАЛИ ДАННЫЕ ПРОФИЛЯ (запустив инструментированную версию)! !!!\n")
    elif PGO_PHASE_INTERNAL == 'INSTRUMENT':
        print("!!! ПОСЛЕ ЭТОЙ СБОРКИ ЗАПУСТИТЕ ВАШЕ ПРИЛОЖЕНИЕ для генерации данных профиля! !!!\n")
else:
    print("\n!!! Используются агрессивные, но портативные флаги оптимизации (БЕЗ PGO) !!!")
    print("!!! Флаги 'fast-math' могут повлиять на точность вычислений с плавающей точкой. !!!\n")


if platform.system() == "Windows":
    compiler_type = "msvc"
    current_compile_args = list(base_compile_args_msvc)
    current_link_args = list(base_link_args_msvc)

    if PGO_ENABLED:
        pgo_pgd_file = os.path.join(pgo_profile_dir_abs, f'{MODULE_NAME}.pgd')
        if PGO_PHASE_INTERNAL == 'INSTRUMENT':
            print(f"Info: MSVC PGO - ИНСТРУМЕНТАЦИЯ. PGD-файл будет: {pgo_pgd_file}")
            if '/GL' not in current_compile_args: current_compile_args.append('/GL') # Обязательно для PGO
            current_compile_args.append('/PROFILE')
            if '/LTCG' not in current_link_args: current_link_args.append('/LTCG')
            current_link_args.append(f'/GENPROFILE:PGD="{pgo_pgd_file}"')
            # Убедимся, что нет конфликтующих флагов оптимизации PGO
            current_link_args = [arg for arg in current_link_args if not arg.startswith(('/LTCG:PGOPTIMIZE', '/USEPROFILE'))]

        elif PGO_PHASE_INTERNAL == 'OPTIMIZE':
            print(f"Info: MSVC PGO - ОПТИМИЗАЦИЯ. Используется PGD-файл: {pgo_pgd_file}")
            if not os.path.exists(pgo_pgd_file):
                print(f"КРИТИЧЕСКАЯ ОШИБКА PGO: Файл {pgo_pgd_file} не найден для OPTIMIZE.")
                sys.exit("PGO Оптимизация: отсутствуют данные профиля.")
            if '/GL' not in current_compile_args: current_compile_args.append('/GL')
            current_compile_args.append(f'/USEPROFILE:PGD="{pgo_pgd_file}"')
            # Удаляем общий /LTCG и флаги инструментации, добавляем оптимизирующий PGO флаг
            current_link_args = [arg for arg in current_link_args if not (arg == '/LTCG' or arg.startswith('/GENPROFILE'))]
            current_link_args.append(f'/LTCG:PGOPTIMIZE')
            current_link_args.append(f'/USEPROFILE:PGD="{pgo_pgd_file}"') # /USEPROFILE также для линкера

    final_compile_args.extend(current_compile_args)
    final_link_args.extend(current_link_args)

elif platform.system() == "Linux" or platform.system() == "Darwin":
    if "clang" in os.environ.get('CXX', '').lower() or "clang" in os.environ.get('CC', '').lower():
        compiler_type = "clang"
    else:
        compiler_type = "gcc"
    
    current_compile_args = list(base_compile_args_gcc_clang)
    current_link_args = list(base_link_args_gcc_clang)

    if PGO_ENABLED:
        profile_dir_flag_part = f'"{pgo_profile_dir_abs}"' # Кавычки для путей с пробелами
        profile_generate_flag = f'-fprofile-generate={profile_dir_flag_part}'
        profile_use_flag = f'-fprofile-use={profile_dir_flag_part}'
        
        if '-flto' not in current_compile_args: current_compile_args.append('-flto')
        if '-flto' not in current_link_args: current_link_args.append('-flto')

        if PGO_PHASE_INTERNAL == 'INSTRUMENT':
            print(f"Info: {compiler_type.upper()} PGO - ИНСТРУМЕНТАЦИЯ. Данные в: {pgo_profile_dir_abs}")
            current_compile_args.append(profile_generate_flag)
            current_link_args.append(profile_generate_flag)
        elif PGO_PHASE_INTERNAL == 'OPTIMIZE':
            print(f"Info: {compiler_type.upper()} PGO - ОПТИМИЗАЦИЯ. Данные из: {pgo_profile_dir_abs}")
            # Проверка наличия .gcda файлов (упрощенная)
            has_gcda_files = any(f.endswith('.gcda') for f_dir in [pgo_profile_dir_abs, os.getcwd(), cpp_src_dir] if os.path.exists(f_dir) for f in os.listdir(f_dir) )
            if not has_gcda_files:
                 print(f"ПРЕДУПРЕЖДЕНИЕ PGO: Данные профиля (.gcda) не найдены в {pgo_profile_dir_abs} или текущем каталоге. Убедитесь, что инструментированная версия была запущена.")
                 # Не прерываем сборку, но предупреждаем
            current_compile_args.append(profile_use_flag)
            if compiler_type == "gcc":
                current_compile_args.append('-fprofile-correction') # Помогает с неточными данными профиля
            current_link_args.append(profile_use_flag)
            
    final_compile_args.extend(current_compile_args)
    final_link_args.extend(current_link_args)
else:
    compiler_type = "unknown"
    print("Warning: Тип компилятора не определен. Используются общие флаги C++17 (без PGO).")
    final_compile_args.extend(['-std=c++17', '-O3', '-DNDEBUG', '-ffast-math', '-flto'])
    final_link_args.extend(['-flto'])


# --- Extension Module Definition ---
ext_modules = [
    Extension(
        MODULE_NAME,
        sources=[os.path.join(cpp_src_dir, f'{MODULE_NAME}.cpp')],
        include_dirs=[
            pybind11.get_include(),
            pybind11.get_include(True),
            glm_include_dir,
            cpp_src_dir,
        ],
        language='c++',
        extra_compile_args=list(set(final_compile_args)),
        extra_link_args=list(set(final_link_args)),
    ),
]

# --- Setup Configuration ---
try:
    long_description = open(os.path.join(current_script_path, 'README.md'), encoding='utf-8').read()
except FileNotFoundError:
    long_description = f'PGO-enabled C++ core ({MODULE_NAME}) for software 3D renderer'

setup(
    name='CppRendererCorePkg', # Имя пакета может отличаться от имени модуля
    version='0.3.1', # Увеличиваем версию
    author='Your Name',
    author_email='your.email@example.com',
    description=f'PGO-enabled C++ core ({MODULE_NAME}) for software 3D renderer',
    long_description=long_description,
    long_description_content_type="text/markdown",
    ext_modules=ext_modules,
    zip_safe=False,
    python_requires=">=3.8",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Graphics :: 3D Rendering",
        "Programming Language :: Python :: 3",
        "Programming Language :: C++",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
    ],
    keywords=f'3d graphics renderer cpp python pybind11 glm openmp sdl sdl2 pgo {MODULE_NAME}',
    project_urls={
        'Bug Reports': 'https://github.com/your_username/your_project_repo/issues',
        'Source': 'https://github.com/your_username/your_project_repo/',
    },
)

print("\n--- Завершение скрипта сборки ---")
print(f"Info: SDL2 сконфигурирован {'успешно' if sdl_config_successful else 'НЕУСПЕШНО или проигнорировано'}.")
print(f"Info: SDL2_ttf сконфигурирован {'успешно' if sdl_ttf_config_successful else 'НЕУСПЕШНО или проигнорировано'}.")     # <--- ДОБАВЛЕНО
print(f"Info: SDL2_image сконфигурирован {'успешно' if sdl_image_config_successful else 'НЕУСПЕШНО или проигнорировано'}.") # <--- ДОБАВЛЕНО
print(f"Info: Тип компилятора: {compiler_type if compiler_type else 'Unknown'}")
if PGO_ENABLED:
    print(f"Info: Сборка с PGO: PGO_BUILD_PHASE = {PGO_PHASE_INTERNAL}")
    if PGO_PHASE_INTERNAL == 'INSTRUMENT':
        print("ДЕЙСТВИЕ: Теперь ЗАПУСТИТЕ ваше приложение, чтобы сгенерировать данные профиля!")
    elif PGO_PHASE_INTERNAL == 'OPTIMIZE':
        print("Info: Сборка с PGO-оптимизацией завершена (или предпринята попытка).")
else:
    print("Info: Сборка без PGO (используются стандартные агрессивные флаги).")
print(f"Info: Итоговые флаги компиляции: {final_compile_args}")
print(f"Info: Итоговые флаги компоновки: {final_link_args}")