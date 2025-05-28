import pygame
import numpy as np
from settings import * # WIN_RES, BG_COLOR, SORT, RANDOM_COL, CLIPPING, BACK_CULL, LIGHT, glm
# VERTEX_DATA и USE_VERTEX_NORMALS теперь приходят через vertex_data_format_info
import random

# --- Вспомогательные функции (calculate_triangle_normal, is_front_facing) ---
def calculate_triangle_normal(v1_world, v2_world, v3_world):
    edge1 = v2_world - v1_world; edge2 = v3_world - v1_world
    normal = glm.cross(edge1, edge2)
    if glm.length(normal) < 1e-6: return glm.vec3(0,0,1)
    return glm.normalize(normal)

def is_front_facing(normal, camera_pos_world, triangle_center_world):
    view_dir = glm.normalize(camera_pos_world - triangle_center_world)
    return glm.dot(normal, view_dir) > 0

class Renderer:
    def __init__(self, app):
        self.app = app; self.screen = app.window
        try: self.camera = app.camera 
        except AttributeError: self.camera = app.player 
        self.triangles = []; self.object_cache = {}

    def project_vertex(self, vertex_world_tuple): 
        view_space = self.camera.get_view_matrix() @ glm.vec4(*vertex_world_tuple, 1.0)
        clip_space = self.app.projection_matrix @ view_space
        if abs(clip_space.w) < 1e-6: return None
        if clip_space.w < 0: return None
        ndc_x = clip_space.x / clip_space.w; ndc_y = clip_space.y / clip_space.w
        x = (ndc_x + 1) * (WIN_RES[0] / 2); y = (1 - ndc_y) * (WIN_RES[1] / 2) 
        return (x, y)
    
    def get_view_z(self, vertex_world_tuple): 
        view_space_vertex_homogeneous = self.camera.get_view_matrix() @ glm.vec4(*vertex_world_tuple, 1.0)
        return view_space_vertex_homogeneous.z

    def render_mesh(self, object_id, vertex_data, vertex_data_format_info,
                    position=glm.vec3(0,0,0), rotation=glm.vec3(0,0,0), scale=glm.vec3(1,1,1)):     

        current_params_tuple = (position.x, position.y, position.z, 
                                rotation.x, rotation.y, rotation.z, 
                                scale.x, scale.y, scale.z) # Используем кортеж примитивов для сравнения

        VERTEX_DATA_STRIDE = vertex_data_format_info['VERTEX_DATA_STRIDE']
        USE_VERTEX_NORMALS_mesh = vertex_data_format_info['USE_VERTEX_NORMALS']

        cached_data = self.object_cache.get(object_id)
        model_matrix = None; normal_transform_matrix = None
        cached_world_vertices_triangles = None; cached_triangle_normals = None       
        recalculate_matrices = True; recalculate_world_coords = True

        if cached_data:
            # Сравниваем кортежи примитивных типов для надежности
            if cached_data['params_tuple'] == current_params_tuple:
                recalculate_matrices = False; recalculate_world_coords = False 
                model_matrix = cached_data['model_matrix']
                normal_transform_matrix = cached_data['normal_matrix']
                cached_world_vertices_triangles = cached_data.get('world_vertices_triangles')
                cached_triangle_normals = cached_data.get('triangle_normals')
            else:
                cached_data['params_tuple'] = current_params_tuple 
        else:
            cached_data = {'params_tuple': current_params_tuple}
            self.object_cache[object_id] = cached_data

        if recalculate_matrices:
            s_m = glm.scale(glm.mat4(1.0),scale); r_x_m = glm.rotate(glm.mat4(1.0),glm.radians(rotation.x),glm.vec3(1,0,0))
            r_y_m = glm.rotate(glm.mat4(1.0),glm.radians(rotation.y),glm.vec3(0,1,0)); r_z_m = glm.rotate(glm.mat4(1.0),glm.radians(rotation.z),glm.vec3(0,0,1))
            rot_m = r_z_m @ r_y_m @ r_x_m; t_m = glm.translate(glm.mat4(1.0),position)
            model_matrix = t_m @ rot_m @ s_m; normal_transform_matrix = glm.mat3(model_matrix) 
            cached_data['model_matrix'] = model_matrix; cached_data['normal_matrix'] = normal_transform_matrix
            recalculate_world_coords = True 
            cached_data.pop('world_vertices_triangles',None); cached_data.pop('triangle_normals',None)
            cached_world_vertices_triangles = None; cached_triangle_normals = None

        num_floats_per_triangle = VERTEX_DATA_STRIDE * 3
        
        if recalculate_world_coords or cached_world_vertices_triangles is None or \
           ((BACK_CULL or LIGHT) and cached_triangle_normals is None):
            
            new_w_v_tris = []; new_tri_norms = [] if (BACK_CULL or LIGHT) else None
            for i in range(0,len(vertex_data),num_floats_per_triangle):
                loc_pos = []; loc_norms = [] 
                for k_v in range(3): 
                    s_idx = i + k_v*VERTEX_DATA_STRIDE
                    loc_pos.append(glm.vec3(vertex_data[s_idx:s_idx+3]))
                    if USE_VERTEX_NORMALS_mesh and VERTEX_DATA_STRIDE>=9: loc_norms.append(glm.vec3(vertex_data[s_idx+6:s_idx+9]))
                v0w=glm.vec3((model_matrix@glm.vec4(loc_pos[0],1.0)).xyz); v1w=glm.vec3((model_matrix@glm.vec4(loc_pos[1],1.0)).xyz)
                v2w=glm.vec3((model_matrix@glm.vec4(loc_pos[2],1.0)).xyz); cur_tri_w_verts = [v0w,v1w,v2w]
                new_w_v_tris.append(cur_tri_w_verts)
                if BACK_CULL or LIGHT:
                    tri_n_w = glm.vec3(0,0,1)
                    if USE_VERTEX_NORMALS_mesh and len(loc_norms)==3:
                        n0w=glm.normalize(normal_transform_matrix@loc_norms[0]);n1w=glm.normalize(normal_transform_matrix@loc_norms[1])
                        n2w=glm.normalize(normal_transform_matrix@loc_norms[2]);tri_n_w=glm.normalize(n0w+n1w+n2w) 
                    else: tri_n_w=calculate_triangle_normal(v0w,v1w,v2w)
                    new_tri_norms.append(tri_n_w)
            cached_data['world_vertices_triangles']=new_w_v_tris; cached_world_vertices_triangles=new_w_v_tris
            if new_tri_norms is not None: cached_data['triangle_normals']=new_tri_norms; cached_triangle_normals=new_tri_norms
        
        for tri_idx, world_verts_cur_tri in enumerate(cached_world_vertices_triangles):
            v0w,v1w,v2w = world_verts_cur_tri
            base_v_data_idx = tri_idx*num_floats_per_triangle; vtx_colors_flt = []
            for k_v in range(3):
                s_c_idx = base_v_data_idx+k_v*VERTEX_DATA_STRIDE+3 
                if VERTEX_DATA_STRIDE>=6: vtx_colors_flt.append(tuple(vertex_data[s_c_idx:s_c_idx+3]))
                else: vtx_colors_flt.append((0.5,0.5,0.5))
            intensity=1.0
            if BACK_CULL or LIGHT:
                cen_w=(v0w+v1w+v2w)/3.0; norm_w=cached_triangle_normals[tri_idx]
                if BACK_CULL and not is_front_facing(norm_w,self.camera.position,cen_w): continue 
                if LIGHT: intensity=max(0.0,glm.dot(norm_w,glm.normalize(self.camera.position-cen_w)))
            if CLIPPING:
                vm=self.camera.get_view_matrix();pm=self.app.projection_matrix
                clips_all=[pm@(vm@glm.vec4(v_w,1.0)) for v_w in world_verts_cur_tri]
                if all(v.w<1e-6 for v in clips_all):continue
                if (all(v.x<-v.w+1e-6 for v in clips_all)or all(v.x>v.w-1e-6 for v in clips_all)or
                    all(v.y<-v.w+1e-6 for v in clips_all)or all(v.y>v.w-1e-6 for v in clips_all)or
                    all(v.z<-v.w+1e-6 for v in clips_all)or all(v.z>v.w-1e-6 for v in clips_all)):continue
            scr_coords=[];avg_z=0.0;valid_proj=True
            for v_w in world_verts_cur_tri:
                scr_pos=self.project_vertex((v_w.x,v_w.y,v_w.z))
                if scr_pos: scr_coords.append(scr_pos);avg_z+=self.get_view_z((v_w.x,v_w.y,v_w.z))
                else: valid_proj=False;break 
            if not valid_proj or len(scr_coords)!=3:continue
            avg_z/=3.0;avg_r=sum(c[0] for c in vtx_colors_flt)/3.0;avg_g=sum(c[1] for c in vtx_colors_flt)/3.0
            avg_b=sum(c[2] for c in vtx_colors_flt)/3.0
            s_r,s_g,s_b = (avg_r*intensity,avg_g*intensity,avg_b*intensity) if LIGHT else (avg_r,avg_g,avg_b)
            fin_col=(int(min(max(s_r*255,0),255)),int(min(max(s_g*255,0),255)),int(min(max(s_b*255,0),255)))
            self.triangles.append([scr_coords,avg_z,fin_col])
            
    def render(self): 
        fcr=int(BG_COLOR.x*255);fcg=int(BG_COLOR.y*255);fcb=int(BG_COLOR.z*255)
        self.screen.fill((fcr,fcg,fcb))
        if SORT:self.triangles.sort(key=lambda i:i[1]) 
        for tri_data in self.triangles:
            scr_pts,_,fin_col=tri_data
            if len(scr_pts)==3:
                try:
                    cur_col=(random.randint(0,255),random.randint(0,255),random.randint(0,255)) if RANDOM_COL else fin_col
                    pygame.draw.polygon(self.screen,cur_col,scr_pts,0) 
                except Exception as e:print(f'Err display tri: {tri_data}, err: {e}')
        self.triangles=[]