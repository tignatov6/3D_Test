import uuid
from .button import Button # Assuming Button and TextLabel are in these files
from .text_label import TextLabel
# We need UIElement to check for element.dirty, will be modified in next step
# from .ui_element import UIElement 

class UIManager:
    def __init__(self, renderer_instance):
        self.renderer = renderer_instance
        self.elements = [] # Keep as list for ordered iteration if needed (e.g. handle_event)
        self.elements_map = {} # For quick lookup by ID
        self.dirty_elements = set() # IDs of elements needing C++ sync

    def add_element(self, element):
        if not hasattr(element, 'id') or element.id is None:
            element.id = str(uuid.uuid4())
        
        if element.id in self.elements_map:
            print(f"Warning: Element with ID {element.id} already exists. Replacing.")
            # Remove old element if replacing by ID
            self.elements = [el for el in self.elements if el.id != element.id]

        self.elements.append(element)
        self.elements_map[element.id] = element
        self.dirty_elements.add(element.id) # Mark new elements as dirty for initial sync
        
        # Optional: sort elements by some criteria, e.g., draw order/layer
        # self.elements.sort(key=lambda x: x.layer if hasattr(x, 'layer') else 0)

    def remove_element(self, element_id_or_instance):
        element_id_to_remove = None
        if hasattr(element_id_or_instance, 'id'): # it's an instance
            element_id_to_remove = element_id_or_instance.id
        else: # it's an id
            element_id_to_remove = element_id_or_instance

        if element_id_to_remove and element_id_to_remove in self.elements_map:
            del self.elements_map[element_id_to_remove]
            self.elements = [el for el in self.elements if el.id != element_id_to_remove]
            
            if self.renderer: # Check if renderer is available
                self.renderer.remove_ui_element(element_id_to_remove)
            
            self.dirty_elements.discard(element_id_to_remove) # Remove from dirty set if present
        else:
            print(f"Warning: Element with ID {element_id_to_remove} not found for removal.")


    def handle_event(self, event):
        # Iterate in reverse for pop-up like behavior (top elements get events first)
        # and to allow elements to consume events.
        # This order is important for event handling.
        for element in reversed(self.elements): 
            if element.visible:
                event_handled = element.handle_event(event)
                if event_handled: # Optional: if an element handles an event, stop propagation
                    break 

    def update(self, dt):
        for element in self.elements: # Iterate in original order for updates
            if element.visible:
                element.update(dt)
                # Check for dirty flag (to be added to UIElement class)
                if hasattr(element, 'dirty') and element.dirty:
                    self.dirty_elements.add(element.id)
                    element.dirty = False # Reset flag after adding to manager's dirty set

    def mark_element_dirty(self, element_id: str):
        """Allows elements to notify the manager that they are dirty."""
        if element_id in self.elements_map:
            self.dirty_elements.add(element_id)
        else:
            print(f"Warning: Attempted to mark non-existent element {element_id} as dirty.")
            
    def set_element_visibility(self, element_id: str, visible: bool):
        """Sets visibility and marks the element as dirty for C++ sync."""
        if element_id in self.elements_map:
            element = self.elements_map[element_id]
            if element.visible != visible:
                element.visible = visible
                self.dirty_elements.add(element.id) 
                # The sync_dirty_elements_to_cpp will send the full element data,
                # which includes visibility.
                # If a specific set_ui_element_visibility_cpp was preferred for *only* visibility changes,
                # one might call self.renderer.set_ui_element_visibility(element_id, visible) here
                # and potentially *not* add to dirty_elements if that C++ call is immediate.
                # However, current C++ API for create_or_update_* includes visibility.
        else:
            print(f"Warning: Element {element_id} not found for set_element_visibility.")


    def sync_dirty_elements_to_cpp(self):
        """
        Synchronizes properties of dirty UI elements to the C++ renderer.
        """
        if not self.renderer:
            # print("UIManager: No renderer attached, cannot sync UI to C++.")
            return

        if not self.dirty_elements:
            return

        for element_id in list(self.dirty_elements): # Iterate a copy as elements might get re-added if errors
            element = self.elements_map.get(element_id)
            if not element:
                # print(f"Warning: Element {element_id} marked dirty but not found in elements_map.")
                continue

            try:
                if isinstance(element, Button):
                    # Use get_effective_background_color for buttons
                    effective_bg_color = element.get_effective_background_color()
                    self.renderer.create_or_update_button(
                        element_id=element.id,
                        rect=element.rect,
                        text=element.text,
                        bg_color=effective_bg_color, # Use the effective color
                        text_color=element.text_color,
                        border_color=element.border_color,
                        border_width=element.border_width,
                        visible=element.visible,
                        font_size=element.font_size # Pass font_size for Button
                    )
                elif isinstance(element, TextLabel):
                    self.renderer.create_or_update_text_label(
                        element_id=element.id,
                        rect=element.rect,
                        text=element.text,
                        text_color=element.text_color,
                        font_size=element.font_size, # Python side uses this name
                        visible=element.visible
                    )
                # Add other element types here if necessary
                else:
                    # Fallback for generic UIElement or unknown types,
                    # potentially just updating visibility if that's the only common C++ function.
                    # For now, only Buttons and TextLabels are explicitly handled.
                    # If a set_ui_element_visibility was the only common call:
                    # self.renderer.set_ui_element_visibility(element.id, element.visible)
                    pass
            except Exception as e:
                print(f"Error syncing element {element_id} to C++: {e}")
                # Optionally, re-add to dirty_elements if it was a transient error
                # self.dirty_elements.add(element_id) 
                # For now, we assume it's processed or error is logged.

        self.dirty_elements.clear()


    def draw_pygame(self, surface):
        """
        Draws all visible UI elements onto a given Pygame surface.
        This is for the Pygame (Python) rendering side.
        """
        for element in self.elements:
            if element.visible:
                element.draw(surface)
