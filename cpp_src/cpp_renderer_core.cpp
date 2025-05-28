// --- START OF FILE cpp_renderer_core.cpp ---

#define GLM_ENABLE_EXPERIMENTAL

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h> // Для std::vector, std::list, std::array, std::map
#include <pybind11/iostream.h> // Для py::print

#include <vector>
#include <array>
#include <algorithm> 
#include <cmath>     
#include <execution> 
#include <list>
#include <unordered_map>
#include <map> 
#include <mutex>
#include <memory>
#include <stdexcept> 
#include <string>    
#include <iostream> // Для std::cerr
#include <unordered_map> // For UI elements
#include <mutex>         // For UI elements thread safety

// SDL Includes
#include <SDL.h>
#include <SDL_render.h>
#include <SDL_ttf.h>     // For text rendering
// SDL_syswm.h больше не нужен

// OpenMP
#ifdef _MSC_VER
    #include <omp.h>
#else
    #include <omp.h>
#endif

// GLM includes
#include "../vendor/glm/glm.hpp"
#include "../vendor/glm/gtc/matrix_transform.hpp"
#include "../vendor/glm/gtc/type_ptr.hpp"
#include "../vendor/glm/gtx/norm.hpp"
#include "../vendor/glm/gtx/hash.hpp"

namespace py = pybind11;

// --- SDL Global Variables ---
static SDL_Window* g_sdl_native_window = nullptr; 
static SDL_Renderer* g_sdl_renderer = nullptr;
static std::array<unsigned char, 3> g_background_color_cpp = {0, 0, 0};
static int g_window_width_cpp = 0;
static int g_window_height_cpp = 0;
static std::mutex g_sdl_resources_mutex; 
static bool g_sdl_subsystems_initialized_by_cpp = false;

// --- UI Element Data Structures ---
struct CppUiElementData {
    std::string id;
    SDL_Rect rect; // x, y, w, h
    bool visible;
    // Common properties can go here
};

struct CppButtonData : CppUiElementData {
    std::string text;
    SDL_Color text_color;
    SDL_Color background_color;
    SDL_Color border_color;
    int border_width;
    int font_size; // Added font_size for buttons
    // Note: hover/click states are managed by Python, C++ just gets current appearance
};

struct CppTextData : CppUiElementData {
    std::string text;
    SDL_Color text_color;
    int font_size; // Specific font size for this label
    // std::string font_name; // Future: if specific fonts per label are needed
};

// Global storage for UI elements
static std::unordered_map<std::string, CppButtonData> g_cpp_buttons;
static std::unordered_map<std::string, CppTextData> g_cpp_texts;
static std::mutex g_ui_elements_mutex;

// Font Management
const char* FONT_FILE_PATH = "data/fonts/DejaVuSans.ttf"; // Global font file path
const int DEFAULT_UI_FONT_SIZE = 18; // Default font size if not specified or load fails for specific size

static std::map<int, TTF_Font*> g_font_cache;
static std::mutex g_font_cache_mutex;

// Helper function to get/load font
TTF_Font* get_font(int size) {
    if (size <= 0) { // Ensure valid size, fallback to default
        size = DEFAULT_UI_FONT_SIZE;
    }
    std::lock_guard<std::mutex> lock(g_font_cache_mutex);
    
    auto it = g_font_cache.find(size);
    if (it != g_font_cache.end()) {
        return it->second; // Return cached font
    }

    // Font not in cache, try to load it
    TTF_Font* font = TTF_OpenFont(FONT_FILE_PATH, size);
    if (!font) {
        py::print(std::string("C++ Warning: TTF_OpenFont(\"") + FONT_FILE_PATH + std::string("\", ") + std::to_string(size) + std::string(") failed: ") + TTF_GetError());
        // Try to get default size font as a fallback if requested size failed
        if (size != DEFAULT_UI_FONT_SIZE) {
            it = g_font_cache.find(DEFAULT_UI_FONT_SIZE);
            if (it != g_font_cache.end()) {
                 py::print(std::string("C++: Using default size (") + std::to_string(DEFAULT_UI_FONT_SIZE) +std::string(") font as fallback."));
                return it->second;
            }
        }
        return nullptr; // Failed to load and no fallback available in cache
    }
    
    py::print(std::string("C++: Loaded and cached font '") + FONT_FILE_PATH + std::string("' at size ") + std::to_string(size) + std::string("."));
    g_font_cache[size] = font;
    return font;
}


// --- Data Structures (CppClipVertex, CppScreenTriangle, CppWorldDataL2, CacheKeyL2, LruCacheL2Internal, CacheKeyL1, LruCacheL1Internal) ---
struct CppClipVertex {
    glm::vec4 position_clip;
    glm::vec3 color_f;
    float view_z;
    glm::vec3 world_pos;
    bool is_original;

    CppClipVertex(const glm::vec4& pc, const glm::vec3& c, float vz, const glm::vec3& wp, bool io) :
        position_clip(pc), color_f(c), view_z(vz), world_pos(wp), is_original(io) {}
};

struct CppScreenTriangle {
    std::array<std::array<float, 2>, 3> screen_coords; 
    float depth;
    std::array<unsigned char, 3> color_final_uint8;   
};

struct CppWorldDataL2 {
    std::vector<float> world_vertices_flat;
    std::vector<float> world_face_normals_flat;
    std::vector<float> vertex_colors_flat;
    size_t num_source_triangles;

    CppWorldDataL2() : num_source_triangles(0) {}
};

struct CacheKeyL2 {
    uintptr_t object_id;
    std::array<float, 9> transform_params_hash_relevant; 
    bool use_vertex_normals_config;

    bool operator==(const CacheKeyL2& other) const {
        return object_id == other.object_id &&
               transform_params_hash_relevant == other.transform_params_hash_relevant &&
               use_vertex_normals_config == other.use_vertex_normals_config;
    }
};

namespace std {
    template <> struct hash<CacheKeyL2> {
        size_t operator()(const CacheKeyL2& k) const {
            size_t seed = hash<uintptr_t>{}(k.object_id);
            seed ^= hash<bool>{}(k.use_vertex_normals_config) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
            for (int i = 0; i < 9; ++i) {
                seed ^= hash<float>{}(k.transform_params_hash_relevant[i]) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
            }
            return seed;
        }
    };
} 

class LruCacheL2Internal {
public:
    LruCacheL2Internal() : capacity_(0) {} 
    void set_capacity(size_t capacity) {
        std::lock_guard<std::mutex> lock(cache_mutex_);
        capacity_ = capacity > 0 ? capacity : 1; 
        while (items_map_.size() > capacity_) { evict_oldest_nolock(); }
    }
    size_t get_capacity() const { std::lock_guard<std::mutex> lock(cache_mutex_); return capacity_; }
    void clear() { std::lock_guard<std::mutex> lock(cache_mutex_); items_map_.clear(); lru_list_.clear(); }
    std::shared_ptr<const CppWorldDataL2> get(const CacheKeyL2& key) {
        std::lock_guard<std::mutex> lock(cache_mutex_);
        auto it = items_map_.find(key);
        if (it == items_map_.end()) { return nullptr; }
        lru_list_.erase(it->second.lru_iterator);
        lru_list_.push_front(key);
        it->second.lru_iterator = lru_list_.begin();
        return it->second.data_ptr;
    }
    void put(const CacheKeyL2& key, CppWorldDataL2 data_to_cache) {
        if (capacity_ == 0) return; 
        std::lock_guard<std::mutex> lock(cache_mutex_);
        auto data_ptr = std::make_shared<CppWorldDataL2>(std::move(data_to_cache));
        auto it = items_map_.find(key);
        if (it != items_map_.end()) { 
            lru_list_.erase(it->second.lru_iterator); 
            it->second.data_ptr = data_ptr;          
            lru_list_.push_front(key);               
            it->second.lru_iterator = lru_list_.begin(); 
        } else { 
            if (items_map_.size() >= capacity_) { evict_oldest_nolock(); }
            lru_list_.push_front(key);
            items_map_.emplace(key, CacheEntry{data_ptr, lru_list_.begin()});
        }
    }
private:
    struct CacheEntry {
        std::shared_ptr<CppWorldDataL2> data_ptr;
        std::list<CacheKeyL2>::iterator lru_iterator;
    };
    void evict_oldest_nolock() {
        if (lru_list_.empty()) return;
        CacheKeyL2 oldest_key = lru_list_.back();
        lru_list_.pop_back();
        items_map_.erase(oldest_key);
    }
    size_t capacity_;
    std::list<CacheKeyL2> lru_list_;
    std::unordered_map<CacheKeyL2, CacheEntry> items_map_;
    mutable std::mutex cache_mutex_; 
};
static LruCacheL2Internal global_l2_cache_cpp_instance;

struct CacheKeyL1 {
    uintptr_t object_id;
    std::array<float, 9> transform_params_hash_relevant; 
    std::size_t view_matrix_hash;
    std::size_t projection_matrix_hash;
    bool light_enabled;
    bool back_cull_enabled;
    bool clipping_enabled; 
    bool debug_clipping_enabled;
    std::array<unsigned char, 3> debug_clipped_color; 
    float small_tri_area_threshold;

