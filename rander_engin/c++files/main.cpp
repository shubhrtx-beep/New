#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <GL/gl.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <cmath>
#include <cctype>

// =============================================================================
// Minimal, Zero-Dependency JSON Parser for Draw3 Transfer Packets
// =============================================================================

enum JsonType { J_NULL, J_BOOL, J_NUM, J_STR, J_ARR, J_OBJ };

struct JsonVal {
    JsonType type = J_NULL;
    bool b = false;
    double num = 0.0;
    std::string str;
    std::vector<JsonVal> arr;
    std::map<std::string, JsonVal> obj;

    bool has(const std::string& k) const {
        return type == J_OBJ && obj.find(k) != obj.end();
    }
    const JsonVal& operator[](const std::string& k) const {
        static JsonVal null_val;
        if (type == J_OBJ) {
            auto it = obj.find(k);
            if (it != obj.end()) return it->second;
        }
        return null_val;
    }
    const JsonVal& operator[](size_t idx) const {
        static JsonVal null_val;
        if (type == J_ARR && idx < arr.size()) return arr[idx];
        return null_val;
    }
    double as_double(double def = 0.0) const { return (type == J_NUM) ? num : def; }
    std::string as_str(const std::string& def = "") const { return (type == J_STR) ? str : def; }
    bool as_bool(bool def = false) const { return (type == J_BOOL) ? b : def; }
};

class SimpleJsonParser {
    std::string src;
    size_t pos = 0;

    void skip_whitespace() {
        while (pos < src.size() && (std::isspace(src[pos]) || src[pos] == '\r' || src[pos] == '\n')) {
            pos++;
        }
    }

    std::string parse_string() {
        pos++; // skip opening quote
        std::string s;
        while (pos < src.size() && src[pos] != '"') {
            if (src[pos] == '\\' && pos + 1 < src.size()) {
                pos++;
                if (src[pos] == 'n') s += '\n';
                else if (src[pos] == 't') s += '\t';
                else s += src[pos];
            } else {
                s += src[pos];
            }
            pos++;
        }
        if (pos < src.size() && src[pos] == '"') pos++;
        return s;
    }

    double parse_number() {
        size_t start = pos;
        if (src[pos] == '-') pos++;
        while (pos < src.size() && (std::isdigit(src[pos]) || src[pos] == '.' || src[pos] == 'e' || src[pos] == 'E' || src[pos] == '+' || src[pos] == '-')) {
            pos++;
        }
        std::string num_str = src.substr(start, pos - start);
        return std::stod(num_str);
    }

public:
    explicit SimpleJsonParser(std::string s) : src(std::move(s)), pos(0) {}

    JsonVal parse() {
        skip_whitespace();
        if (pos >= src.size()) return JsonVal();

        char c = src[pos];
        if (c == '"') {
            JsonVal v; v.type = J_STR; v.str = parse_string(); return v;
        }
        if (std::isdigit(c) || c == '-') {
            JsonVal v; v.type = J_NUM; v.num = parse_number(); return v;
        }
        if (c == '{') {
            pos++;
            JsonVal v; v.type = J_OBJ;
            skip_whitespace();
            if (pos < src.size() && src[pos] == '}') { pos++; return v; }
            while (pos < src.size()) {
                skip_whitespace();
                if (src[pos] != '"') break;
                std::string key = parse_string();
                skip_whitespace();
                if (pos < src.size() && src[pos] == ':') pos++;
                v.obj[key] = parse();
                skip_whitespace();
                if (pos < src.size() && src[pos] == ',') { pos++; }
                else if (pos < src.size() && src[pos] == '}') { pos++; break; }
            }
            return v;
        }
        if (c == '[') {
            pos++;
            JsonVal v; v.type = J_ARR;
            skip_whitespace();
            if (pos < src.size() && src[pos] == ']') { pos++; return v; }
            while (pos < src.size()) {
                v.arr.push_back(parse());
                skip_whitespace();
                if (pos < src.size() && src[pos] == ',') { pos++; }
                else if (pos < src.size() && src[pos] == ']') { pos++; break; }
            }
            return v;
        }
        if (src.compare(pos, 4, "true") == 0) { pos += 4; JsonVal v; v.type = J_BOOL; v.b = true; return v; }
        if (src.compare(pos, 5, "false") == 0) { pos += 5; JsonVal v; v.type = J_BOOL; v.b = false; return v; }
        if (src.compare(pos, 4, "null") == 0) { pos += 4; JsonVal v; v.type = J_NULL; return v; }

        pos++;
        return JsonVal();
    }
};

