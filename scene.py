from settings import *
import pygame as pg
from classes.GameObject import GameObject
from ui import Button, TextLabel
import random


class Scene:
    def __init__(self, app):
        self.app = app
        self.objs =[]
        self.map = GameObject(self.app,'assets/de_dust2_2.obj')
        #for i in range(10):
        #    self.objs.append(GameObject(self.app,'assets/cube2.obj'))
        #    self.objs.append(GameObject(self.app,'assets/pawn.obj'))
        #self.quad1 = Mesh(self.app,'assets/de_dust2.obj')
        self.init_ui()

    def init_ui(self):
        # --- Add UI Example Elements ---
        # Define the callback function for the button
        def example_button_on_click(button_instance):
            print(f"Button '{button_instance.text}' clicked!")
            if hasattr(self, 'info_label') and self.info_label:
                # The TextLabel's text property setter should automatically call mark_dirty()
                self.info_label.text = "Button was clicked!" 
            else:
                print("Info label not found on engine instance.")

        # Create a TextLabel
        self.info_label = TextLabel(
            rect=pg.Rect(50, 50, 300, 40), # x, y, width, height
            text="Hello, UI World!",
            text_color=(200, 200, 200), # Light gray
            font_size=20, # This font size is passed to C++, but current C++ impl. uses one default font size
            auto_size_rect=False # If True, rect width/height might be adjusted by text content
        )
        self.app.ui_manager.add_element(self.info_label)

        # Create a Button
        self.example_button = Button(
            rect=pg.Rect(50, 100, 200, 50), # x, y, width, height
            text="Click Me!",
            background_color=(0, 100, 200),    # Blue
            hover_color=(0, 150, 255),       # Lighter blue
            click_color=(0, 50, 150),        # Darker blue
            text_color=(255, 255, 255),      # White text
            border_color=(255, 255, 255),    # White border
            border_width=2,
            on_click=example_button_on_click # Assign the callback
        )
        self.app.ui_manager.add_element(self.example_button)

    def update(self):
        pass
        
        #for obj in self.objs:
        #    obj.position.z += 0.001
        #    obj.scale.xyz += 0.0001
        #    obj.rotation.xyz += 0.1
        #if self.app.pressed_keys[pg.K_r]:
            #self.obj.position.z += 0.0001

    def render(self):
        self.map.render()
        #for obj in self.objs:
        #    obj.render()
        #self.quad1.render()