    bool operator==(const CacheKeyL1& other) const {
        return object_id == other.object_id &&
               transform_params_hash_relevant == other.transform_params_hash_relevant &&
               view_matrix_hash == other.view_matrix_hash &&
               projection_matrix_hash == other.projection_matrix_hash &&
               light_enabled == other.light_enabled &&
               back_cull_enabled == other.back_cull_enabled &&
               clipping_enabled == other.clipping_enabled &&
               debug_clipping_enabled == other.debug_clipping_enabled &&
               debug_clipped_color == other.debug_clipped_color &&
               small_tri_area_threshold == other.small_tri_area_threshold;
    }
};
namespace std {
    template <> struct hash<CacheKeyL1> {
        size_t operator()(const CacheKeyL1& k) const {
            size_t seed = hash<uintptr_t>{}(k.object_id);
            for (int i = 0; i < 9; ++i) {
                seed ^= hash<float>{}(k.transform_params_hash_relevant[i]) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
            }
            seed ^= k.view_matrix_hash + 0x9e3779b9 + (seed << 6) + (seed >> 2);
            seed ^= k.projection_matrix_hash + 0x9e3779b9 + (seed << 6) + (seed >> 2);
            seed ^= hash<bool>{}(k.light_enabled) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
            seed ^= hash<bool>{}(k.back_cull_enabled) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
            seed ^= hash<bool>{}(k.clipping_enabled) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
            seed ^= hash<bool>{}(k.debug_clipping_enabled) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
            for(int i=0; i<3; ++i) {
                seed ^= hash<unsigned char>{}(k.debug_clipped_color[i]) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
            }
            seed ^= hash<float>{}(k.small_tri_area_threshold) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
            return seed;
        }
    };
} 
class LruCacheL1Internal {
public:
    LruCacheL1Internal() : capacity_(0) {}
    void set_capacity(size_t capacity) {
        std::lock_guard<std::mutex> lock(cache_mutex_);
        capacity_ = capacity > 0 ? capacity : 1;
        while (items_map_.size() > capacity_) { evict_oldest_nolock(); }
    }
    size_t get_capacity() const { std::lock_guard<std::mutex> lock(cache_mutex_); return capacity_; }
    void clear() { std::lock_guard<std::mutex> lock(cache_mutex_); items_map_.clear(); lru_list_.clear(); }
    std::shared_ptr<const std::vector<CppScreenTriangle>> get(const CacheKeyL1& key) {
        std::lock_guard<std::mutex> lock(cache_mutex_);
        auto it = items_map_.find(key);
        if (it == items_map_.end()) { return nullptr; }
        lru_list_.erase(it->second.lru_iterator);
        lru_list_.push_front(key);
        it->second.lru_iterator = lru_list_.begin();
        return it->second.data_ptr;
    }
    void put(const CacheKeyL1& key, std::vector<CppScreenTriangle> data_to_cache) {
        if (capacity_ == 0) return;
        std::lock_guard<std::mutex> lock(cache_mutex_);
        auto data_ptr = std::make_shared<const std::vector<CppScreenTriangle>>(std::move(data_to_cache));
        auto it = items_map_.find(key);
        if (it != items_map_.end()) {
            lru_list_.erase(it->second.lru_iterator);
            it->second.data_ptr = data_ptr;
            lru_list_.push_front(key);
            it->second.lru_iterator = lru_list_.begin();
        } else {
            if (items_map_.size() >= capacity_) { evict_oldest_nolock(); }
            lru_list_.push_front(key);
            items_map_.emplace(key, CacheEntryL1{data_ptr, lru_list_.begin()});
        }
    }
private:
    struct CacheEntryL1 {
        std::shared_ptr<const std::vector<CppScreenTriangle>> data_ptr;
        std::list<CacheKeyL1>::iterator lru_iterator;
    };
    void evict_oldest_nolock() {
        if (lru_list_.empty()) return;
        CacheKeyL1 oldest_key = lru_list_.back();
        lru_list_.pop_back();
        items_map_.erase(oldest_key);
    }
    size_t capacity_;
    std::list<CacheKeyL1> lru_list_;
    std::unordered_map<CacheKeyL1, CacheEntryL1> items_map_;
    mutable std::mutex cache_mutex_;
};
static LruCacheL1Internal global_l1_cache_cpp_instance;

// --- Global Frame Data & Parameters ---
static std::vector<CppScreenTriangle> global_frame_triangles_cpp_;
static std::mutex global_frame_triangles_mutex_; 
static glm::mat4 g_current_view_matrix_cpp;
static glm::mat4 g_current_projection_matrix_cpp;
static glm::vec3 g_current_camera_pos_w_cpp;
static bool g_current_light_enabled_flag;
static bool g_current_back_cull_enabled_flag;
static bool g_current_clipping_enabled_flag; 
static bool g_current_debug_clipping_enabled_flag;
static std::array<unsigned char, 3> g_current_debug_clipped_color_arr_cpp;
static bool g_current_sort_triangles_in_cpp_flag; 
static float g_current_small_triangle_area_threshold;

// --- Core Rendering Helper Functions ---
glm::vec3 calculate_triangle_normal_internal_cpp(const glm::vec3& v0, const glm::vec3& v1, const glm::vec3& v2) {
    glm::vec3 edge1 = v1 - v0; 
    glm::vec3 edge2 = v2 - v0;
    glm::vec3 normal = glm::cross(edge1, edge2);
    float length_squared = glm::dot(normal, normal);
    if (length_squared < 1e-18f) { 
        return glm::vec3(0.0f, 0.0f, 1.0f); 
    }
    return normal / std::sqrt(length_squared);
}

bool is_front_facing_internal_cpp(const glm::vec3& normal_w, const glm::vec3& camera_pos_w, const glm::vec3& triangle_center_w) {
    glm::vec3 vec_to_camera = camera_pos_w - triangle_center_w;
    if (glm::length2(vec_to_camera) < 1e-12f) { 
        return true; 
    }
    return glm::dot(normal_w, vec_to_camera) > 1e-6f; 
}

float get_intersection_param_internal_cpp(const glm::vec4& v_start_pos_c, const glm::vec4& v_end_pos_c, const glm::vec4& plane_coeffs) {
    float dist_start = glm::dot(plane_coeffs, v_start_pos_c); 
    float dist_end = glm::dot(plane_coeffs, v_end_pos_c);
    if (std::abs(dist_start - dist_end) < 1e-9f) { 
        return -1.0f; 
    }
    return dist_start / (dist_start - dist_end); 
}

std::vector<CppClipVertex> clip_polygon_to_plane_internal_cpp(const std::vector<CppClipVertex>& polygon_in, const glm::vec4& plane_coeffs) {
    std::vector<CppClipVertex> polygon_out; 
    size_t num_vertices = polygon_in.size();
    if (num_vertices == 0) return polygon_out;
    polygon_out.reserve(num_vertices + 1); 

    for (size_t i = 0; i < num_vertices; ++i) {
        const CppClipVertex& current_v = polygon_in[i];
        const CppClipVertex& prev_v = polygon_in[(i + num_vertices - 1) % num_vertices]; 
        float dist_current = glm::dot(plane_coeffs, current_v.position_clip);
        float dist_prev = glm::dot(plane_coeffs, prev_v.position_clip);
        bool current_is_inside = dist_current >= -1e-7f; 
        bool prev_is_inside = dist_prev >= -1e-7f;

        if (current_is_inside) {
            if (!prev_is_inside) { 
                float t = get_intersection_param_internal_cpp(prev_v.position_clip, current_v.position_clip, plane_coeffs);
                if (t >= 0.0f && t <= 1.0f) { 
                    polygon_out.emplace_back(
                        glm::mix(prev_v.position_clip, current_v.position_clip, t),
                        glm::mix(prev_v.color_f, current_v.color_f, t),
                        glm::mix(prev_v.view_z, current_v.view_z, t),
                        glm::mix(prev_v.world_pos, current_v.world_pos, t),
                        false 
                    );
                }
            }
            polygon_out.push_back(current_v); 
        } else if (prev_is_inside) { 
            float t = get_intersection_param_internal_cpp(prev_v.position_clip, current_v.position_clip, plane_coeffs);
            if (t >= 0.0f && t <= 1.0f) { 
                 polygon_out.emplace_back(
                    glm::mix(prev_v.position_clip, current_v.position_clip, t),
                    glm::mix(prev_v.color_f, current_v.color_f, t),
                    glm::mix(prev_v.view_z, current_v.view_z, t),
                    glm::mix(prev_v.world_pos, current_v.world_pos, t),
                    false
                );
            }
        }
    }
    return polygon_out;
}

std::vector<std::vector<CppClipVertex>> clip_triangle_to_frustum_internal_cpp(
    const std::vector<CppClipVertex>& triangle_clip_vertices_in, 
    const std::vector<glm::vec4>& frustum_planes_coeffs
) {
    std::vector<std::vector<CppClipVertex>> final_triangulated_polygons;
    if (triangle_clip_vertices_in.size() != 3) return final_triangulated_polygons; 
    std::vector<CppClipVertex> polygon_to_clip = triangle_clip_vertices_in;
    for (const auto& plane : frustum_planes_coeffs) {
        polygon_to_clip = clip_polygon_to_plane_internal_cpp(polygon_to_clip, plane);
        if (polygon_to_clip.size() < 3) { 
            return final_triangulated_polygons; 
        }
    }
    if (polygon_to_clip.size() >= 3) {
        const CppClipVertex& anchor_vertex = polygon_to_clip[0];
        for (size_t i = 1; i < polygon_to_clip.size() - 1; ++i) {
            final_triangulated_polygons.push_back({anchor_vertex, polygon_to_clip[i], polygon_to_clip[i + 1]});
        }
    }
    return final_triangulated_polygons;
}

bool is_triangle_too_small_on_screen(const CppScreenTriangle& tri, float min_area_threshold) {
    float x1 = tri.screen_coords[0][0]; float y1 = tri.screen_coords[0][1];
    float x2 = tri.screen_coords[1][0]; float y2 = tri.screen_coords[1][1];
    float x3 = tri.screen_coords[2][0]; float y3 = tri.screen_coords[2][1];
    float area_doubled = x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2);
    return std::abs(area_doubled) * 0.5f < min_area_threshold;
}

