# ui/panel.py
import pygame
from .ui_element import UIElement

class Panel(UIElement):
    def __init__(self, rect: pygame.Rect, 
                 background_color: tuple = (50, 50, 50, 200), # Полупрозрачный серый по умолчанию
                 border_color: tuple | None = None, 
                 border_width: int = 0,
                 visible: bool = True, parent=None, id: str = None):
        super().__init__(rect, visible, parent, id)
        
        self._background_color = background_color
        self._border_color = border_color if border_color else (0,0,0,0) # Прозрачный, если None
        self._border_width = border_width
        
        # Pygame-side drawing - не обязателен, если все рендерится через C++
        # self._surface = pygame.Surface(rect.size, pygame.SRCALPHA) # Для поддержки альфа-канала
        # self.redraw_pygame_surface()
        self.mark_dirty() # Пометить грязным для первоначальной синхронизации с C++

    @property
    def background_color(self) -> tuple:
        return self._background_color

    @background_color.setter
    def background_color(self, value: tuple):
        if self._background_color != value:
            self._background_color = value
            # self.redraw_pygame_surface()
            self.mark_dirty()

    @property
    def border_color(self) -> tuple:
        return self._border_color

    @border_color.setter
    def border_color(self, value: tuple | None):
        new_color = value if value else (0,0,0,0)
        if self._border_color != new_color:
            self._border_color = new_color
            # self.redraw_pygame_surface()
            self.mark_dirty()

    @property
    def border_width(self) -> int:
        return self._border_width

    @border_width.setter
    def border_width(self, value: int):
        if self._border_width != value:
            self._border_width = max(0, value) # Ширина не может быть отрицательной
            # self.redraw_pygame_surface()
            self.mark_dirty()

    # def redraw_pygame_surface(self):
    #     """Если используется Pygame-side отрисовка для этого элемента."""
    #     if not hasattr(self, '_surface') or self._surface.get_size() != self.rect.size:
    #         self._surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        
    #     self._surface.fill(self.background_color)
    #     if self.border_width > 0 and self.border_color[3] > 0: # Рисуем рамку, если она видима
    #         pygame.draw.rect(self._surface, self.border_color, self._surface.get_rect(), self.border_width)

    def draw(self, surface_or_renderer):
        """Эта функция в основном для Pygame-side отрисовки, если она нужна.
           C++ рендерер будет рисовать на основе данных, синхронизированных через UIManager."""
        if not self.visible:
            return
        # if hasattr(self, '_surface') and self._surface:
        #     surface_or_renderer.blit(self._surface, self.rect.topleft)
        pass # Основная отрисовка через C++

    # handle_event и update могут быть унаследованы или быть пустыми для простой панели