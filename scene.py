from settings import *
import pygame as pg
from classes.GameObject import GameObject


class Scene:
    def __init__(self, app):
        self.app = app
        self.objs =[]
        self.map = GameObject(self.app,'assets/de_dust2_2.obj')
        #for i in range(10):
        #    self.objs.append(GameObject(self.app,'assets/cube2.obj'))
        #    self.objs.append(GameObject(self.app,'assets/pawn.obj'))
        #self.quad1 = Mesh(self.app,'assets/de_dust2.obj')

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