// --- Stage 1: Local to World Transformation ---
CppWorldDataL2 transform_to_world_internal_cpp(
    const float* local_vertices_raw_ptr,
    py::ssize_t num_total_floats_local,
    int vertex_data_stride,
    bool use_vertex_normals_from_mesh,
    const glm::mat4& model_m
) {
    CppWorldDataL2 world_data_out;
    if (num_total_floats_local == 0) return world_data_out;
    if (vertex_data_stride <= 0 || (num_total_floats_local % (static_cast<py::ssize_t>(vertex_data_stride) * 3)) != 0) {
         throw std::runtime_error("C++ (transform_to_world): Vertex data/stride mismatch.");
    }
    const long num_source_triangles_long = static_cast<long>(num_total_floats_local / (static_cast<py::ssize_t>(vertex_data_stride) * 3));
    if (num_source_triangles_long <= 0) return world_data_out;
    world_data_out.num_source_triangles = static_cast<size_t>(num_source_triangles_long);
    const glm::mat3 normal_model_m = glm::mat3(glm::transpose(glm::inverse(model_m)));
    world_data_out.world_vertices_flat.resize(world_data_out.num_source_triangles * 9);
    world_data_out.world_face_normals_flat.resize(world_data_out.num_source_triangles * 3);
    world_data_out.vertex_colors_flat.resize(world_data_out.num_source_triangles * 9);

#ifdef _MSC_VER
    _Pragma("omp parallel for schedule(dynamic, 8)")
#else
    #pragma omp parallel for schedule(dynamic, 8)
#endif
    for (long i_tri = 0; i_tri < num_source_triangles_long; ++i_tri) {
        const float* tri_base_ptr = local_vertices_raw_ptr + i_tri * vertex_data_stride * 3;
        glm::vec3 local_v[3], model_n[3], v_colors[3];
        bool current_triangle_has_vertex_normals = false;
        size_t base_idx_vertices = static_cast<size_t>(i_tri) * 9;
        size_t base_idx_normals = static_cast<size_t>(i_tri) * 3;

        for (int k = 0; k < 3; ++k) {
            const float* v_ptr = tri_base_ptr + k * vertex_data_stride;
            local_v[k] = glm::vec3(v_ptr[0], v_ptr[1], v_ptr[2]);
            if (vertex_data_stride >= 6) {
                v_colors[k] = glm::vec3(v_ptr[3], v_ptr[4], v_ptr[5]);
            } else {
                v_colors[k] = glm::vec3(0.5f, 0.5f, 0.5f); // Default color
            }
            if (use_vertex_normals_from_mesh && vertex_data_stride >= 9) {
                model_n[k] = glm::vec3(v_ptr[6], v_ptr[7], v_ptr[8]);
                current_triangle_has_vertex_normals = true;
            }
            world_data_out.vertex_colors_flat[base_idx_vertices + k*3 + 0] = v_colors[k].r;
            world_data_out.vertex_colors_flat[base_idx_vertices + k*3 + 1] = v_colors[k].g;
            world_data_out.vertex_colors_flat[base_idx_vertices + k*3 + 2] = v_colors[k].b;
        }
        glm::vec3 world_v[3];
        world_v[0] = glm::vec3(model_m * glm::vec4(local_v[0], 1.0f));
        world_v[1] = glm::vec3(model_m * glm::vec4(local_v[1], 1.0f));
        world_v[2] = glm::vec3(model_m * glm::vec4(local_v[2], 1.0f));
        for(int k=0; k<3; ++k) {
            world_data_out.world_vertices_flat[base_idx_vertices + k*3 + 0] = world_v[k].x;
            world_data_out.world_vertices_flat[base_idx_vertices + k*3 + 1] = world_v[k].y;
            world_data_out.world_vertices_flat[base_idx_vertices + k*3 + 2] = world_v[k].z;
        }
        glm::vec3 face_normal_w;
        if (current_triangle_has_vertex_normals) {
            glm::vec3 n0w = glm::normalize(normal_model_m * model_n[0]);
            glm::vec3 n1w = glm::normalize(normal_model_m * model_n[1]);
            glm::vec3 n2w = glm::normalize(normal_model_m * model_n[2]);
            face_normal_w = glm::normalize(n0w + n1w + n2w); // Average of transformed vertex normals
        } else {
            face_normal_w = calculate_triangle_normal_internal_cpp(world_v[0], world_v[1], world_v[2]);
        }
        world_data_out.world_face_normals_flat[base_idx_normals + 0] = face_normal_w.x;
        world_data_out.world_face_normals_flat[base_idx_normals + 1] = face_normal_w.y;
        world_data_out.world_face_normals_flat[base_idx_normals + 2] = face_normal_w.z;
    }
    return world_data_out;
}

// --- Stage 2: World to Screen Transformation ---
std::vector<CppScreenTriangle> process_world_to_screen_internal_cpp(
    const CppWorldDataL2& world_data
) {
    if (world_data.num_source_triangles == 0) return {};

    const float* world_verts_ptr = world_data.world_vertices_flat.data();
    const float* world_normals_ptr = world_data.world_face_normals_flat.data();
    const float* vert_colors_ptr = world_data.vertex_colors_flat.data();

    const std::vector<glm::vec4> frustum_planes_static = {
        glm::vec4(1.f, 0.f, 0.f, 1.f), glm::vec4(-1.f,0.f, 0.f, 1.f), // Left, Right
        glm::vec4(0.f, 1.f, 0.f, 1.f), glm::vec4(0.f,-1.f, 0.f, 1.f), // Bottom, Top
        glm::vec4(0.f, 0.f, 1.f, 1.f), glm::vec4(0.f, 0.f,-1.f, 1.f)  // Near, Far (for -w to w range)
    };

    std::vector<std::vector<CppScreenTriangle>> per_thread_results;
    int num_threads_to_use = 1;
    #ifdef _OPENMP
        num_threads_to_use = omp_get_max_threads();
        if (num_threads_to_use <= 0) num_threads_to_use = 1;
    #endif
    per_thread_results.resize(num_threads_to_use);
    for(auto& list : per_thread_results) {
        if (world_data.num_source_triangles > 0 && num_threads_to_use > 0) {
             list.reserve(world_data.num_source_triangles / num_threads_to_use + 32); // Heuristic
        } else if (world_data.num_source_triangles > 0) {
            list.reserve(world_data.num_source_triangles + 32);
        }
    }

#ifdef _MSC_VER
    _Pragma("omp parallel for schedule(dynamic, 8)")
#else
    #pragma omp parallel for schedule(dynamic, 8)
#endif
    for (long i_tri_long = 0; i_tri_long < static_cast<long>(world_data.num_source_triangles); ++i_tri_long) {
        size_t i_tri = static_cast<size_t>(i_tri_long);
        int current_thread_id = 0;
        #ifdef _OPENMP
            current_thread_id = omp_get_thread_num();
        #endif

        glm::vec3 current_world_v[3]; glm::vec3 current_v_colors[3];
        for(int k=0; k<3; ++k){
            current_world_v[k] = glm::vec3(world_verts_ptr[i_tri*9 + k*3 + 0], world_verts_ptr[i_tri*9 + k*3 + 1], world_verts_ptr[i_tri*9 + k*3 + 2]);
            current_v_colors[k] = glm::vec3(vert_colors_ptr[i_tri*9 + k*3 + 0], vert_colors_ptr[i_tri*9 + k*3 + 1], vert_colors_ptr[i_tri*9 + k*3 + 2]);
        }
        glm::vec3 current_world_face_normal(world_normals_ptr[i_tri*3 + 0], world_normals_ptr[i_tri*3 + 1], world_normals_ptr[i_tri*3 + 2]);

        if (g_current_back_cull_enabled_flag) {
            glm::vec3 triangle_center_w = (current_world_v[0] + current_world_v[1] + current_world_v[2]) / 3.0f;
            if (!is_front_facing_internal_cpp(current_world_face_normal, g_current_camera_pos_w_cpp, triangle_center_w)) {
                continue; 
            }
        }

        std::vector<CppClipVertex> clip_space_input_triangle; clip_space_input_triangle.reserve(3);
        for (int i_vtx = 0; i_vtx < 3; ++i_vtx) {
            glm::vec4 view_space_pos_h = g_current_view_matrix_cpp * glm::vec4(current_world_v[i_vtx], 1.0f);
            glm::vec4 clip_space_pos_h = g_current_projection_matrix_cpp * view_space_pos_h;
            clip_space_input_triangle.emplace_back(clip_space_pos_h, current_v_colors[i_vtx], view_space_pos_h.z, current_world_v[i_vtx], true);
        }
        
        std::vector<std::vector<CppClipVertex>> processed_triangles_after_clipping;
        if (g_current_clipping_enabled_flag) {
            processed_triangles_after_clipping = clip_triangle_to_frustum_internal_cpp(clip_space_input_triangle, frustum_planes_static);
        } else {
            processed_triangles_after_clipping.push_back(clip_space_input_triangle);
        }

        for (const auto& single_clipped_triangle_verts_cpp : processed_triangles_after_clipping) {
            if (single_clipped_triangle_verts_cpp.size() != 3) continue; 
            CppScreenTriangle final_screen_triangle; 
            bool is_triangle_valid_for_draw = true; 
            bool was_modified_by_clipping_debug = false;
            final_screen_triangle.depth = 0.0f; 
            glm::vec3 accumulated_interpolated_color_float(0.0f);

            for (int i_final_vtx = 0; i_final_vtx < 3; ++i_final_vtx) {
                const CppClipVertex& current_clip_vertex = single_clipped_triangle_verts_cpp[i_final_vtx];
                if (g_current_debug_clipping_enabled_flag && !current_clip_vertex.is_original) {
                    was_modified_by_clipping_debug = true;
                }
                const glm::vec4& clip_space_pos = current_clip_vertex.position_clip;
                if (std::abs(clip_space_pos.w) < 1e-7f) { // Check for near-zero w
                    is_triangle_valid_for_draw = false; break; 
                }
                float inv_w = 1.0f / clip_space_pos.w; 
                float ndc_x = clip_space_pos.x * inv_w; 
                float ndc_y = clip_space_pos.y * inv_w;
                // float ndc_z = clip_space_pos.z * inv_w; // For Z-buffer if needed
                
                final_screen_triangle.screen_coords[i_final_vtx][0] = (ndc_x + 1.0f) * 0.5f * static_cast<float>(g_window_width_cpp);
                final_screen_triangle.screen_coords[i_final_vtx][1] = (1.0f - ndc_y) * 0.5f * static_cast<float>(g_window_height_cpp); 
                
                final_screen_triangle.depth += current_clip_vertex.view_z; 
                accumulated_interpolated_color_float += current_clip_vertex.color_f;
            }

            if (!is_triangle_valid_for_draw) continue;
            final_screen_triangle.depth /= 3.0f; 

            if (g_current_small_triangle_area_threshold > 0.0f) {
                if (is_triangle_too_small_on_screen(final_screen_triangle, g_current_small_triangle_area_threshold)) {
                    continue;
                }
            }

            glm::vec3 average_final_color_float = accumulated_interpolated_color_float / 3.0f; 
            float light_intensity = 1.0f;
            if (g_current_light_enabled_flag) {
                glm::vec3 triangle_center_w = (current_world_v[0] + current_world_v[1] + current_world_v[2]) / 3.0f;
                glm::vec3 light_dir = g_current_camera_pos_w_cpp - triangle_center_w;
                if (glm::length2(light_dir) > 1e-9f) {
                    light_dir = glm::normalize(light_dir);
                    light_intensity = glm::max(0.0f, glm::dot(current_world_face_normal, light_dir));
                    light_intensity = 0.3f + 0.7f * light_intensity; // Ambient + Diffuse
                }
            }

            if (g_current_debug_clipping_enabled_flag && was_modified_by_clipping_debug) {
                final_screen_triangle.color_final_uint8 = g_current_debug_clipped_color_arr_cpp;
            } else {
                final_screen_triangle.color_final_uint8[0] = static_cast<unsigned char>(std::clamp(average_final_color_float.r * light_intensity * 255.0f, 0.0f, 255.0f));
                final_screen_triangle.color_final_uint8[1] = static_cast<unsigned char>(std::clamp(average_final_color_float.g * light_intensity * 255.0f, 0.0f, 255.0f));
                final_screen_triangle.color_final_uint8[2] = static_cast<unsigned char>(std::clamp(average_final_color_float.b * light_intensity * 255.0f, 0.0f, 255.0f));
            }
            
            // Safely add to per_thread_results
            if (current_thread_id >= 0 && static_cast<size_t>(current_thread_id) < per_thread_results.size()) {
                 per_thread_results[static_cast<size_t>(current_thread_id)].push_back(final_screen_triangle);
            } else { 
                // Fallback for safety, though should not happen with correct omp_get_thread_num usage
                #pragma omp critical
                { 
                  if (per_thread_results.empty()) per_thread_results.resize(1); // Should not be empty
                  size_t safe_thread_id = (current_thread_id >= 0 && static_cast<size_t>(current_thread_id) < per_thread_results.size()) ? static_cast<size_t>(current_thread_id) : 0;
                  per_thread_results[safe_thread_id].push_back(final_screen_triangle);
                }
            }
        }
    } 

    std::vector<CppScreenTriangle> final_combined_output_list;
    size_t total_triangles_estimate = 0;
    for (const auto& thread_list : per_thread_results) { total_triangles_estimate += thread_list.size(); }
    final_combined_output_list.reserve(total_triangles_estimate);
    for (const auto& thread_list : per_thread_results) {
        final_combined_output_list.insert(final_combined_output_list.end(), thread_list.begin(), thread_list.end());
    }
    
    return final_combined_output_list;
}

