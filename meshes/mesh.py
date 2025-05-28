# meshes/mesh.py
import glm
from settings import VERTEX_DATA_STRIDE, USE_VERTEX_NORMALS
from meshes.obj_loader import load_obj_file 
import numpy as np

class Mesh:
    def __init__(self, app, obj_filename: str, default_color_tuple: tuple = (0.8, 0.8, 0.8)):
        self.app = app
        self.obj_filename = obj_filename
        
        self.vertex_data_format_info = {
            'VERTEX_DATA_STRIDE': VERTEX_DATA_STRIDE,
            'USE_VERTEX_NORMALS': USE_VERTEX_NORMALS
        }
        self.vertex_data_np = self._load_and_prepare_vertex_data(default_color_tuple)

    def _load_and_prepare_vertex_data(self, default_color_tuple: tuple) -> np.ndarray:
        vertex_data_loaded = load_obj_file(self.obj_filename, default_color=default_color_tuple)

        if not isinstance(vertex_data_loaded, np.ndarray):
            vertex_data_loaded = np.array(vertex_data_loaded, dtype=np.float32)
        elif vertex_data_loaded.dtype != np.float32:
            vertex_data_loaded = vertex_data_loaded.astype(np.float32)

        stride = self.vertex_data_format_info['VERTEX_DATA_STRIDE']
        if vertex_data_loaded.size > 0:
            if vertex_data_loaded.ndim == 1:
                if vertex_data_loaded.size % stride != 0:
                    print(f"WARNING (Mesh): Vertex data size ({vertex_data_loaded.size}) for '{self.obj_filename}' is not a multiple of stride ({stride}).")
            elif vertex_data_loaded.ndim == 2:
                 if vertex_data_loaded.shape[1] != stride:
                     print(f"WARNING (Mesh): Vertex data shape ({vertex_data_loaded.shape}) for '{self.obj_filename}' does not match stride ({stride}) in the second dimension.")
                 vertex_data_loaded = vertex_data_loaded.flatten() # Ensure flat array for C++
            else:
                print(f"WARNING (Mesh): Vertex data for '{self.obj_filename}' has an unexpected number of dimensions: {vertex_data_loaded.ndim}.")
        
        if vertex_data_loaded.size == 0 and self.obj_filename:
            # print(f"Warning (Mesh): No vertex data loaded for '{self.obj_filename}'. Using empty array.")
            return np.array([], dtype=np.float32) 
            
        return vertex_data_loaded

    def render(self, game_object_id: int, position: glm.vec3, rotation: glm.vec3, scale: glm.vec3):
        if hasattr(self.app, 'renderer') and hasattr(self.app.renderer, 'render_mesh'):
            if self.vertex_data_np.size > 0:
                self.app.renderer.render_mesh(
                    object_id=game_object_id,
                    vertex_data_np=self.vertex_data_np,
                    vertex_data_format_info=self.vertex_data_format_info,
                    position=position,
                    rotation=rotation,
                    scale=scale
                )
        # else:
            # print(f"ERROR (Mesh): self.app.renderer or its method render_mesh not found for mesh '{self.obj_filename}'.")