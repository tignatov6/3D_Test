from settings import *
from meshes.mesh import Mesh


class Scene:
    def __init__(self, app):
        self.app = app
        self.quad = Mesh(self.app,'assets/Dragon_8K.obj')

    def update(self):
        pass

    def render(self):
        self.quad.render()











