// --- Pybind11 Exposed Functions ---

// Helper to convert SDL_WindowEvent ID to string (optional, for debugging)
const char* GetSDLEventWindowTypeString(Uint8 event_type) {
    switch (event_type) {
        case SDL_WINDOWEVENT_SHOWN: return "SHOWN";
        case SDL_WINDOWEVENT_HIDDEN: return "HIDDEN";
        case SDL_WINDOWEVENT_EXPOSED: return "EXPOSED";
        case SDL_WINDOWEVENT_MOVED: return "MOVED";
        case SDL_WINDOWEVENT_RESIZED: return "RESIZED";
        case SDL_WINDOWEVENT_SIZE_CHANGED: return "SIZE_CHANGED";
        case SDL_WINDOWEVENT_MINIMIZED: return "MINIMIZED";
        case SDL_WINDOWEVENT_MAXIMIZED: return "MAXIMIZED";
        case SDL_WINDOWEVENT_RESTORED: return "RESTORED";
        case SDL_WINDOWEVENT_ENTER: return "ENTER";
        case SDL_WINDOWEVENT_LEAVE: return "LEAVE";
        case SDL_WINDOWEVENT_FOCUS_GAINED: return "FOCUS_GAINED";
        case SDL_WINDOWEVENT_FOCUS_LOST: return "FOCUS_LOST";
        case SDL_WINDOWEVENT_CLOSE: return "CLOSE";
        case SDL_WINDOWEVENT_TAKE_FOCUS: return "TAKE_FOCUS";
        case SDL_WINDOWEVENT_HIT_TEST: return "HIT_TEST";
        default: return "UNKNOWN_WINDOW_EVENT";
    }
}


py::tuple initialize_cpp_renderer(int initial_width, int initial_height, bool fullscreen_flag,
                                  const std::string& window_title,
                                  size_t l1_capacity, size_t l2_capacity,
                                  std::array<unsigned char, 3> bg_color) {
    std::lock_guard<std::mutex> lock(g_sdl_resources_mutex); 

    if (g_sdl_renderer || g_sdl_native_window) {
         throw std::runtime_error("C++ Renderer: Already initialized. Call cleanup_cpp_renderer first.");
    }
    
    // SDL_Init() initializes all subsystems if called with 0.
    // SDL_InitSubSystem(SDL_INIT_VIDEO) is fine too.
    // Pygame.init() might have already called SDL_Init().
    // We check if VIDEO is initialized. If not, we initialize it.
    if (!SDL_WasInit(SDL_INIT_VIDEO)) {
        if (SDL_InitSubSystem(SDL_INIT_VIDEO) < 0) {
            throw std::runtime_error(std::string("C++ (SDL_InitSubSystem(VIDEO)) failed: ") + SDL_GetError());
        }
        g_sdl_subsystems_initialized_by_cpp = true; // We initialized it.
         py::print("C++: SDL_INIT_VIDEO initialized by cpp_renderer_core.");
    } else {
        g_sdl_subsystems_initialized_by_cpp = false; // Already initialized (likely by Pygame)
         py::print("C++: SDL_INIT_VIDEO was already initialized.");
    }

    // Initialize SDL_ttf
    if (TTF_Init() == -1) {
        py::print(std::string("C++ CRITICAL: TTF_Init() failed: ") + TTF_GetError());
        // This is more critical now, as UI might be unusable. Consider throwing.
    } else {
        // Pre-load default font into cache.
        // get_font() will handle caching and error messages.
        TTF_Font* default_cached_font = get_font(DEFAULT_UI_FONT_SIZE);
        if (!default_cached_font) {
            py::print(std::string("C++ Warning: Failed to load and cache the default UI font (") + FONT_FILE_PATH + std::string(", size ") + std::to_string(DEFAULT_UI_FONT_SIZE) + std::string("). Text rendering might fail."));
        } else {
             py::print(std::string("C++: Default UI font (size ") + std::to_string(DEFAULT_UI_FONT_SIZE) + std::string(") loaded and cached."));
        }
    }


    Uint32 window_flags = SDL_WINDOW_OPENGL | SDL_WINDOW_ALLOW_HIGHDPI; // OpenGL flag might be needed for some SDL_Renderer backends
                                                                      // even if we don't use OpenGL directly for drawing primitives.
                                                                      // Or SDL_WINDOW_SHOWN.
    if (fullscreen_flag) {
        // Using SDL_WINDOW_FULLSCREEN_DESKTOP is often preferred for "true" fullscreen
        // that uses the current desktop resolution.
        // SDL_WINDOW_FULLSCREEN would try to change the resolution.
        window_flags |= SDL_WINDOW_FULLSCREEN_DESKTOP; 
         py::print("C++: Fullscreen requested (SDL_WINDOW_FULLSCREEN_DESKTOP).");
    }

    g_sdl_native_window = SDL_CreateWindow(
        window_title.c_str(),
        SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED,
        initial_width,
        initial_height,
        window_flags
    );

    if (!g_sdl_native_window) {
        if (g_sdl_subsystems_initialized_by_cpp) SDL_QuitSubSystem(SDL_INIT_VIDEO);
        throw std::runtime_error(std::string("C++ (SDL_CreateWindow) failed: ") + SDL_GetError());
    }
     py::print("C++: SDL_Window created.");

    // Get actual window size after creation, especially if fullscreen_desktop was used
    SDL_GetWindowSize(g_sdl_native_window, &g_window_width_cpp, &g_window_height_cpp);
     py::print("C++: Actual window size after creation: ", g_window_width_cpp, "x", g_window_height_cpp);


    Uint32 renderer_flags = SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC;
    g_sdl_renderer = SDL_CreateRenderer(g_sdl_native_window, -1, renderer_flags);
    if (!g_sdl_renderer) { 
        py::print("C++: VSync renderer creation failed, trying without VSync. Error: ", SDL_GetError());
        renderer_flags = SDL_RENDERER_ACCELERATED;
        g_sdl_renderer = SDL_CreateRenderer(g_sdl_native_window, -1, renderer_flags);
    }
    if (!g_sdl_renderer) { 
        py::print("C++: Accelerated renderer creation failed, trying software. Error: ", SDL_GetError());
        renderer_flags = SDL_RENDERER_SOFTWARE;
        g_sdl_renderer = SDL_CreateRenderer(g_sdl_native_window, -1, renderer_flags);
    }

    if (!g_sdl_renderer) {
        SDL_DestroyWindow(g_sdl_native_window);
        g_sdl_native_window = nullptr;
        if (g_sdl_subsystems_initialized_by_cpp) SDL_QuitSubSystem(SDL_INIT_VIDEO);
        throw std::runtime_error(std::string("C++ (SDL_CreateRenderer) failed for all types: ") + SDL_GetError());
    }
    py::print("C++: SDL_Renderer created successfully.");
    SDL_RendererInfo info;
    SDL_GetRendererInfo(g_sdl_renderer, &info);
    py::print("C++: Renderer name: ", info.name);


    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "0"); // Nearest pixel sampling

    g_background_color_cpp = bg_color;

    global_l1_cache_cpp_instance.set_capacity(l1_capacity);
    global_l2_cache_cpp_instance.set_capacity(l2_capacity);
    py::print("C++: Caches configured.");

    return py::make_tuple(g_window_width_cpp, g_window_height_cpp);
}