// =============================================================================
// Robust 2D Polygon Stroke & Miter Joint Triangulation
// =============================================================================

void draw_polygon_stroke(const std::vector<float>& vertices, float width, float r, float g, float b, float a) {
    size_t num_verts = vertices.size() / 2;
    if (num_verts < 3 || width <= 0.0f) return;

    // 1. Calculate signed area to detect winding
    float signed_area = 0.0f;
    for (size_t i = 0; i < num_verts; ++i) {
        size_t next = (i + 1) % num_verts;
        float x1 = vertices[i * 2], y1 = vertices[i * 2 + 1];
        float x2 = vertices[next * 2], y2 = vertices[next * 2 + 1];
        signed_area += (x1 * y2 - x2 * y1);
    }
    bool is_clockwise = (signed_area < 0.0f);

    // 2. Compute edge unit normals
    std::vector<float> edge_nx(num_verts), edge_ny(num_verts);
    for (size_t i = 0; i < num_verts; ++i) {
        size_t next = (i + 1) % num_verts;
        float dx = vertices[next * 2] - vertices[i * 2];
        float dy = vertices[next * 2 + 1] - vertices[i * 2 + 1];
        float len = sqrtf(dx * dx + dy * dy);
        if (len < 1e-6f) len = 1.0f;
        if (is_clockwise) {
            edge_nx[i] = -dy / len;
            edge_ny[i] =  dx / len;
        } else {
            edge_nx[i] =  dy / len;
            edge_ny[i] = -dx / len;
        }
    }

    // 3. Compute miter offsets at each vertex
    float hw = width * 0.5f;
    std::vector<float> outer_vx(num_verts), outer_vy(num_verts);
    std::vector<float> inner_vx(num_verts), inner_vy(num_verts);

    for (size_t i = 0; i < num_verts; ++i) {
        size_t prev = (i + num_verts - 1) % num_verts;
        float n1x = edge_nx[prev], n1y = edge_ny[prev];
        float n2x = edge_nx[i],    n2y = edge_ny[i];

        float dot = n1x * n2x + n1y * n2y;
        float denom = 1.0f + dot;

        float mx, my;
        if (denom > 0.05f) {
            mx = (n1x + n2x) / denom;
            my = (n1y + n2y) / denom;
            float miter_len_sq = mx * mx + my * my;
            if (miter_len_sq > 16.0f) { // clamp miter limit
                float scale = 4.0f / sqrtf(miter_len_sq);
                mx *= scale;
                my *= scale;
            }
        } else {
            mx = n1x;
            my = n1y;
        }

        float vx = vertices[i * 2];
        float vy = vertices[i * 2 + 1];

        outer_vx[i] = vx + hw * mx;
        outer_vy[i] = vy + hw * my;
        inner_vx[i] = vx - hw * mx;
        inner_vy[i] = vy - hw * my;
    }

    // 4. Render stroke as a continuous closed GL_TRIANGLE_STRIP
    glColor4f(r, g, b, a);
    glBegin(GL_TRIANGLE_STRIP);
    for (size_t i = 0; i < num_verts; ++i) {
        glVertex2f(outer_vx[i], outer_vy[i]);
        glVertex2f(inner_vx[i], inner_vy[i]);
    }
    // Close the loop
    glVertex2f(outer_vx[0], outer_vy[0]);
    glVertex2f(inner_vx[0], inner_vy[0]);
    glEnd();
}

void hsv_to_rgb(float h, float s, float v, float& r, float& g, float& b) {
    h = fmodf(h, 360.0f);
    if (h < 0.0f) h += 360.0f;
    float s_norm = s / 100.0f;
    float v_norm = v / 100.0f;

    float c = v_norm * s_norm;
    float x = c * (1.0f - fabsf(fmodf(h / 60.0f, 2.0f) - 1.0f));
    float m = v_norm - c;

    float r1 = 0.0f, g1 = 0.0f, b1 = 0.0f;
    if (h < 60.0f) { r1 = c; g1 = x; }
    else if (h < 120.0f) { r1 = x; g1 = c; }
    else if (h < 180.0f) { g1 = c; b1 = x; }
    else if (h < 240.0f) { g1 = x; b1 = c; }
    else if (h < 300.0f) { r1 = x; b1 = c; }
    else { r1 = c; b1 = x; }

    r = r1 + m;
    g = g1 + m;
    b = b1 + m;
}

