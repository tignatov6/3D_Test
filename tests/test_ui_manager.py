import unittest
from unittest.mock import Mock, ANY # ANY for some arguments
import pygame # For pygame.Rect
from ui.ui_manager import UIManager
from ui.button import Button
from ui.text_label import TextLabel
from ui.ui_element import UIElement # For type checking or direct use if needed

class TestUIManager(unittest.TestCase):
    def setUp(self):
        self.mock_renderer = Mock()
        self.ui_manager = UIManager(renderer_instance=self.mock_renderer)

    def test_add_element(self):
        button_rect = pygame.Rect(0, 0, 100, 30)
        button = Button(rect=button_rect, text="Test")
        
        # Element should be dirty upon creation by default (UIElement.__init__)
        self.assertTrue(button.dirty) 
        
        self.ui_manager.add_element(button)
        
        self.assertIn(button.id, self.ui_manager.elements_map)
        self.assertIn(button, self.ui_manager.elements)
        self.assertIn(button.id, self.ui_manager.dirty_elements) # add_element also marks dirty

    def test_remove_element_by_instance(self):
        button = Button(rect=pygame.Rect(0,0,10,10), text="B")
        self.ui_manager.add_element(button)
        button_id = button.id
        self.ui_manager.dirty_elements.clear() # Clear dirty set for this test part

        self.ui_manager.remove_element(button)
        
        self.assertNotIn(button_id, self.ui_manager.elements_map)
        self.assertNotIn(button, self.ui_manager.elements)
        self.mock_renderer.remove_ui_element.assert_called_once_with(button_id)
        self.assertNotIn(button_id, self.ui_manager.dirty_elements)

    def test_remove_element_by_id(self):
        button = Button(rect=pygame.Rect(0,0,10,10), text="B")
        self.ui_manager.add_element(button)
        button_id = button.id
        self.ui_manager.dirty_elements.clear()

        self.ui_manager.remove_element(button_id)

        self.assertNotIn(button_id, self.ui_manager.elements_map)
        self.assertNotIn(button, self.ui_manager.elements) # Also check list
        self.mock_renderer.remove_ui_element.assert_called_once_with(button_id)
        self.assertNotIn(button_id, self.ui_manager.dirty_elements)

    def test_sync_dirty_elements(self):
        button_rect = pygame.Rect(0, 0, 100, 30)
        button = Button(rect=button_rect, text="Test Button", 
                        background_color=(10,10,10), text_color=(20,20,20),
                        border_color=(30,30,30), border_width=1, font_size=18)
        
        self.ui_manager.add_element(button)
        self.assertIn(button.id, self.ui_manager.dirty_elements)

        # First sync
        self.ui_manager.sync_dirty_elements_to_cpp()
        self.mock_renderer.create_or_update_button.assert_called_once_with(
            element_id=button.id,
            rect=button.rect,
            text=button.text,
            bg_color=button.get_effective_background_color(),
            text_color=button.text_color,
            border_color=button.border_color,
            border_width=button.border_width,
            visible=button.visible
            # font_size implicitly passed if it's part of Button's attributes now
            # and renderer wrapper expects it. Assuming current Button does not pass font_size yet.
        )
        self.assertEqual(len(self.ui_manager.dirty_elements), 0, "Dirty elements should be empty after sync.")

        # Modify button to make it dirty again
        self.mock_renderer.create_or_update_button.reset_mock()
        button.text = "New Text" # This should use the property setter and call mark_dirty()
        
        # UIManager's update loop is what normally moves element.dirty to manager.dirty_elements
        # So, we call it here to simulate that part of the game loop.
        self.ui_manager.update(dt=0.1) # dt value doesn't matter for this test
        
        self.assertIn(button.id, self.ui_manager.dirty_elements, "Button should be dirty after text change and UI manager update.")

        # Second sync
        self.ui_manager.sync_dirty_elements_to_cpp()
        self.mock_renderer.create_or_update_button.assert_called_once_with(
            element_id=button.id,
            rect=button.rect,
            text="New Text", # Check new text
            bg_color=button.get_effective_background_color(),
            text_color=button.text_color,
            border_color=button.border_color,
            border_width=button.border_width,
            visible=button.visible
        )
        self.assertEqual(len(self.ui_manager.dirty_elements), 0)
        
    def test_sync_text_label(self):
        label = TextLabel(rect=pygame.Rect(10,10,50,20), text="Info", font_size=22)
        self.ui_manager.add_element(label)
        
        self.ui_manager.sync_dirty_elements_to_cpp()
        self.mock_renderer.create_or_update_text_label.assert_called_once_with(
            element_id=label.id,
            rect=label.rect,
            text=label.text,
            text_color=label.text_color,
            font_size=label.font_size, # Check font_size
            visible=label.visible
        )
        self.assertEqual(len(self.ui_manager.dirty_elements), 0)


    def test_set_element_visibility(self):
        button = Button(rect=pygame.Rect(0,0,10,10), text="VisButton")
        self.ui_manager.add_element(button)
        self.assertTrue(button.visible)
        self.ui_manager.dirty_elements.clear() # Clear after add

        self.ui_manager.set_element_visibility(button.id, False)
        self.assertFalse(button.visible)
        self.assertIn(button.id, self.ui_manager.dirty_elements)

        self.ui_manager.sync_dirty_elements_to_cpp()
        self.mock_renderer.create_or_update_button.assert_called_with(
            element_id=button.id,
            rect=ANY, text=ANY, bg_color=ANY, text_color=ANY, 
            border_color=ANY, border_width=ANY, 
            visible=False # Check that visibility is now false
        )
        self.assertEqual(len(self.ui_manager.dirty_elements), 0)

        # Test setting it back to True
        self.mock_renderer.create_or_update_button.reset_mock()
        self.ui_manager.set_element_visibility(button.id, True)
        self.assertTrue(button.visible)
        self.assertIn(button.id, self.ui_manager.dirty_elements)
        self.ui_manager.sync_dirty_elements_to_cpp()
        self.mock_renderer.create_or_update_button.assert_called_with(
            element_id=button.id,
            rect=ANY, text=ANY, bg_color=ANY, text_color=ANY, 
            border_color=ANY, border_width=ANY, 
            visible=True # Check that visibility is now true
        )
        self.assertEqual(len(self.ui_manager.dirty_elements), 0)


if __name__ == '__main__':
    unittest.main()