void cleanup_cpp_renderer() {
    std::lock_guard<std::mutex> lock(g_sdl_resources_mutex);
    py::print("C++: cleanup_cpp_renderer called.");
    global_l1_cache_cpp_instance.clear();
    global_l2_cache_cpp_instance.clear();
    
    { // Clear UI elements
        std::lock_guard<std::mutex> ui_lock(g_ui_elements_mutex);
        g_cpp_buttons.clear();
        g_cpp_texts.clear();
        py::print("C++: UI elements cleared.");
    }

    { 
        std::lock_guard<std::mutex> frame_lock(global_frame_triangles_mutex_);
        global_frame_triangles_cpp_.clear();
        global_frame_triangles_cpp_.shrink_to_fit();
    }

    if (g_sdl_renderer) {
        SDL_DestroyRenderer(g_sdl_renderer);
        g_sdl_renderer = nullptr;
        py::print("C++: SDL_Renderer destroyed.");
    }
    if (g_sdl_native_window) {
        SDL_DestroyWindow(g_sdl_native_window); 
        g_sdl_native_window = nullptr;
        py::print("C++: SDL_Window destroyed.");
    }

    if (g_sdl_subsystems_initialized_by_cpp) {
        if (SDL_WasInit(SDL_INIT_VIDEO)) { // Check if it's still initialized
            SDL_QuitSubSystem(SDL_INIT_VIDEO);
            py::print("C++: SDL_INIT_VIDEO SubSystem quit by cpp_renderer_core.");
        }
        // SDL_Quit(); // Only call SDL_Quit if this module called SDL_Init() for everything.
                   // If Pygame called SDL_Init(0), Pygame should call SDL_Quit().
                   // It's safer to just quit the subsystems we explicitly started.
    }

    // Cleanup SDL_ttf and font cache
    {
        std::lock_guard<std::mutex> lock(g_font_cache_mutex);
        for (auto const& [size, font_ptr] : g_font_cache) {
            if (font_ptr) {
                TTF_CloseFont(font_ptr);
            }
        }
        g_font_cache.clear();
        py::print("C++: Font cache cleared and fonts closed.");
    }

    if (TTF_WasInit()) { // Only quit if it was initialized
        TTF_Quit();
        py::print("C++: SDL_ttf quit.");
    }
    
    py::print("C++: Cleanup finished.");
}

// Хэшер для glm::mat4
struct GlmMat4Hash {
    std::size_t operator()(const glm::mat4& m) const {
        std::size_t seed = 0;
        const float* p = glm::value_ptr(m);
        for (size_t i = 0; i < 16; ++i) { 
            seed ^= std::hash<float>{}(p[i]) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
        }
        return seed;
    }
};

void set_frame_parameters_cpp(
    py::array_t<float, py::array::c_style | py::array::forcecast> view_matrix_np,
    py::array_t<float, py::array::c_style | py::array::forcecast> projection_matrix_np,
    py::array_t<float, py::array::c_style | py::array::forcecast> camera_pos_w_np,
    bool light_enabled_flag, bool back_cull_enabled_flag, bool clipping_enabled_flag,
    bool debug_clipping_enabled_flag, std::array<unsigned char, 3> debug_clipped_color_arr,
    bool sort_triangles_flag, float small_triangle_area_threshold
) {
    if (!g_sdl_renderer && !g_sdl_native_window) { 
        // py::print("C++ set_frame_params: Renderer not initialized!"); // Too noisy
        return; 
    }

    if (view_matrix_np.ndim() != 1 || view_matrix_np.size() != 16) throw std::runtime_error("View matrix must be a flat array of 16 floats.");
    if (projection_matrix_np.ndim() != 1 || projection_matrix_np.size() != 16) throw std::runtime_error("Projection matrix must be a flat array of 16 floats.");
    if (camera_pos_w_np.ndim() != 1 || camera_pos_w_np.size() != 3) throw std::runtime_error("Camera position must be a flat array of 3 floats.");

    g_current_view_matrix_cpp = glm::make_mat4(view_matrix_np.data());
    g_current_projection_matrix_cpp = glm::make_mat4(projection_matrix_np.data());
    g_current_camera_pos_w_cpp = glm::make_vec3(camera_pos_w_np.data());
    g_current_light_enabled_flag = light_enabled_flag;
    g_current_back_cull_enabled_flag = back_cull_enabled_flag;
    g_current_clipping_enabled_flag = clipping_enabled_flag;
    g_current_debug_clipping_enabled_flag = debug_clipping_enabled_flag;
    g_current_debug_clipped_color_arr_cpp = debug_clipped_color_arr;
    g_current_sort_triangles_in_cpp_flag = sort_triangles_flag;
    g_current_small_triangle_area_threshold = small_triangle_area_threshold;

    {
        std::lock_guard<std::mutex> lock(global_frame_triangles_mutex_);
        global_frame_triangles_cpp_.clear(); 
    }
}

void process_and_accumulate_object_cpp(
    uintptr_t object_id_py,
    py::array_t<float, py::array::c_style | py::array::forcecast> transform_params_np, 
    py::array_t<float, py::array::c_style | py::array::forcecast> local_vertex_data_np,
    int vertex_data_stride,
    bool use_vertex_normals_from_mesh
) {
    if (!g_sdl_renderer && !g_sdl_native_window) return; 
    if (local_vertex_data_np.size() == 0) return;
    if (transform_params_np.ndim() != 1 || transform_params_np.size() != 9) {
         throw std::runtime_error("C++ (process_object): transform_params_np must be a flat array of 9 floats.");
    }
    const float* tp_ptr = transform_params_np.data();

    CacheKeyL1 key_l1;
    key_l1.object_id = object_id_py;
    for (int i = 0; i < 9; ++i) key_l1.transform_params_hash_relevant[i] = tp_ptr[i];
    key_l1.view_matrix_hash = GlmMat4Hash{}(g_current_view_matrix_cpp);
    key_l1.projection_matrix_hash = GlmMat4Hash{}(g_current_projection_matrix_cpp);
    key_l1.light_enabled = g_current_light_enabled_flag;
    key_l1.back_cull_enabled = g_current_back_cull_enabled_flag;
    key_l1.clipping_enabled = g_current_clipping_enabled_flag;
    key_l1.debug_clipping_enabled = g_current_debug_clipping_enabled_flag;
    key_l1.debug_clipped_color = g_current_debug_clipped_color_arr_cpp;
    key_l1.small_tri_area_threshold = g_current_small_triangle_area_threshold;

    std::shared_ptr<const std::vector<CppScreenTriangle>> screen_triangles_from_l1 = global_l1_cache_cpp_instance.get(key_l1);

    if (screen_triangles_from_l1) {
        std::lock_guard<std::mutex> lock(global_frame_triangles_mutex_);
        global_frame_triangles_cpp_.insert(global_frame_triangles_cpp_.end(), screen_triangles_from_l1->begin(), screen_triangles_from_l1->end());
        return;
    }

    CacheKeyL2 key_l2;
    key_l2.object_id = object_id_py;
    key_l2.use_vertex_normals_config = use_vertex_normals_from_mesh;
    for (int i = 0; i < 9; ++i) key_l2.transform_params_hash_relevant[i] = tp_ptr[i];

    std::shared_ptr<const CppWorldDataL2> world_data_from_cache_l2 = global_l2_cache_cpp_instance.get(key_l2);
    std::vector<CppScreenTriangle> new_screen_triangles_for_l1;

    if (world_data_from_cache_l2) {
        new_screen_triangles_for_l1 = process_world_to_screen_internal_cpp(*world_data_from_cache_l2);
    } else {
        glm::vec3 pos(tp_ptr[0], tp_ptr[1], tp_ptr[2]);
        glm::vec3 rot_deg(tp_ptr[3], tp_ptr[4], tp_ptr[5]);
        glm::vec3 scl(tp_ptr[6], tp_ptr[7], tp_ptr[8]);
        glm::mat4 model_m_calculated = glm::translate(glm::mat4(1.0f), pos);
        model_m_calculated = glm::rotate(model_m_calculated, glm::radians(rot_deg.y), glm::vec3(0,1,0)); 
        model_m_calculated = glm::rotate(model_m_calculated, glm::radians(rot_deg.x), glm::vec3(1,0,0)); 
        model_m_calculated = glm::rotate(model_m_calculated, glm::radians(rot_deg.z), glm::vec3(0,0,1)); 
        model_m_calculated = glm::scale(model_m_calculated, scl);

        CppWorldDataL2 new_world_data_l2 = transform_to_world_internal_cpp(
            local_vertex_data_np.data(), local_vertex_data_np.size(),
            vertex_data_stride, use_vertex_normals_from_mesh, model_m_calculated
        );

        if (new_world_data_l2.num_source_triangles > 0) {
            // Move new_world_data_l2 into the cache, then get a shared_ptr to it
            // to avoid copying the potentially large data.
            auto shared_new_world_data = std::make_shared<CppWorldDataL2>(std::move(new_world_data_l2));
            global_l2_cache_cpp_instance.put(key_l2, *shared_new_world_data); // put might make its own shared_ptr or copy, check impl.
                                                                              // My LruCacheL2Internal::put takes by value, then moves.
                                                                              // So, it should be efficient.
            new_screen_triangles_for_l1 = process_world_to_screen_internal_cpp(*shared_new_world_data);
        }
    }

    if (!new_screen_triangles_for_l1.empty()) {
        global_l1_cache_cpp_instance.put(key_l1, new_screen_triangles_for_l1); 
        std::lock_guard<std::mutex> lock(global_frame_triangles_mutex_);
        global_frame_triangles_cpp_.insert(global_frame_triangles_cpp_.end(), new_screen_triangles_for_l1.begin(), new_screen_triangles_for_l1.end());
    }
}