struct ColorChannel {
    bool exists = false;
    bool is_hsv = false;
    // Static RGBA
    float static_r = 1.0f, static_g = 1.0f, static_b = 1.0f, static_a = 1.0f;
    // HSV components
    bool dynamic_h = false;
    float h_speed = 60.0f, h_offset = 0.0f, h_static = 0.0f;
    float s = 100.0f, v = 100.0f, a = 1.0f;

    // Evaluate color at time t
    void evaluate(float t, float& out_r, float& out_g, float& out_b, float& out_a) const {
        if (!exists) { out_r = out_g = out_b = out_a = 0.0f; return; }
        if (!is_hsv) {
            out_r = static_r; out_g = static_g; out_b = static_b; out_a = static_a;
            return;
        }

        float cur_h = h_static;
        if (dynamic_h) {
            cur_h = fmodf(h_speed * t + h_offset, 360.0f);
            if (cur_h < 0.0f) cur_h += 360.0f;
        }
        hsv_to_rgb(cur_h, s, v, out_r, out_g, out_b);
        out_a = a;
    }
};

struct DynamicFloat {
    bool is_pulse = false;
    float static_val = 1.0f;
    float min_val = 1.0f, max_val = 1.0f, speed = 1.0f;

    float evaluate(float t) const {
        if (!is_pulse) return static_val;
        float factor = 0.5f + 0.5f * sinf(speed * 2.0f * 3.14159265f * t);
        return min_val + (max_val - min_val) * factor;
    }
};

struct RenderShape {
    std::string name;
    float pos_x = 0.0f, pos_y = 0.0f;
    std::vector<float> vertices; // [x, y, x, y, ...]
    std::vector<int> indices;    // Triangles
    ColorChannel body_color;
    ColorChannel border_color;
    DynamicFloat border_width;
};

// =============================================================================
// Scene Loader
// =============================================================================

