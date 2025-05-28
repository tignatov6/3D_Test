import unittest
from unittest.mock import Mock
import pygame # For pygame.Rect and possibly other constants if needed
from ui.button import Button # Adjust import path as necessary

# Helper to create event dictionaries similar to what SDL wrapper might produce
def create_event_dict(event_type_str, **kwargs):
    event_data = {'type': event_type_str}
    event_data.update(kwargs)
    return event_data

class TestUIButtonStates(unittest.TestCase):
    def setUp(self):
        self.button_rect = pygame.Rect(10, 10, 100, 30)
        self.button = Button(rect=self.button_rect, text="Test Button")

    def test_button_initial_state(self):
        self.assertFalse(self.button.is_hovered, "Button should not be hovered initially.")
        self.assertFalse(self.button.is_clicked, "Button should not be clicked initially.")
        self.assertTrue(self.button.visible, "Button should be visible initially.")
        self.assertTrue(self.button.dirty, "Button should be dirty initially for first sync.")
        self.button.dirty = False # Reset for next tests

    def test_button_hover_state(self):
        # Simulate MOUSEMOTION inside the button
        event_inside = create_event_dict('MOUSEMOTION', x=self.button_rect.centerx, y=self.button_rect.centery)
        self.button.handle_event(event_inside)
        self.assertTrue(self.button.is_hovered, "Button should be hovered when mouse is inside.")
        self.assertTrue(self.button.dirty, "Button should be dirty after hover state change.")
        self.button.dirty = False

        # Simulate MOUSEMOTION outside the button
        event_outside = create_event_dict('MOUSEMOTION', x=self.button_rect.right + 10, y=self.button_rect.bottom + 10)
        self.button.handle_event(event_outside)
        self.assertFalse(self.button.is_hovered, "Button should not be hovered when mouse is outside.")
        self.assertTrue(self.button.dirty, "Button should be dirty after hover state change.")
        self.button.dirty = False # Reset

        # Simulate mouse leaving while clicked (is_clicked should also become false)
        self.button.is_hovered = True # Force hover
        self.button.is_clicked = True # Force click
        self.button.dirty = False 
        self.button.handle_event(event_outside) # Mouse moves out
        self.assertFalse(self.button.is_hovered, "Button should not be hovered after mouse leaves.")
        self.assertFalse(self.button.is_clicked, "Button should not be clicked after mouse leaves while pressed.")
        self.assertTrue(self.button.dirty)


    def test_button_click_state(self):
        # 1. Hover over button
        event_hover = create_event_dict('MOUSEMOTION', x=self.button_rect.centerx, y=self.button_rect.centery)
        self.button.handle_event(event_hover)
        self.assertTrue(self.button.is_hovered)
        self.button.dirty = False

        # 2. Press mouse button down on the button
        event_down = create_event_dict('MOUSEBUTTONDOWN', button=1, x=self.button_rect.centerx, y=self.button_rect.centery)
        self.button.handle_event(event_down)
        self.assertTrue(self.button.is_clicked, "Button should be clicked after MOUSEBUTTONDOWN while hovered.")
        self.assertTrue(self.button.dirty)
        self.button.dirty = False

        # 3. Release mouse button up on the button
        event_up = create_event_dict('MOUSEBUTTONUP', button=1, x=self.button_rect.centerx, y=self.button_rect.centery)
        self.button.handle_event(event_up)
        self.assertFalse(self.button.is_clicked, "Button should not be clicked after MOUSEBUTTONUP.")
        self.assertTrue(self.button.dirty) # is_clicked changed
        self.button.dirty = False

        # Test clicking outside (should not register as a button click)
        self.button.is_hovered = False # Ensure not hovered
        self.button.is_clicked = False # Reset click state
        self.button.dirty = False
        
        event_down_outside = create_event_dict('MOUSEBUTTONDOWN', button=1, x=self.button_rect.right + 10, y=self.button_rect.bottom + 10)
        self.button.handle_event(event_down_outside)
        self.assertFalse(self.button.is_clicked, "Button should not be clicked if MOUSEBUTTONDOWN is outside.")
        self.assertFalse(self.button.dirty) # State should not have changed