void render_accumulated_triangles_cpp() {
    if (!g_sdl_renderer) return; 
    
    std::vector<CppScreenTriangle> triangles_to_render_this_frame; 
    { 
        std::lock_guard<std::mutex> frame_lock(global_frame_triangles_mutex_);
        if (!global_frame_triangles_cpp_.empty()) {
            triangles_to_render_this_frame.swap(global_frame_triangles_cpp_); // Efficiently move data
        }
        // global_frame_triangles_cpp_ is now empty or contains previous frame's (if swap wasn't needed)
        // but it's cleared in set_frame_parameters_cpp anyway.
    }

    SDL_SetRenderDrawColor(g_sdl_renderer, g_background_color_cpp[0], g_background_color_cpp[1], g_background_color_cpp[2], SDL_ALPHA_OPAQUE);
    SDL_RenderClear(g_sdl_renderer);

    if (triangles_to_render_this_frame.empty()) {
        SDL_RenderPresent(g_sdl_renderer); 
        return;
    }

    if (g_current_sort_triangles_in_cpp_flag) {
        #if __cplusplus >= 201703L && defined(__cpp_lib_parallel_algorithm) && !defined(_MSC_VER) && defined(USE_CPP_PARALLEL_SORT) // Add a define to control this
        try {
            std::sort(std::execution::par, triangles_to_render_this_frame.begin(), triangles_to_render_this_frame.end(),
                [](const CppScreenTriangle& a, const CppScreenTriangle& b) { return a.depth < b.depth; });
        } catch (const std::exception& e) { 
             // std::cerr << "Parallel sort failed: " << e.what() << ", falling back to sequential." << std::endl;
             std::sort(triangles_to_render_this_frame.begin(), triangles_to_render_this_frame.end(),
                [](const CppScreenTriangle& a, const CppScreenTriangle& b) { return a.depth < b.depth; });
        }
        #else
        std::sort(triangles_to_render_this_frame.begin(), triangles_to_render_this_frame.end(),
                  [](const CppScreenTriangle& a, const CppScreenTriangle& b) { return a.depth < b.depth; });
        #endif
    }
    
    std::vector<SDL_Vertex> sdl_vertices;
    sdl_vertices.reserve(triangles_to_render_this_frame.size() * 3); 

    for (const auto& tri : triangles_to_render_this_frame) {
        for (int i = 0; i < 3; ++i) {
            SDL_Vertex vertex;
            vertex.position.x = tri.screen_coords[i][0];
            vertex.position.y = tri.screen_coords[i][1]; 
            vertex.color.r = tri.color_final_uint8[0];
            vertex.color.g = tri.color_final_uint8[1];
            vertex.color.b = tri.color_final_uint8[2];
            vertex.color.a = SDL_ALPHA_OPAQUE; 
            vertex.tex_coord.x = 0.0f; // Not using textures currently
            vertex.tex_coord.y = 0.0f;
            sdl_vertices.push_back(vertex);
        }
    }
    
    if (!sdl_vertices.empty()) {
        int result = SDL_RenderGeometry(g_sdl_renderer, nullptr, sdl_vertices.data(), 
                                        static_cast<int>(sdl_vertices.size()), nullptr, 0);      
        if (result != 0) {
            // std::cerr << "C++ (SDL_RenderGeometry) failed: " << SDL_GetError() << std::endl;
        }
    }
    SDL_RenderPresent(g_sdl_renderer);
}

// --- New Window/Input Control Functions ---
void set_window_title_cpp(const std::string& title) {
    std::lock_guard<std::mutex> lock(g_sdl_resources_mutex);
    if (g_sdl_native_window) {
        SDL_SetWindowTitle(g_sdl_native_window, title.c_str());
    }
}

void set_relative_mouse_mode_cpp(bool active) {
    std::lock_guard<std::mutex> lock(g_sdl_resources_mutex);
    if (SDL_SetRelativeMouseMode(active ? SDL_TRUE : SDL_FALSE) < 0) {
        // std::cerr << "Warning: Could not set relative mouse mode: " << SDL_GetError() << std::endl;
    }
}

void set_mouse_visible_cpp(bool visible) {
    std::lock_guard<std::mutex> lock(g_sdl_resources_mutex);
     // SDL_ShowCursor returns current state if argument is -1, or sets and returns previous.
    if (SDL_ShowCursor(visible ? SDL_ENABLE : SDL_DISABLE) < 0) {
        // std::cerr << "Warning: Could not set mouse visibility: " << SDL_GetError() << std::endl;
    }
}

void set_window_grab_cpp(bool grab_on) {
    std::lock_guard<std::mutex> lock(g_sdl_resources_mutex);
    if (g_sdl_native_window) {
        SDL_SetWindowGrab(g_sdl_native_window, grab_on ? SDL_TRUE : SDL_FALSE);
    }
}

py::list poll_sdl_events_cpp() {
    // No g_sdl_resources_mutex here, SDL_PollEvent is designed to be called from the main thread.
    // SDL_PumpEvents(); // Often called by SDL_PollEvent internally, but can be called explicitly if needed elsewhere.
    
    py::list events_list;
    SDL_Event sdl_event;

    while (SDL_PollEvent(&sdl_event)) {
        py::dict py_event;
        switch (sdl_event.type) {
            case SDL_QUIT:
                py_event["type"] = "QUIT";
                break;
            case SDL_KEYDOWN:
                py_event["type"] = "KEYDOWN";
                py_event["scancode"] = static_cast<int>(sdl_event.key.keysym.scancode); // SDL_Scancode to int
                py_event["key"] = static_cast<int>(sdl_event.key.keysym.sym);           // SDL_Keycode to int
                py_event["mod"] = static_cast<int>(sdl_event.key.keysym.mod);           // SDL_Keymod to int
                py_event["repeat"] = static_cast<int>(sdl_event.key.repeat);           // Uint8 to int for consistency
                break;
            case SDL_KEYUP:
                py_event["type"] = "KEYUP";
                py_event["scancode"] = static_cast<int>(sdl_event.key.keysym.scancode); // SDL_Scancode to int
                py_event["key"] = static_cast<int>(sdl_event.key.keysym.sym);           // SDL_Keycode to int
                py_event["mod"] = static_cast<int>(sdl_event.key.keysym.mod);           // SDL_Keymod to int
                break;
            case SDL_MOUSEMOTION:
                py_event["type"] = "MOUSEMOTION";
                py_event["x"] = sdl_event.motion.x;           // Sint32
                py_event["y"] = sdl_event.motion.y;           // Sint32
                py_event["xrel"] = sdl_event.motion.xrel;     // Sint32
                py_event["yrel"] = sdl_event.motion.yrel;     // Sint32
                py_event["buttons"] = sdl_event.motion.state; // Uint32 (button mask)
                break;
            case SDL_MOUSEBUTTONDOWN:
                py_event["type"] = "MOUSEBUTTONDOWN";
                py_event["button"] = static_cast<int>(sdl_event.button.button); // Uint8 to int
                py_event["x"] = sdl_event.button.x;           // Sint32
                py_event["y"] = sdl_event.button.y;           // Sint32
                py_event["clicks"] = static_cast<int>(sdl_event.button.clicks); // Uint8 to int
                break;
            case SDL_MOUSEBUTTONUP:
                py_event["type"] = "MOUSEBUTTONUP";
                py_event["button"] = static_cast<int>(sdl_event.button.button); // Uint8 to int
                py_event["x"] = sdl_event.button.x;           // Sint32
                py_event["y"] = sdl_event.button.y;           // Sint32
                break;
            case SDL_MOUSEWHEEL:
                py_event["type"] = "MOUSEWHEEL";
                py_event["x"] = sdl_event.wheel.x;             // Sint32
                py_event["y"] = sdl_event.wheel.y;             // Sint32
                py_event["direction"] = static_cast<int>(sdl_event.wheel.direction); // Uint32 to int (SDL_MOUSEWHEEL_NORMAL or SDL_MOUSEWHEEL_FLIPPED)
                break;
            case SDL_WINDOWEVENT:
                py_event["type"] = "WINDOWEVENT";
                py_event["event_type_str"] = GetSDLEventWindowTypeString(sdl_event.window.event); // For debugging
                py_event["event_id"] = static_cast<int>(sdl_event.window.event);       // Uint8 (SDL_WindowEventID) to int
                py_event["data1"] = sdl_event.window.data1;      // Sint32
                py_event["data2"] = sdl_event.window.data2;      // Sint32
                
                // Update global window dimensions if the window size actually changed
                if (sdl_event.window.event == SDL_WINDOWEVENT_SIZE_CHANGED || 
                    sdl_event.window.event == SDL_WINDOWEVENT_RESIZED) {
                    // This lock protects g_window_width_cpp and g_window_height_cpp
                    // as they might be read by the rendering thread (if it were separate,
                    // but here mainly for consistency and future-proofing if C++ side becomes more threaded).
                    // Python side (Engine) will also react to these events to update projection matrix.
                    std::lock_guard<std::mutex> lock(g_sdl_resources_mutex); 
                    g_window_width_cpp = sdl_event.window.data1;
                    g_window_height_cpp = sdl_event.window.data2;
                    // py::print("C++ (poll_sdl_events): Window event SIZE_CHANGED/RESIZED recorded: ", g_window_width_cpp, "x", g_window_height_cpp);
                }
                break;
            default:
                // Optional: Log unknown events if needed for debugging.
                // py::dict unknown_event;
                // unknown_event["type"] = "UNKNOWN_SDL_EVENT";
                // unknown_event["sdl_event_type_id"] = static_cast<int>(sdl_event.type);
                // events_list.append(unknown_event);
                continue; // Skip adding unknown events to the list sent to Python for now
        }
        // Only add the event to the list if py_event is not empty 
        // (e.g. if we didn't 'continue' for an unhandled event type)
        if (!py_event.empty()) {
            events_list.append(py_event);
        }
    }
    return events_list;
}

