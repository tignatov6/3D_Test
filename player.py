# player.py
# import pygame as pg # Pygame больше не нужен здесь для ввода напрямую
from camera import Camera
from settings import PLAYER_POS, MOUSE_SENSITIVITY, PLAYER_SPEED # Импортируем необходимые настройки

# --- SDL Scancode Константы ---
# Эти значения соответствуют стандартным SDL Scancodes.
# Полный список: https://wiki.libsdl.org/SDL2/SDL_Scancode
# Используются как индексы для массива sdl_keyboard_state.

SDL_SCANCODE_UNKNOWN = 0

SDL_SCANCODE_A = 4
SDL_SCANCODE_B = 5
SDL_SCANCODE_C = 6
SDL_SCANCODE_D = 7
SDL_SCANCODE_E = 8
SDL_SCANCODE_F = 9
SDL_SCANCODE_G = 10
SDL_SCANCODE_H = 11
SDL_SCANCODE_I = 12
SDL_SCANCODE_J = 13
SDL_SCANCODE_K = 14
SDL_SCANCODE_L = 15
SDL_SCANCODE_M = 16
SDL_SCANCODE_N = 17
SDL_SCANCODE_O = 18
SDL_SCANCODE_P = 19
SDL_SCANCODE_Q = 20
SDL_SCANCODE_R = 21
SDL_SCANCODE_S = 22
SDL_SCANCODE_T = 23
SDL_SCANCODE_U = 24
SDL_SCANCODE_V = 25
SDL_SCANCODE_W = 26
SDL_SCANCODE_X = 27
SDL_SCANCODE_Y = 28
SDL_SCANCODE_Z = 29

SDL_SCANCODE_1 = 30
SDL_SCANCODE_2 = 31
SDL_SCANCODE_3 = 32
SDL_SCANCODE_4 = 33
SDL_SCANCODE_5 = 34
SDL_SCANCODE_6 = 35
SDL_SCANCODE_7 = 36
SDL_SCANCODE_8 = 37
SDL_SCANCODE_9 = 38
SDL_SCANCODE_0 = 39

SDL_SCANCODE_RETURN = 40
SDL_SCANCODE_ESCAPE = 41
SDL_SCANCODE_BACKSPACE = 42
SDL_SCANCODE_TAB = 43
SDL_SCANCODE_SPACE = 44

SDL_SCANCODE_MINUS = 45
SDL_SCANCODE_EQUALS = 46
SDL_SCANCODE_LEFTBRACKET = 47
SDL_SCANCODE_RIGHTBRACKET = 48
SDL_SCANCODE_BACKSLASH = 49 
SDL_SCANCODE_NONUSHASH = 50 
SDL_SCANCODE_SEMICOLON = 51
SDL_SCANCODE_APOSTROPHE = 52
SDL_SCANCODE_GRAVE = 53 
SDL_SCANCODE_COMMA = 54
SDL_SCANCODE_PERIOD = 55
SDL_SCANCODE_SLASH = 56

SDL_SCANCODE_CAPSLOCK = 57

SDL_SCANCODE_F1 = 58
SDL_SCANCODE_F2 = 59
SDL_SCANCODE_F3 = 60
SDL_SCANCODE_F4 = 61
SDL_SCANCODE_F5 = 62
SDL_SCANCODE_F6 = 63
SDL_SCANCODE_F7 = 64
SDL_SCANCODE_F8 = 65
SDL_SCANCODE_F9 = 66
SDL_SCANCODE_F10 = 67
SDL_SCANCODE_F11 = 68
SDL_SCANCODE_F12 = 69

SDL_SCANCODE_PRINTSCREEN = 70
SDL_SCANCODE_SCROLLLOCK = 71
SDL_SCANCODE_PAUSE = 72
SDL_SCANCODE_INSERT = 73 
SDL_SCANCODE_HOME = 74
SDL_SCANCODE_PAGEUP = 75
SDL_SCANCODE_DELETE = 76
SDL_SCANCODE_END = 77
SDL_SCANCODE_PAGEDOWN = 78
SDL_SCANCODE_RIGHT = 79
SDL_SCANCODE_LEFT = 80
SDL_SCANCODE_DOWN = 81
SDL_SCANCODE_UP = 82

SDL_SCANCODE_NUMLOCKCLEAR = 83 
SDL_SCANCODE_KP_DIVIDE = 84
SDL_SCANCODE_KP_MULTIPLY = 85
SDL_SCANCODE_KP_MINUS = 86
SDL_SCANCODE_KP_PLUS = 87
SDL_SCANCODE_KP_ENTER = 88
SDL_SCANCODE_KP_1 = 89
SDL_SCANCODE_KP_2 = 90
SDL_SCANCODE_KP_3 = 91
SDL_SCANCODE_KP_4 = 92
SDL_SCANCODE_KP_5 = 93
SDL_SCANCODE_KP_6 = 94
SDL_SCANCODE_KP_7 = 95
SDL_SCANCODE_KP_8 = 96
SDL_SCANCODE_KP_9 = 97
SDL_SCANCODE_KP_0 = 98
SDL_SCANCODE_KP_PERIOD = 99

