import glm
import math
from settings import *
from classes.EasyPygame import *
import pygame as pg
from scene import Scene
from player import Player
from utils.renderer import *

class Engine:
    def __init__(self,size=glm.vec2(1280,720),fullscreen=False,color=glm.vec3(0,0,0)):
        pygame.init()
        self.color = color
        if fullscreen:
            self.window = pygame.display.set_mode(size,pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode(size)
        self.clock = pygame.time.Clock()
        self.delta_time = 0
        self.time = 0
        

        pg.event.set_grab(True)
        pg.mouse.set_visible(False)

        self.is_running = True
        self.on_init()

    def on_init(self):
        self.player = Player(self)
        self.scene = Scene(self)
        self.renderer = Renderer(self)
        self.projection_matrix = self.create_projection_matrix()
        
    def create_projection_matrix(self):
        return glm.perspective(glm.radians(FOV_DEG), ASPECT_RATIO, NEAR, FAR)



    def update(self):
        self.player.update()
        self.scene.update()

        self.delta_time = self.clock.tick()
        self.time = pg.time.get_ticks() * 0.001
        pg.display.set_caption(f'{self.clock.get_fps() :.0f}')

    def render(self):
        self.window.fill(self.color)
        self.renderer.render()
        self.scene.render()
        pg.display.flip()

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                self.is_running = False

    def run(self):
        while self.is_running:
            self.handle_events()
            self.update()
            self.render()
        pg.quit()
        sys.exit()

if __name__ == '__main__':
    app = Engine()
    app.run()