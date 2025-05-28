import pygame
from .ui_element import UIElement

class TextLabel(UIElement):
    def __init__(self, rect: pygame.Rect, text: str, 
                 font_name: str = None, font_size: int = 24, 
                 text_color: tuple = (255, 255, 255),
                 visible: bool = True, parent=None, id: str = None,
                 auto_size_rect: bool = False): # New flag for auto-sizing logic
        super().__init__(rect, visible, parent, id)
        
        self._text = text
        self._font_name = font_name
        self._font_size = font_size
        self._text_color = text_color
        self._auto_size_rect = auto_size_rect 

        # Initial font and text surface creation
        self._update_font_and_text_surface(initial_setup=True)

    def _update_font_and_text_surface(self, initial_setup=False):
        try:
            self._font = pygame.font.Font(self._font_name, self._font_size)
        except pygame.error as e:
            print(f"Warning: Could not load font '{self._font_name}' at size {self._font_size}. Using default. Error: {e}")
            self._font = pygame.font.Font(None, self._font_size) # Pygame default font

        self._text_surface = self._font.render(self._text, True, self._text_color)
        
        # Auto-size logic
        # Use self.rect (property) to ensure mark_dirty is called by UIElement's setter
        current_rect_obj = self.rect 
        new_w, new_h = current_rect_obj.width, current_rect_obj.height

        if self._auto_size_rect or (initial_setup and (current_rect_obj.width == 0 or current_rect_obj.height == 0)):
            text_surf_rect = self._text_surface.get_rect()
            if self._auto_size_rect or current_rect_obj.width == 0:
                new_w = text_surf_rect.width
            if self._auto_size_rect or current_rect_obj.height == 0:
                new_h = text_surf_rect.height
            
            if current_rect_obj.width != new_w or current_rect_obj.height != new_h:
                # This will use the rect property setter from UIElement, which calls mark_dirty()
                self.rect = pygame.Rect(current_rect_obj.left, current_rect_obj.top, new_w, new_h)
                # After self.rect is updated (which also calls mark_dirty),
                # we need to ensure our internal _text_rect for Pygame drawing is centered.
                self._text_rect = self._text_surface.get_rect(center=self.rect.center)
            else:
                 # If size didn't change, still ensure _text_rect is centered (e.g. if rect was moved)
                self._text_rect = self._text_surface.get_rect(center=self.rect.center)
        else:
            # No auto-sizing, just center the text in the current rect
            self._text_rect = self._text_surface.get_rect(center=self.rect.center)
        
        self.mark_dirty() # Text content, style, or related rect auto-size implies visual change

    # Properties
    @property
    def text(self): return self._text
    @text.setter
    def text(self, value):
        if self._text != value:
            self._text = value
            self._update_font_and_text_surface()

    @property
    def font_name(self): return self._font_name
    @font_name.setter
    def font_name(self, value):
        if self._font_name != value:
            self._font_name = value
            self._update_font_and_text_surface()

    @property
    def font_size(self): return self._font_size
    @font_size.setter
    def font_size(self, value):
        if self._font_size != value:
            self._font_size = value
            self._update_font_and_text_surface()

    @property
    def text_color(self): return self._text_color
    @text_color.setter
    def text_color(self, value):
        if self._text_color != value:
            self._text_color = value
            self._update_font_and_text_surface()

    @property
    def auto_size_rect(self): return self._auto_size_rect
    @auto_size_rect.setter
    def auto_size_rect(self, value: bool):
        if self._auto_size_rect != value:
            self._auto_size_rect = value
            self._update_font_and_text_surface() # Re-evaluate sizing

    # The old set_text method is replaced by the 'text' property setter.

    def update(self, dt):
        if not self.visible: # Use property from UIElement
            return
        
        # If rect was changed externally, ensure _text_rect is re-centered.
        # UIElement.rect setter calls mark_dirty.
        # _update_font_and_text_surface also calls mark_dirty.
        # This check is mainly for the Pygame-side rendering (_text_rect).
        if self._text_rect.center != self.rect.center: # Use property from UIElement
            self._text_rect.center = self.rect.center # Use property from UIElement
            # No need to mark_dirty here again, as the change to self.rect would have done it.

    def draw(self, surface_or_renderer):
        if not self.visible: # Use property from UIElement
            return
        surface_or_renderer.blit(self._text_surface, self._text_rect)