SDL_SCANCODE_LCTRL = 224
SDL_SCANCODE_LSHIFT = 225
SDL_SCANCODE_LALT = 226 # alt, option
SDL_SCANCODE_LGUI = 227 # windows, command, super
SDL_SCANCODE_RCTRL = 228
SDL_SCANCODE_RSHIFT = 229
SDL_SCANCODE_RALT = 230 # alt gr, option
SDL_SCANCODE_RGUI = 231 # windows, command, super

SDL_NUM_SCANCODES = 512 # Максимальное количество скан-кодов


class Player(Camera):
    def __init__(self, app, position=PLAYER_POS, yaw=-90.0, pitch=0.0): # Явное указание float для углов
        self.app = app # Ссылка на экземпляр Engine
        super().__init__(position, yaw, pitch)

    def update(self):
        """
        Обновляет состояние камеры (векторы). 
        Обработка ввода теперь происходит в handle_input_sdl, который вызывается из Engine.
        """
        super().update() # Вызывает Camera.update_camera_vectors()

    def handle_input_sdl(self, sdl_events: list, sdl_keyboard_state: bytes, delta_time: float):
        """
        Обрабатывает ввод от SDL.
        :param sdl_events: Список событий от SDL (словари).
        :param sdl_keyboard_state: Состояние клавиатуры от SDL (bytes).
        :param delta_time: Время кадра.
        """
        if not sdl_keyboard_state: # Если состояние клавиатуры не получено
            # print("Warning: sdl_keyboard_state is None or empty in Player.handle_input_sdl")
            pass # Можно добавить логирование или обработку ошибки

        self._process_mouse_sdl(sdl_events)
        self._process_keyboard_sdl(sdl_keyboard_state, delta_time)

    def _process_mouse_sdl(self, sdl_events: list):
        """ Обрабатывает события движения мыши из списка событий SDL. """
        # В SDL, если включен SDL_SetRelativeMouseMode(SDL_TRUE),
        # то события MOUSEMOTION содержат относительное смещение в xrel и yrel.
        # Это аналог pg.mouse.get_rel().
        # Если бы мы не использовали относительный режим, нам пришлось бы использовать 
        # self.app.renderer.get_relative_mouse_state() или вычислять вручную.

        for event_data in sdl_events:
            if event_data.get('type') == 'MOUSEMOTION':
                mouse_dx = event_data.get('xrel', 0)
                mouse_dy = event_data.get('yrel', 0)

                if mouse_dx:
                    self.rotate_yaw(delta_x = float(mouse_dx) * MOUSE_SENSITIVITY)
                if mouse_dy:
                    self.rotate_pitch(delta_y = float(mouse_dy) * MOUSE_SENSITIVITY)
                # Нет необходимости суммировать, так как каждое событие MOUSEMOTION дает дельту
                # с момента последнего события. SDL_SetRelativeMouseMode(SDL_TRUE) это обеспечивает.

    def _process_keyboard_sdl(self, key_state: bytes, delta_time: float):
        """ Обрабатывает состояние клавиатуры SDL для перемещения игрока. """
        if not key_state or len(key_state) < SDL_NUM_SCANCODES: # Проверка, что key_state не пустой и достаточной длины
            # print(f"Warning: Invalid key_state in _process_keyboard_sdl. Length: {len(key_state) if key_state else 'None'}")
            return

        vel = PLAYER_SPEED * delta_time

        # Проверяем нажатые клавиши, используя SDL_SCANCODE константы как индексы
        # key_state[SCANCODE] вернет 1 (или True), если клавиша нажата, 0 (или False) иначе.
        
        # Движение вперед/назад
        if key_state[SDL_SCANCODE_W]:
            self.move_forward(vel)
        if key_state[SDL_SCANCODE_S]:
            self.move_back(vel)

        # Движение влево/вправо (стрейф)
        if key_state[SDL_SCANCODE_A]:
            self.move_left(vel)
        if key_state[SDL_SCANCODE_D]:
            self.move_right(vel)

        # Движение вверх/вниз (полет/приседание)
        if key_state[SDL_SCANCODE_SPACE]: # Пример: пробел для движения вверх
            self.move_up(vel)
        if key_state[SDL_SCANCODE_LSHIFT] or key_state[SDL_SCANCODE_RSHIFT]: # Пример: Shift для движения вниз
            self.move_down(vel)
        
        # Альтернативные клавиши для движения вверх/вниз (если нужны)
        if key_state[SDL_SCANCODE_Q]: # Часто используется для "вверх" в редакторах
             # self.move_up(vel) # Закомментировано, чтобы не конфликтовать с SPACE
             pass
        if key_state[SDL_SCANCODE_E]: # Часто используется для "вниз" или "использовать"
             # self.move_down(vel) # Закомментировано, чтобы не конфликтовать с SHIFT
             pass

    # Старые методы, основанные на Pygame вводе, больше не нужны:
    # def mouse_control(self): ...
    # def keyboard_control(self): ...