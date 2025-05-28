import pygame
from .ui_element import UIElement

class Button(UIElement):
    def __init__(self, rect: pygame.Rect, text: str, 
                 font_name: str = None, font_size: int = 24, 
                 text_color: tuple = (255, 255, 255), 
                 background_color: tuple = (100, 100, 100), 
                 hover_color: tuple = (150, 150, 150), 
                 click_color: tuple = (50, 50, 50), 
                 border_color: tuple = None, border_width: int = 0, 
                 visible: bool = True, parent=None, id: str = None,
                 on_click=None, on_hover_enter=None, on_hover_exit=None):
        super().__init__(rect, visible, parent, id)
        
        self._text = text
        self._font_name = font_name
        self._font_size = font_size
        self._text_color = text_color
        self._background_color = background_color
        self._hover_color = hover_color
        self._click_color = click_color
        self._border_color = border_color
        self._border_width = border_width

        self._is_hovered = False
        self._is_clicked = False

        self.on_click = on_click
        self.on_hover_enter = on_hover_enter
        self.on_hover_exit = on_hover_exit
        
        self._update_font_and_text_surface()

    def _update_font_and_text_surface(self):
        # This method is called when text-related properties change
        try:
            self._font = pygame.font.Font(self._font_name, self._font_size)
        except pygame.error as e:
            print(f"Warning: Could not load font '{self._font_name}' at size {self._font_size}. Using default. Error: {e}")
            self._font = pygame.font.Font(None, self._font_size) # Pygame default font
            
        self._text_surface = self._font.render(self._text, True, self._text_color)
        self._text_rect = self._text_surface.get_rect(center=self.rect.center)
        self.mark_dirty() # Text surface change means visual change

    # Properties for attributes that affect visual representation
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
    def background_color(self): return self._background_color
    @background_color.setter
    def background_color(self, value):
        if self._background_color != value:
            self._background_color = value
            self.mark_dirty()

    @property
    def hover_color(self): return self._hover_color
    @hover_color.setter
    def hover_color(self, value):
        if self._hover_color != value:
            self._hover_color = value
            # No direct mark_dirty() here, hover state change will trigger it
            
    @property
    def click_color(self): return self._click_color
    @click_color.setter
    def click_color(self, value):
        if self._click_color != value:
            self._click_color = value
            # No direct mark_dirty() here, click state change will trigger it

    @property
    def border_color(self): return self._border_color
    @border_color.setter
    def border_color(self, value):
        if self._border_color != value:
            self._border_color = value
            self.mark_dirty()

    @property
    def border_width(self): return self._border_width
    @border_width.setter
    def border_width(self, value):
        if self._border_width != value:
            self._border_width = value
            self.mark_dirty()

    @property
    def is_hovered(self): return self._is_hovered
    @is_hovered.setter
    def is_hovered(self, value):
        if self._is_hovered != value:
            self._is_hovered = value
            self.mark_dirty() # Hover state change affects appearance

    @property
    def is_clicked(self): return self._is_clicked
    @is_clicked.setter
    def is_clicked(self, value):
        if self._is_clicked != value:
            self._is_clicked = value
            self.mark_dirty() # Click state change affects appearance


    def handle_event(self, event_data: dict):
        if not self.visible: # Use property
            return False # Event not handled

        event_type = event_data.get('type')
        event_handled = False

        if event_type == 'MOUSEMOTION':
            mouse_x = event_data.get('x')
            mouse_y = event_data.get('y')

            if mouse_x is None or mouse_y is None:
                return False # Not enough data

            currently_colliding = self.rect.collidepoint(mouse_x, mouse_y) # Use property for rect

            if currently_colliding:
                if not self.is_hovered: # Use property
                    self.is_hovered = True # Setter calls mark_dirty
                    if self.on_hover_enter:
                        self.on_hover_enter(self)
                    event_handled = True 
            else: # Not colliding
                if self.is_hovered: # Use property
                    self.is_hovered = False # Setter calls mark_dirty
                    self.is_clicked = False # Also reset click state if mouse leaves while pressed
                                           # Setter for is_clicked also calls mark_dirty
                    if self.on_hover_exit:
                        self.on_hover_exit(self)
                    event_handled = True
        
        elif event_type == 'MOUSEBUTTONDOWN':
            button_id = event_data.get('button')
            # SDL_BUTTON_LEFT is 1
            if self.is_hovered and button_id == 1: # Use property
                self.is_clicked = True # Setter calls mark_dirty
                event_handled = True
        
        elif event_type == 'MOUSEBUTTONUP':
            button_id = event_data.get('button')
            # SDL_BUTTON_LEFT is 1
            if button_id == 1:
                # Store states before changing them, especially is_clicked
                was_clicked_on_element = self.is_clicked and self.is_hovered # Use properties

                # Always set is_clicked to False on MOUSEBUTTONUP for the left button
                # This will trigger mark_dirty via the property setter if the state changes.
                if self.is_clicked: # Only change if it was true, to ensure mark_dirty is called.
                    self.is_clicked = False
                else: 
                    # If it wasn't clicked, but we still need to ensure a redraw for potential
                    # hover state changes if the mouse up happened without a prior click on this button.
                    # This scenario is less common for button logic itself but ensures consistency.
                    self.mark_dirty()


                if was_clicked_on_element:
                    if self.on_click:
                        self.on_click(self)
                
                event_handled = True # Consumed the MOUSEBUTTONUP event for the left button

        return event_handled


    def update(self, dt):
        if not self.visible: # Use property
            return
        # Update text rect if button rect changes (e.g. by parent or self.rect setter)
        # self.rect is a property, its setter calls mark_dirty.
        # If _text_rect needs update due to self.rect changing, it should happen here or in _update_font_and_text_surface
        # Let's ensure _text_rect is updated if self.rect changes.
        # The UIElement's rect setter already calls mark_dirty.
        # _update_font_and_text_surface also calls mark_dirty.
        # We need to ensure _text_rect is correctly positioned if self.rect changes.
        current_center = self._text_rect.center
        if current_center != self.rect.center: # Use property for rect
            self._text_rect.center = self.rect.center # Use property for rect
            # This local Pygame surface positioning doesn't need to mark dirty,
            # as the overall rect (synced to C++) defines the button's space.
            # C++ side will handle its own text centering.

    def get_effective_background_color(self) -> tuple:
        """Returns the background color based on the current state (hover, click)."""
        if self.is_clicked and self._click_color:
            return self._click_color
        elif self.is_hovered and self._hover_color:
            return self._hover_color
        return self._background_color

    def draw(self, surface_or_renderer):
        if not self.visible: # Use property
            return

        current_bg_color = self.get_effective_background_color()
        
        pygame.draw.rect(surface_or_renderer, current_bg_color, self.rect) # Use property

        if self._border_color and self._border_width > 0: # Use internal vars for drawing properties
            pygame.draw.rect(surface_or_renderer, self._border_color, self.rect, self._border_width) # Use property
        
        surface_or_renderer.blit(self._text_surface, self._text_rect)