std::vector<RenderShape> load_scene(const std::string& path, float& canvas_w, float& canvas_h) {
    std::vector<RenderShape> shapes;
    std::ifstream file(path);
    if (!file.is_open()) {
        std::cerr << "Failed to open scene file: " << path << std::endl;
        return shapes;
    }
    std::stringstream buf;
    buf << file.rdbuf();
    SimpleJsonParser parser(buf.str());
    JsonVal root = parser.parse();

    canvas_w = (float)root["canvas"][0].as_double(960.0);
    canvas_h = (float)root["canvas"][1].as_double(720.0);

    const JsonVal& shape_list = root["shapes"];
    for (size_t i = 0; i < shape_list.arr.size(); ++i) {
        const JsonVal& s_json = shape_list[i];
        RenderShape rs;
        rs.name = s_json["name"].as_str();
        rs.pos_x = (float)s_json["transform"]["position"][0].as_double(0.0);
        rs.pos_y = (float)s_json["transform"]["position"][1].as_double(0.0);

        // Load geometry vertices
        const JsonVal& v_arr = s_json["geometry"]["vertices"];
        for (size_t vi = 0; vi < v_arr.arr.size(); ++vi) {
            rs.vertices.push_back((float)v_arr[vi].as_double(0.0));
        }

        // Load geometry indices
        const JsonVal& idx_arr = s_json["geometry"]["indices"];
        for (size_t ii = 0; ii < idx_arr.arr.size(); ++ii) {
            rs.indices.push_back((int)idx_arr[ii].as_double(0.0));
        }

        // Color channels
        const JsonVal& c_json = s_json["color"]["channels"];

        // Body fill
        if (c_json.has("body") && c_json["body"].type != J_NULL) {
            rs.body_color.exists = true;
            const JsonVal& fill = c_json["body"]["fill"];
            if (fill.type == J_ARR && fill.arr.size() >= 4) {
                rs.body_color.is_hsv = false;
                rs.body_color.static_r = (float)fill[0].as_double(1.0);
                rs.body_color.static_g = (float)fill[1].as_double(1.0);
                rs.body_color.static_b = (float)fill[2].as_double(1.0);
                rs.body_color.static_a = (float)fill[3].as_double(1.0);
            } else if (fill.type == J_OBJ && fill["type"].as_str() == "hsv") {
                rs.body_color.is_hsv = true;
                rs.body_color.s = (float)fill["s"].as_double(100.0);
                rs.body_color.v = (float)fill["v"].as_double(100.0);
                rs.body_color.a = (float)fill["a"].as_double(1.0);
                if (fill["h"].type == J_OBJ && fill["h"]["type"].as_str() == "cycle") {
                    rs.body_color.dynamic_h = true;
                    rs.body_color.h_speed = (float)fill["h"]["speed"].as_double(60.0);
                    rs.body_color.h_offset = (float)fill["h"]["offset"].as_double(0.0);
                } else {
                    rs.body_color.h_static = (float)fill["h"].as_double(0.0);
                }
            }
        }

        // Border fill & width
        if (c_json.has("border") && c_json["border"].type != J_NULL) {
            rs.border_color.exists = true;
            const JsonVal& b_fill = c_json["border"]["fill"];
            if (b_fill.type == J_ARR && b_fill.arr.size() >= 4) {
                rs.border_color.is_hsv = false;
                rs.border_color.static_r = (float)b_fill[0].as_double(1.0);
                rs.border_color.static_g = (float)b_fill[1].as_double(1.0);
                rs.border_color.static_b = (float)b_fill[2].as_double(1.0);
                rs.border_color.static_a = (float)b_fill[3].as_double(1.0);
            } else if (b_fill.type == J_OBJ && b_fill["type"].as_str() == "hsv") {
                rs.border_color.is_hsv = true;
                rs.border_color.s = (float)b_fill["s"].as_double(100.0);
                rs.border_color.v = (float)b_fill["v"].as_double(100.0);
                rs.border_color.a = (float)b_fill["a"].as_double(1.0);
                if (b_fill["h"].type == J_OBJ && b_fill["h"]["type"].as_str() == "cycle") {
                    rs.border_color.dynamic_h = true;
                    rs.border_color.h_speed = (float)b_fill["h"]["speed"].as_double(60.0);
                    rs.border_color.h_offset = (float)b_fill["h"]["offset"].as_double(0.0);
                } else {
                    rs.border_color.h_static = (float)b_fill["h"].as_double(0.0);
                }
            }

            // Border width (static or pulse)
            const JsonVal& w_val = c_json["border"]["width"];
            if (w_val.type == J_OBJ && w_val["type"].as_str() == "pulse") {
                rs.border_width.is_pulse = true;
                rs.border_width.min_val = (float)w_val["min"].as_double(1.0);
                rs.border_width.max_val = (float)w_val["max"].as_double(5.0);
                rs.border_width.speed = (float)w_val["speed"].as_double(1.0);
            } else {
                rs.border_width.is_pulse = false;
                rs.border_width.static_val = (float)w_val.as_double(1.0);
            }
        }

        shapes.push_back(rs);
    }
    return shapes;
}

// =============================================================================
// Win32 OpenGL Application Window
// =============================================================================

LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    if (msg == WM_CLOSE || msg == WM_DESTROY) {
        PostQuitMessage(0);
        return 0;
    }
    if (msg == WM_KEYDOWN && wParam == VK_ESCAPE) {
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProc(hwnd, msg, wParam, lParam);
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    AllocConsole();
    freopen("CONOUT$", "w", stdout);
    std::cout << "======================================================" << std::endl;
    std::cout << "Draw3 Real-Time OpenGL Visual Color Test Engine" << std::endl;
    std::cout << "======================================================" << std::endl;

    float canvas_w = 960.0f, canvas_h = 720.0f;
    std::string scene_path = "D:/draw3/rander_engin/scene.json";
    std::vector<RenderShape> shapes = load_scene(scene_path, canvas_w, canvas_h);
    std::cout << "Loaded " << shapes.size() << " shapes from " << scene_path << std::endl;

    // Register Window Class
    WNDCLASSEX wc = {};
    wc.cbSize = sizeof(WNDCLASSEX);
    wc.style = CS_OWNDC | CS_HREDRAW | CS_VREDRAW;
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = "Draw3OpenGLTestClass";
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    RegisterClassEx(&wc);

    int win_w = 960, win_h = 720;
    RECT rect = {0, 0, win_w, win_h};
    AdjustWindowRect(&rect, WS_OVERLAPPEDWINDOW, FALSE);

    HWND hwnd = CreateWindowEx(
        0, wc.lpszClassName,
        "Draw3 — Interactive C++ OpenGL Color & Animation Test (Press ESC to close)",
        WS_OVERLAPPEDWINDOW | WS_VISIBLE,
        CW_USEDEFAULT, CW_USEDEFAULT,
        rect.right - rect.left, rect.bottom - rect.top,
        NULL, NULL, hInstance, NULL
    );

    HDC hdc = GetDC(hwnd);

    // Setup Pixel Format
    PIXELFORMATDESCRIPTOR pfd = {};
    pfd.nSize = sizeof(PIXELFORMATDESCRIPTOR);
    pfd.nVersion = 1;
    pfd.dwFlags = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER;
    pfd.iPixelType = PFD_TYPE_RGBA;
    pfd.cColorBits = 32;
    pfd.cDepthBits = 24;

    int format = ChoosePixelFormat(hdc, &pfd);
    SetPixelFormat(hdc, format, &pfd);

    HGLRC hglrc = wglCreateContext(hdc);
    wglMakeCurrent(hdc, hglrc);

    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glEnable(GL_LINE_SMOOTH);
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST);

    // Timing Setup
    LARGE_INTEGER freq, start_counter, cur_counter;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&start_counter);

    std::cout << "Running render loop at 60 FPS... Window is open!" << std::endl;

    MSG msg = {};
    bool running = true;
    while (running) {
        while (PeekMessage(&msg, NULL, 0, 0, PM_REMOVE)) {
            if (msg.message == WM_QUIT) {
                running = false;
                break;
            }
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }

        if (!running) break;

        QueryPerformanceCounter(&cur_counter);
        float time_sec = (float)(cur_counter.QuadPart - start_counter.QuadPart) / (float)freq.QuadPart;

        // Viewport and Orthographic Projection
        RECT client_rect;
        GetClientRect(hwnd, &client_rect);
        int w = client_rect.right - client_rect.left;
        int h = client_rect.bottom - client_rect.top;
        if (w <= 0) w = 1;
        if (h <= 0) h = 1;
        glViewport(0, 0, w, h);

        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glOrtho(-canvas_w / 2.0f, canvas_w / 2.0f, -canvas_h / 2.0f, canvas_h / 2.0f, -1.0, 1.0);

        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();

        // Dark background #0b0f19
        glClearColor(0.043f, 0.059f, 0.098f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        // Draw each shape using its geometry and animated color evaluation
        for (const auto& s : shapes) {
            glPushMatrix();
            glTranslatef(s.pos_x, s.pos_y, 0.0f);

            // 1. Draw Body Fill
            if (s.body_color.exists && !s.indices.empty() && !s.vertices.empty()) {
                float r, g, b, a;
                s.body_color.evaluate(time_sec, r, g, b, a);
                glColor4f(r, g, b, a);

                glBegin(GL_TRIANGLES);
                for (size_t idx : s.indices) {
                    if (idx * 2 + 1 < s.vertices.size()) {
                        glVertex2f(s.vertices[idx * 2], s.vertices[idx * 2 + 1]);
                    }
                }
                glEnd();
            }

            // 2. Draw Border Stroke (Triangulated Continuous Miter Joint)
            if (s.border_color.exists && s.vertices.size() >= 4) {
                float r, g, b, a;
                s.border_color.evaluate(time_sec, r, g, b, a);
                float cur_width = s.border_width.evaluate(time_sec);
                draw_polygon_stroke(s.vertices, cur_width, r, g, b, a);
            }

            glPopMatrix();
        }

        SwapBuffers(hdc);
        Sleep(16); // ~60 FPS
    }

    wglMakeCurrent(NULL, NULL);
    wglDeleteContext(hglrc);
    ReleaseDC(hwnd, hdc);
    DestroyWindow(hwnd);
    return 0;
}