// Returns a py::bytes object representing the keyboard state.
// Python can index this using SDL_SCANCODE_* constants.
py::bytes get_keyboard_state_cpp() {
    // SDL_PumpEvents(); // Ensures the keyboard state is up-to-date. Called by PollEvent too.
    int num_keys = 0; 
    const Uint8* state = SDL_GetKeyboardState(&num_keys);
    if (state == nullptr || num_keys == 0) {
        // Fallback if SDL_GetKeyboardState returns NULL or 0 keys (should not happen if SDL is init)
        // py::print("C++: SDL_GetKeyboardState returned NULL or 0 keys.");
        return py::bytes(); // Return empty bytes
    }
    return py::bytes(reinterpret_cast<const char*>(state), static_cast<size_t>(num_keys));
}

// Returns (x, y, button_mask)
py::tuple get_mouse_state_cpp() {
    // SDL_PumpEvents(); 
    int x, y;
    Uint32 buttons = SDL_GetMouseState(&x, &y);
    return py::make_tuple(x, y, buttons);
}

// Returns (xrel, yrel)
py::tuple get_relative_mouse_state_cpp() {
    // SDL_PumpEvents(); 
    int xrel, yrel;
    // This function returns the relative motion since the last call to SDL_GetRelativeMouseState 
    // OR SDL_PollEvent, IF relative mode is active.
    // If relative mode is NOT active, it might return deltas since last poll.
    // For pg.mouse.get_rel() like behavior, relative mode is key.
    Uint32 buttons_mask_unused = SDL_GetRelativeMouseState(&xrel, &yrel); 
    return py::make_tuple(xrel, yrel);
}

// --- UI Management Functions (Implementation) ---
void create_or_update_button_cpp(
    const std::string& element_id, int x, int y, int w, int h, 
    const std::string& text, 
    uint8_t bg_r, uint8_t bg_g, uint8_t bg_b, uint8_t bg_a,
    uint8_t text_r, uint8_t text_g, uint8_t text_b, uint8_t text_a,
    uint8_t border_r, uint8_t border_g, uint8_t border_b, uint8_t border_a,
    int border_width, bool visible, int font_size) { // Added font_size parameter
    
    std::lock_guard<std::mutex> lock(g_ui_elements_mutex);
    CppButtonData button;
    button.id = element_id;
    button.rect = {x, y, w, h};
    button.text = text;
    button.background_color = {bg_r, bg_g, bg_b, bg_a};
    button.text_color = {text_r, text_g, text_b, text_a};
    button.border_color = {border_r, border_g, border_b, border_a};
    button.border_width = border_width;
    button.visible = visible;
    button.font_size = (font_size > 0) ? font_size : DEFAULT_UI_FONT_SIZE;
    g_cpp_buttons[element_id] = button;
}

void create_or_update_text_label_cpp(
    const std::string& element_id, int x, int y, int w, int h, 
    const std::string& text, 
    uint8_t text_r, uint8_t text_g, uint8_t text_b, uint8_t text_a,
    int font_size, bool visible) {

    std::lock_guard<std::mutex> lock(g_ui_elements_mutex);
    CppTextData label;
    label.id = element_id;
    // If w or h is 0, it implies auto-sizing based on text. 
    // This will be handled during rendering or if a specific "get_text_size" function is added.
    // For now, store as given.
    label.rect = {x, y, w, h}; 
    label.text = text;
    label.text_color = {text_r, text_g, text_b, text_a};
    label.font_size = (font_size > 0) ? font_size : DEFAULT_UI_FONT_SIZE;
    label.visible = visible;
    g_cpp_texts[element_id] = label;
}

void remove_ui_element_cpp(const std::string& element_id) {
    std::lock_guard<std::mutex> lock(g_ui_elements_mutex);
    if (g_cpp_buttons.erase(element_id) > 0) {
        // py::print("C++: Removed button ", element_id);
    } else if (g_cpp_texts.erase(element_id) > 0) {
        // py::print("C++: Removed text label ", element_id);
    } else {
        // py::print("C++: UI Element not found for removal: ", element_id);
    }
}

void set_ui_element_visibility_cpp(const std::string& element_id, bool visible) {
    std::lock_guard<std::mutex> lock(g_ui_elements_mutex);
    auto it_button = g_cpp_buttons.find(element_id);
    if (it_button != g_cpp_buttons.end()) {
        it_button->second.visible = visible;
        // py::print("C++: Visibility set for button ", element_id, " to ", visible);
        return;
    }
    auto it_text = g_cpp_texts.find(element_id);
    if (it_text != g_cpp_texts.end()) {
        it_text->second.visible = visible;
        // py::print("C++: Visibility set for text ", element_id, " to ", visible);
    } else {
        // py::print("C++: UI Element not found for visibility change: ", element_id);
    }
}

// --- UI Rendering Function ---
void render_ui_elements_cpp() {
    if (!g_sdl_renderer) return;

    std::lock_guard<std::mutex> lock(g_ui_elements_mutex);

    // Render Buttons
    for (const auto& pair : g_cpp_buttons) {
        const CppButtonData& button = pair.second;
        if (!button.visible) continue;

        // Draw background
        SDL_SetRenderDrawColor(g_sdl_renderer, button.background_color.r, button.background_color.g, button.background_color.b, button.background_color.a);
        SDL_RenderFillRect(g_sdl_renderer, &button.rect);

        // Draw border
        if (button.border_width > 0) {
            SDL_SetRenderDrawColor(g_sdl_renderer, button.border_color.r, button.border_color.g, button.border_color.b, button.border_color.a);
            // SDL_RenderDrawRects would be better for multiple rects, but for one, this is fine.
            // For border_width > 1, we might need to draw multiple rects or a thicker line.
            // For simplicity, SDL_RenderDrawRect draws a 1px border. To make it thicker,
            // we can draw multiple concentric rects or adjust the rect and fill.
            // Here, we'll just use SDL_RenderDrawRect for a 1px border of the given color,
            // and ignore border_width > 1 for now, or draw it multiple times.
            for(int i = 0; i < button.border_width; ++i) {
                SDL_Rect border_rect = {button.rect.x + i, button.rect.y + i, button.rect.w - 2*i, button.rect.h - 2*i};
                if (border_rect.w <=0 || border_rect.h <=0) break; // Avoid negative or zero dimensions
                SDL_RenderDrawRect(g_sdl_renderer, &border_rect);
            }
        }

        // Render text
        TTF_Font* button_font = get_font(button.font_size);
        if (button_font && !button.text.empty()) {
            SDL_Surface* text_surface = TTF_RenderUTF8_Blended(button_font, button.text.c_str(), button.text_color);
            if (text_surface) {
                SDL_Texture* text_texture = SDL_CreateTextureFromSurface(g_sdl_renderer, text_surface);
                if (text_texture) {
                    SDL_Rect text_dest_rect;
                    text_dest_rect.w = text_surface->w;
                    text_dest_rect.h = text_surface->h;
                    text_dest_rect.x = button.rect.x + (button.rect.w - text_dest_rect.w) / 2;
                    text_dest_rect.y = button.rect.y + (button.rect.h - text_dest_rect.h) / 2;
                    
                    if (text_dest_rect.w > button.rect.w) { text_dest_rect.w = button.rect.w; }
                    if (text_dest_rect.h > button.rect.h) { text_dest_rect.h = button.rect.h; }
                    if (text_dest_rect.x < button.rect.x) { text_dest_rect.x = button.rect.x; }
                    if (text_dest_rect.y < button.rect.y) { text_dest_rect.y = button.rect.y; }

                    SDL_RenderCopy(g_sdl_renderer, text_texture, nullptr, &text_dest_rect);
                    SDL_DestroyTexture(text_texture);
                } else {
                     py::print(std::string("C++ Warning: SDL_CreateTextureFromSurface failed for button text '") + button.text + std::string("': ") + SDL_GetError());
                }
                SDL_FreeSurface(text_surface);
            } else {
                 py::print(std::string("C++ Warning: TTF_RenderUTF8_Blended failed for button text '") + button.text + std::string("': ") + TTF_GetError());
            }
        } else if (!button_font && !button.text.empty()) {
             py::print(std::string("C++ Warning: Font not available for button text '") + button.text + std::string("'."));
        }
    }

    // Render Text Labels
    for (const auto& pair : g_cpp_texts) {
        const CppTextData& label = pair.second;
        if (!label.visible) continue;

        TTF_Font* label_font = get_font(label.font_size);
        if (label_font && !label.text.empty()) {
            SDL_Surface* text_surface = TTF_RenderUTF8_Blended(label_font, label.text.c_str(), label.text_color);
            if (text_surface) {
                SDL_Texture* text_texture = SDL_CreateTextureFromSurface(g_sdl_renderer, text_surface);
                if (text_texture) {
                    SDL_Rect text_dest_rect;
                    text_dest_rect.w = text_surface->w;
                    text_dest_rect.h = text_surface->h;
                    text_dest_rect.x = label.rect.x + (label.rect.w - text_dest_rect.w) / 2;
                    text_dest_rect.y = label.rect.y + (label.rect.h - text_dest_rect.h) / 2;
                    
                    if (text_dest_rect.w > label.rect.w) { text_dest_rect.w = label.rect.w; }
                    if (text_dest_rect.h > label.rect.h) { text_dest_rect.h = label.rect.h; }
                    if (text_dest_rect.x < label.rect.x) { text_dest_rect.x = label.rect.x; }
                    if (text_dest_rect.y < label.rect.y) { text_dest_rect.y = label.rect.y; }

                    SDL_RenderCopy(g_sdl_renderer, text_texture, nullptr, &text_dest_rect);
                    SDL_DestroyTexture(text_texture);
                } else {
                    py::print(std::string("C++ Warning: SDL_CreateTextureFromSurface failed for label text '") + label.text + std::string("': ") + SDL_GetError());
                }
                SDL_FreeSurface(text_surface);
            } else {
                 py::print(std::string("C++ Warning: TTF_RenderUTF8_Blended failed for label text '") + label.text + std::string("': ") + TTF_GetError());
            }
        } else if (!label_font && !label.text.empty()) {
            py::print(std::string("C++ Warning: Font not available for label text '") + label.text + std::string("'."));
        }
    }
}