class TestUIButtonCallbacks(unittest.TestCase):
    def setUp(self):
        self.button_rect = pygame.Rect(10, 10, 100, 30)
        self.mock_on_click = Mock()
        self.mock_on_hover_enter = Mock()
        self.mock_on_hover_exit = Mock()
        
        self.button = Button(
            rect=self.button_rect, 
            text="Callback Button",
            on_click=self.mock_on_click,
            on_hover_enter=self.mock_on_hover_enter,
            on_hover_exit=self.mock_on_hover_exit
        )

    def test_button_on_click_callback(self):
        # Simulate hover
        event_hover = create_event_dict('MOUSEMOTION', x=self.button_rect.centerx, y=self.button_rect.centery)
        self.button.handle_event(event_hover)
        
        # Simulate click
        event_down = create_event_dict('MOUSEBUTTONDOWN', button=1, x=self.button_rect.centerx, y=self.button_rect.centery)
        self.button.handle_event(event_down)
        
        event_up = create_event_dict('MOUSEBUTTONUP', button=1, x=self.button_rect.centerx, y=self.button_rect.centery)
        self.button.handle_event(event_up)
        
        self.mock_on_click.assert_called_once_with(self.button)

    def test_button_on_click_callback_not_called_if_mouse_moves_off(self):
        # Simulate hover
        event_hover = create_event_dict('MOUSEMOTION', x=self.button_rect.centerx, y=self.button_rect.centery)
        self.button.handle_event(event_hover)
        
        # Simulate mousedown
        event_down = create_event_dict('MOUSEBUTTONDOWN', button=1, x=self.button_rect.centerx, y=self.button_rect.centery)
        self.button.handle_event(event_down)
        self.assertTrue(self.button.is_clicked)

        # Simulate mouse moving off the button before mouseup
        event_move_off = create_event_dict('MOUSEMOTION', x=self.button_rect.right + 10, y=self.button_rect.centery)
        self.button.handle_event(event_move_off)
        self.assertFalse(self.button.is_hovered)
        self.assertFalse(self.button.is_clicked) # Click should be cancelled

        # Simulate mouseup (now outside the button)
        event_up_outside = create_event_dict('MOUSEBUTTONUP', button=1, x=self.button_rect.right + 10, y=self.button_rect.centery)
        self.button.handle_event(event_up_outside)
        
        self.mock_on_click.assert_not_called()


    def test_button_hover_callbacks(self):
        # Mouse enters
        event_enter = create_event_dict('MOUSEMOTION', x=self.button_rect.centerx, y=self.button_rect.centery)
        self.button.handle_event(event_enter)
        self.mock_on_hover_enter.assert_called_once_with(self.button)
        self.mock_on_hover_exit.assert_not_called()
        self.mock_on_hover_enter.reset_mock() # Reset for next check

        # Mouse moves within the button (should not re-trigger enter)
        event_move_inside = create_event_dict('MOUSEMOTION', x=self.button_rect.centerx + 1, y=self.button_rect.centery)
        self.button.handle_event(event_move_inside)
        self.mock_on_hover_enter.assert_not_called()
        self.mock_on_hover_exit.assert_not_called()

        # Mouse exits
        event_exit = create_event_dict('MOUSEMOTION', x=self.button_rect.right + 10, y=self.button_rect.centery)
        self.button.handle_event(event_exit)
        self.mock_on_hover_exit.assert_called_once_with(self.button)
        self.mock_on_hover_enter.assert_not_called() # Ensure enter wasn't called again
        self.mock_on_hover_exit.reset_mock()

        # Mouse moves outside (should not re-trigger exit)
        event_move_outside = create_event_dict('MOUSEMOTION', x=self.button_rect.right + 20, y=self.button_rect.centery)
        self.button.handle_event(event_move_outside)
        self.mock_on_hover_exit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
