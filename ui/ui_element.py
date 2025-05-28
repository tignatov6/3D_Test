import uuid
import pygame

class UIElement:
    def __init__(self, rect: pygame.Rect, visible: bool = True, parent=None, id: str = None):
        self._id = id if id else str(uuid.uuid4())
        self._rect = rect
        self._visible = visible
        self.parent = parent # Could be another UIElement or the UIManager
        self.dirty = True # Mark dirty on creation for initial sync

    @property
    def id(self):
        return self._id

    # No setter for id, it should be immutable after creation or managed carefully

    @property
    def rect(self):
        return self._rect

    @rect.setter
    def rect(self, value: pygame.Rect):
        if self._rect != value:
            self._rect = value
            self.mark_dirty()

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value: bool):
        if self._visible != value:
            self._visible = value
            self.mark_dirty()

    def mark_dirty(self):
        self.dirty = True
        # If a direct link to UIManager and its notify method was desired:
        # if self.parent and hasattr(self.parent, 'mark_element_dirty'):
        #     self.parent.mark_element_dirty(self.id)
        # But current UIManager design iterates and checks self.dirty flag.

    def handle_event(self, event):
        # To be implemented by subclasses
        pass

    def update(self, dt):
        # To be implemented by subclasses
        pass

    def draw(self, surface_or_renderer):
        # To be implemented by subclasses for Pygame-side drawing if needed
        pass