// --- Test Function for Python (Оставляем для отладки, если нужен) ---
py::array_t<float> calculate_triangle_normal_test_wrapper(
    py::array_t<float, py::array::c_style | py::array::forcecast> v1_np,
    py::array_t<float, py::array::c_style | py::array::forcecast> v2_np,
    py::array_t<float, py::array::c_style | py::array::forcecast> v3_np) {
    if (v1_np.ndim()!=1||v1_np.shape(0)!=3||v2_np.ndim()!=1||v2_np.shape(0)!=3||v3_np.ndim()!=1||v3_np.shape(0)!=3) {
        throw std::runtime_error("Test normal calc: Input vectors must be 1D NumPy arrays of size 3.");
    }
    glm::vec3 v1(v1_np.data()[0], v1_np.data()[1], v1_np.data()[2]);
    glm::vec3 v2(v2_np.data()[0], v2_np.data()[1], v2_np.data()[2]);
    glm::vec3 v3(v3_np.data()[0], v3_np.data()[1], v3_np.data()[2]);
    glm::vec3 res_norm = calculate_triangle_normal_internal_cpp(v1,v2,v3);
    auto res_np = py::array_t<float>(3); 
    float* ptr = static_cast<float*>(res_np.request().ptr);
    ptr[0] = res_norm.x; ptr[1] = res_norm.y; ptr[2] = res_norm.z;
    return res_np;
}


PYBIND11_MODULE(cpp_renderer_core, m) {
    m.doc() = "C++ core renderer using direct SDL rendering, with L1/L2 cache and input handling";

    m.def("initialize_cpp_renderer", &initialize_cpp_renderer,
          "Initializes SDL creating its own window, and sets up caches. Returns (actual_width, actual_height).",
          py::arg("initial_width"), py::arg("initial_height"), py::arg("fullscreen_flag"),
          py::arg("window_title"), py::arg("l1_cache_capacity"), py::arg("l2_cache_capacity"),
          py::arg("background_color_rgb"));

    m.def("cleanup_cpp_renderer", &cleanup_cpp_renderer, "Cleans up C++ SDL resources and caches.");

    m.def("set_frame_parameters_cpp", &set_frame_parameters_cpp,
          "Sets view/projection matrices and other per-frame rendering flags for C++ processing.",
          py::arg("view_matrix_np"), py::arg("projection_matrix_np"), py::arg("camera_pos_w_np"),
          py::arg("light_enabled_flag"), py::arg("back_cull_enabled_flag"), py::arg("clipping_enabled_flag"),
          py::arg("debug_clipping_enabled_flag"), py::arg("debug_clipped_color_arr"),
          py::arg("sort_triangles_flag"), py::arg("small_triangle_area_threshold"));

    m.def("process_and_accumulate_object_cpp", &process_and_accumulate_object_cpp,
          "Processes a single object and adds its triangles to a global C++ list for the current frame.",
          py::arg("object_id_py"), py::arg("transform_params_np"),
          py::arg("local_vertex_data_np"), py::arg("vertex_data_stride"),
          py::arg("use_vertex_normals_from_mesh"),
          py::call_guard<py::gil_scoped_release>()); 

    m.def("render_accumulated_triangles_cpp", &render_accumulated_triangles_cpp,
          "Renders all accumulated triangles for the frame to the SDL renderer.",
          py::call_guard<py::gil_scoped_release>()); 

    // --- Window and Input Control ---
    m.def("set_window_title_cpp", &set_window_title_cpp, "Sets the SDL window title.", py::arg("title"));
    m.def("set_relative_mouse_mode_cpp", &set_relative_mouse_mode_cpp, "Enables or disables relative mouse mode.", py::arg("active"));
    m.def("set_mouse_visible_cpp", &set_mouse_visible_cpp, "Shows or hides the mouse cursor.", py::arg("visible"));
    m.def("set_window_grab_cpp", &set_window_grab_cpp, "Grabs or ungrabs the mouse cursor to the window.", py::arg("grab_on"));
    
    m.def("poll_sdl_events_cpp", &poll_sdl_events_cpp, "Polls and returns a list of SDL events.");
    m.def("get_keyboard_state_cpp", &get_keyboard_state_cpp, "Returns the current state of the keyboard as bytes.");
    m.def("get_mouse_state_cpp", &get_mouse_state_cpp, "Returns (x, y, button_mask) for the mouse.");
    m.def("get_relative_mouse_state_cpp", &get_relative_mouse_state_cpp, "Returns (xrel, yrel) for relative mouse motion.");

    // --- UI Management ---
    m.def("create_or_update_button_cpp", &create_or_update_button_cpp, 
          "Creates or updates a button UI element in C++.",
          py::arg("element_id"), py::arg("x"), py::arg("y"), py::arg("w"), py::arg("h"),
          py::arg("text"),
          py::arg("bg_r"), py::arg("bg_g"), py::arg("bg_b"), py::arg("bg_a"),
          py::arg("text_r"), py::arg("text_g"), py::arg("text_b"), py::arg("text_a"),
          py::arg("border_r"), py::arg("border_g"), py::arg("border_b"), py::arg("border_a"),
          py::arg("border_width"), py::arg("visible"), py::arg("font_size"));

    m.def("create_or_update_text_label_cpp", &create_or_update_text_label_cpp,
          "Creates or updates a text label UI element in C++.",
          py::arg("element_id"), py::arg("x"), py::arg("y"), py::arg("w"), py::arg("h"),
          py::arg("text"),
          py::arg("text_r"), py::arg("text_g"), py::arg("text_b"), py::arg("text_a"),
          py::arg("font_size"), py::arg("visible"));

    m.def("remove_ui_element_cpp", &remove_ui_element_cpp, 
          "Removes a UI element by ID from C++ maps.", py::arg("element_id"));

    m.def("set_ui_element_visibility_cpp", &set_ui_element_visibility_cpp,
          "Sets the visibility of a UI element by ID in C++.", 
          py::arg("element_id"), py::arg("visible"));

    // --- Test/Debug ---
    m.def("calculate_triangle_normal_cpp_test_func", &calculate_triangle_normal_test_wrapper,
          "Test function for normal calculation",
          py::arg("v1"), py::arg("v2"), py::arg("v3"));
    
    py::class_<CppScreenTriangle>(m, "_CppScreenTriangle_DebugBinding")
        .def_property_readonly("screen_coords", [](const CppScreenTriangle &self) {
            py::list py_coords_list;
            for (int i = 0; i < 3; ++i) {
                py_coords_list.append(py::make_tuple(self.screen_coords[i][0], self.screen_coords[i][1]));
            }
            return py_coords_list;
        })
        .def_readonly("depth", &CppScreenTriangle::depth)
        .def_property_readonly("color", [](const CppScreenTriangle &self) {
            return py::make_tuple(self.color_final_uint8[0], self.color_final_uint8[1], self.color_final_uint8[2]);
        });
}

// --- END OF FILE cpp_renderer_core.cpp ---