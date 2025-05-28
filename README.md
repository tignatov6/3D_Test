# 3D_Test
My pygame 3D test
nuitka --standalone --output-dir=build/nuitka_dist --output-filename="MyRendererApp_Optimized" --include-module=cpp_renderer_core --include-plugin-files="C:/Libs/SDL2-2.28.4/bin/SDL2.dll" --include-plugin-files="C:/Libs/SDL2-2.28.4/bin/SDL2main.dll" --include-plugin-files="C:/Windows/System32/vcomp140.dll" --include-plugin-files="C:/Windows/System32/concrt140.dll" --include-data-dir=assets=assets --lto=yes --jobs=8 main.py

python setup.py build_ext --inplace