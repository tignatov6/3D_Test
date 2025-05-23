import pygame
from math import inf
import time
import sys
from pygame.math import Vector2, Vector3
from utils.obj_parser import *

pygame.init()
try:
	pygame.mixer.init()
except:
	pass
pi = 3.1415926535

# После импортов
try:
	if not pygame.get_init():
		raise RuntimeError("Pygame не инициализирован!")
except:
	pass

# Проверка инициализации дисплея
if not pygame.display.get_init():
	pygame.display.init()

def get_font(size): # Returns Press-Start-2P in the desired size
	try:
		return pygame.font.Font("data/fonts/font.ttf", size)
	except:
		return pygame.font.Font("font.png", size)

def calculate_v1(u1: Vector2, u2: Vector2, m1: float, m2: float, 
				e1: float, e2: float, normal: Vector2) -> Vector2:
	"""
	Рассчитывает скорость первого тела после столкновения (2D случай).
	
	Параметры:
	u1, u2 (Vector2): скорости тел до столкновения
	m1, m2 (float): массы тел
	e1, e2 (float): коэффициенты восстановления
	normal (Vector2): нормаль к поверхности столкновения (должна быть нормализована)
	
	Возвращает:
	Vector2: новая скорость первого тела
	"""
	# Рассчитываем относительную скорость вдоль нормали
	v_rel = (u1 - u2).dot(normal)
	
	# Коэффициент восстановления
	e = min(e1, e2)
	
	# Учитываем случай с бесконечной массой (неподвижный объект)
	if m2 == float('inf'):
		return u1 - (1 + e) * v_rel * normal
	
	# Импульс удара
	j = -(1 + e) * v_rel / (1/m1 + 1/m2)
	
	# Новая скорость первого тела
	new_u1 = u1 + (j * normal) / m1
	return new_u1


class Vector2():
	def __init__(self,x=0,y=0):
		self.x = x
		self.y = y

	def __add__(self, arg):
		if isinstance(arg, Vector2):
			return Vector2(self.x + arg.x, self.y + arg.y)
		else:
			return Vector2(self.x + arg, self.y + arg)

	def __sub__(self, arg):
		if isinstance(arg, Vector2):
			return Vector2(self.x - arg.x, self.y - arg.y)
		else:
			return Vector2(self.x - arg, self.y - arg)

	def __mul__(self, arg):
		if isinstance(arg, Vector2):
			return Vector2(self.x * arg.x, self.y * arg.y)
		else:
			return Vector2(self.x * arg, self.y * arg)

	def __rmul__(self, arg):
		return self.__mul__(arg)

	def __pow__(self, arg):
		if isinstance(arg, Vector2):
			return Vector2(self.x ** arg.x, self.y ** arg.y)
		else:
			return Vector2(self.x ** arg, self.y ** arg)


	def __truediv__(self, arg):
		if isinstance(arg, Vector2):
			return Vector2(self.x / arg.x, self.y / arg.y)
		else:
			return Vector2(self.x / arg, self.y / arg)


	def __str__(self):
		return f"{self.x}, {self.y}"
	
	def len(self):
		c = self.x **2 + self.y **2
		c = c**0.5
		return float(c)

	def __abs__(self):
		return Vector2(abs(self.x),abs(self.y))


	def distance(self,b):
		c = abs(self - b)
		return (c.x**2 + c.y**2) ** 0.5

	def normalize(self):
		_len = self.len()
		return Vector2(self.x/_len,self.y/_len)

	def dot(self, other: 'Vector2') -> float:
		"""Скалярное произведение векторов"""
		return self.x * other.x + self.y * other.y
	
class EasyGame():
	def __init__(self, size=(256,256),color=(0,0,0),cameraPosition=Vector2(0,0), cameraScale = Vector2(1,1),fullscreen=False):
		self.size = size
		self.color = color
		if fullscreen:
			self.window = pygame.display.set_mode(size,pygame.FULLSCREEN)
		else:
			self.window = pygame.display.set_mode(size)
		self.gameObjects = []
		self.events = None
		self.keysPressed = None
		try:
			self.prev_time = time.perf_counter()
		except:
			self.prev_time = time.time()
		self.current_time = 0
		self.delta_time = 0
		self.prev_time = 0
		self.physicsGameObjects = []
		self.started = False
		self.cameraPosition = (cameraPosition +Vector2( size[0]/2, size[1]/2))
		self.cameraScale = cameraScale
		self.MOUSE_POS = None
		self.MOUSEBUTTONDOWN = None
		self.UIs = []
		self.buttons = []
		self.InputBoxes = []

	def Render(self):
		self.window.fill(self.color)

		for gameObject in self.gameObjects:
			if gameObject.active == True and gameObject.visible == True:
				gameObject.blit()

		for InputBox in self.InputBoxes:
			InputBox.update()

		for button in self.buttons:
			#button.checkForInput(self.MOUSE_POS)
			pass

		for UI in self.UIs:
			UI.blit()
		
			
	def processEvents(self):
		self.MOUSE_POS = pygame.mouse.get_pos()
		if self.started == False:
			try:
				self.prev_time = time.perf_counter()
			except:
				self.prev_time = time.time()
			self.started = True
		self.events = pygame.event.get()
		self.keysPressed = pygame.key.get_pressed()
		try:
			self.current_time = time.perf_counter()
		except:
			self.current_time = time.time()
		self.delta_time = self.current_time - self.prev_time
		self.prev_time = self.current_time
		quit = True
		self.MOUSEBUTTONDOWN = False
		for e in self.events:
			if e.type == pygame.QUIT:
				quit = False
			if e.type == pygame.MOUSEBUTTONDOWN:
				self.MOUSEBUTTONDOWN = True
			for InputBox in self.InputBoxes:
				InputBox.handle_event(e)
		return quit

	def CheckEvent(self,pygameEvent):
		for e in self.events:
			if e.type == pygameEvent:
				return True
		return False
	
	def CheckEvents(self,pygameEvents,ReturnOneBool = True):
		"""
		Might be broken if ReturnOneBool = False
		"""
	

		if not ReturnOneBool:
			foundEvents = []
		for e in self.events:
			for pygameEvent in pygameEvents:
				if e.type == pygameEvent:
					if ReturnOneBool:
						return True
					else:
						foundEvents.append[True]
			if not ReturnOneBool:
				foundEvents.append[False]
		if ReturnOneBool:
			return False
		else:
			return foundEvents
		
				
	def GetKeyState(self,key):
		if self.keysPressed[key]:
			return True
		else:
			return False


	def UpdatePhysics(self):
		for gameObject in self.physicsGameObjects:
			if gameObject.active == True:
				gameObject.UpdatePhysics()

	def SetCameraPosition(self, NewCameraPosition):
		try:
			self.cameraPosition = (NewCameraPosition +Vector2( self.cameraScale.x * self.size[0]/2,  self.cameraScale.y * self.size[1]/2))
		except Exception:
			e = sys.exc_info()[1]
			print(e)

	def SetCameraScale(self, NewCameraScale):
		try:
			cPos = self.cameraPosition
			self.cameraScale = NewCameraScale
			#self.SetCameraPosition(cPos)
			for gameObject in self.gameObjects:
				if gameObject.active == True:
					gameObject.ChangeScale(gameObject.scale)
		except Exception:
			e = sys.exc_info()[1]
			print(e)
			

	def PlayMusic(self,music_path,count=-1):
		"""
		Don`t write count for infinite loop
		"""
		pygame.mixer.music.load(music_path)
		pygame.mixer.music.play(count)

	def PlaySound(self,sound_path,count=0):
		"""
		Don`t write count for play once
		"""
		sound = pygame.mixer.Sound(sound_path)
		sound.play(count)

	def Update(self):
		for gameObject in self.gameObjects:
			if gameObject.active == True:
				gameObject.Update()

class Button():
	def __init__(self,EasyGame, image, pos, text_input, font, base_color, hovering_color,imageScale = Vector2()):
		try:
			if imageScale.x > 0 and imageScale.y > 0:
				self.image = pygame.transform.scale(pygame.image.load(image), (int(imageScale.x),int(imageScale.y)))
			else:
				self.image = pygame.image.load(image)
		except:
			self.image = None
		self.EasyGame = EasyGame

		self.EasyGame.UIs.append(self)
		self.EasyGame.buttons.append(self)

		self.imageScale = imageScale

		self.x_pos = pos.x
		self.y_pos = pos.y
		self.font = font
		self.base_color, self.hovering_color = base_color, hovering_color
		self.text_input = text_input
		self.text = self.font.render(self.text_input, True, self.base_color)
		if self.image is None:
			#self.image = self.text
			self.image = pygame.Surface((0, 0))  # Заглушка
			#self.image.fill((255, 0, 0))  # Красный цвет для отладки
		self.rect = self.image.get_rect(center=(int(self.x_pos), int(self.y_pos)))
		self.text_rect = self.text.get_rect(center=(self.x_pos, self.y_pos))

	def blit(self):
		if self.image is not None:
			self.EasyGame.window.blit(self.image, self.rect)
		self.EasyGame.window.blit(self.text, self.text_rect)

	def checkForInput(self, position):
		if position[0] in range(self.rect.left, self.rect.right) and position[1] in range(self.rect.top, self.rect.bottom):
			return True
		return False

	def clicked(self):
		for event in self.EasyGame.events:
			if event.type == pygame.MOUSEBUTTONDOWN:
				return self.checkForInput(self.EasyGame.MOUSE_POS)
		return False

	def changeColor(self, position):
		if position[0] in range(self.rect.left, self.rect.right) and position[1] in range(self.rect.top, self.rect.bottom):
			self.text = self.font.render(self.text_input, True, self.hovering_color)
		else:
			self.text = self.font.render(self.text_input, True, self.base_color)

	def changeText(self,newText):
		self.text_input = newText
		self.text = self.font.render(self.text_input, True, self.base_color)
		self.text_rect = self.text.get_rect(center=(self.x_pos, self.y_pos))

	def setText(self,newText):
		self.changeText(newText)


	def changeImage(self, newImage):
		try:
			# Проверяем, если указаны размеры для масштабирования
			if self.imageScale.x > 0 and self.imageScale.y > 0:
				self.image = pygame.transform.scale(pygame.image.load(newImage), (int(self.imageScale.x), int(self.imageScale.y)))
			else:
				self.image = pygame.image.load(newImage)
		except Exception as e:
			print(f"Error loading image: {e}")
			self.image = None  # Устанавливаем в None, если не удалось загрузить изображение

		# Если изображение не загружено, используем текст
		if self.image is None:
			self.image = self.text

		# Обновляем прямоугольник после изменения изображения
		self.rect = self.image.get_rect(center=(self.x_pos, self.y_pos))


	def setImage(self,newImage):
		self.changeImage(newImage)

class Lable(Button):
	def __init__(self,EasyGame, pos, text_input, font, base_color, hovering_color,image = None, imageScale = Vector2()):
		super().__init__(EasyGame, image, pos, text_input, font, base_color, hovering_color,imageScale)

class Image(Button):
	def __init__(self,EasyGame, pos,image, font=get_font(1), base_color="#d7fcd4", hovering_color="White",imageScale = Vector2(), text_input = None):
		super().__init__(EasyGame, image, pos, text_input, font, base_color, hovering_color,imageScale)

class InputBox:
	def __init__(self,EasyGame, position, scale,font,text='',COLOR_ACTIVE = pygame.Color('dodgerblue2'),COLOR_INACTIVE = pygame.Color('lightskyblue3')):
		self.position = position
		self.scale = scale
		self.rect = pygame.Rect(self.position.x, self.position.y, self.scale.x, self.scale.y)
		self.COLOR_INACTIVE = COLOR_INACTIVE
		self.COLOR_ACTIVE = COLOR_ACTIVE
		self.color = COLOR_INACTIVE
		self.text = text
		self.font = font
		self.txt_surface = self.font.render(text, True, self.color)
		self.active = False
		self.EasyGame = EasyGame

		self.EasyGame.UIs.append(self)
		self.EasyGame.InputBoxes.append(self)

	def handle_event(self, event):
		if event.type == pygame.MOUSEBUTTONDOWN:
			# If the user clicked on the input_box rect.
			if self.rect.collidepoint(event.pos):
				# Toggle the active variable.
				self.active = not self.active
			else:
				self.active = False
			# Change the current color of the input box.
			self.color = self.COLOR_ACTIVE if self.active else self.COLOR_INACTIVE
		if event.type == pygame.KEYDOWN:
			if self.active:
				if event.key == pygame.K_RETURN:
					print(self.text)
					self.text = ''
				elif event.key == pygame.K_BACKSPACE:
					self.text = self.text[:-1]
				else:
					self.text += event.unicode
				# Re-render the text.
				self.txt_surface = self.font.render(self.text, True, self.color)

	def update(self):
		# Resize the box if the text is too long.
		width = max(200, self.txt_surface.get_width()+10)
		self.rect.w = width

	def blit(self):
		# Blit the text.
		self.EasyGame.window.blit(self.txt_surface, (self.rect.x+5, self.rect.y+5))
		# Blit the rect.
		pygame.draw.rect(self.EasyGame.window, self.color, self.rect, 2)

	def getText(self):
		return self.text

	def getValue(self):
		self.getText()
			
class GameObject():
	def __init__(self,EasyGame,position=Vector2(0,0),scale=Vector2(25,25),sprite='data/textures/ball.png',radius='auto',offset=Vector2(0,0),collisionMode ='None', tag = 'None'):
		"""
		Collision modes: none / circle / box
		"""
		self.EasyGame = EasyGame
		self.window = self.EasyGame.window
		self.position = position
		self.scale = scale
		self.sprite = str(sprite)
		self.offset = offset
		self.pygameObject = pygame.transform.scale(pygame.image.load(self.sprite), (int(self.scale.x * self.EasyGame.cameraScale.x),int(self.scale.y * self.EasyGame.cameraScale.y)))
		self.active = True
		self.EasyGame.gameObjects.append(self)
		self.collisionMode = collisionMode
		self.radius = radius
		self.collided = False
		self.previousCollided = False
		self.tag = tag
		if self.collisionMode != 'circle' and radius == 'auto':
			self.radius = -1
		if radius == 'auto' and self.collisionMode == 'circle':
			self.radius = (self.scale.x + self.scale.y)/4

		self.visible = True
		

	def Update(self):
		pass
		
	def blit(self):
			if self.active == True:
				self.window.blit(self.pygameObject,((self.position.x+self.offset.x+self.EasyGame.cameraPosition.x) * self.EasyGame.cameraScale.x, (self.position.y+self.offset.y+self.EasyGame.cameraPosition.y) * self.EasyGame.cameraScale.x))
		
	def ChangeScale(self, newscale):
			self.scale = newscale
			self.pygameObject = pygame.transform.scale(pygame.image.load(self.sprite), (int(self.scale.x * self.EasyGame.cameraScale.x),int(self.scale.y * self.EasyGame.cameraScale.y)))

	def OnCollisionEnter(self,tag = 'None',collisionsThreshold = 1):
		collisions = self.CheckCollisions(tag=tag,returnOnlyCollisionsCount=True)
		self.collided = collisions > 0
		if self.collided == True and self.previousCollided == False:
			self.previousCollided = collisions > 0
			return True
		else:
			self.previousCollided = collisions > 0
			return False

	def OnCollisionExit(self,tag = 'None',collisionsThreshold = 1):
		collisions = self.CheckCollisions(tag=tag,returnOnlyCollisionsCount=True)
		self.collided = collisions > 0
		if self.collided == False and self.previousCollided == True:
			self.previousCollided = collisions > 0
			return True
		else:
			self.previousCollided = collisions > 0
			return False

	def OnCollisionStay(self,tag = 'None',collisionsThreshold = 1):
		collisions = self.CheckCollisions(tag=tag,returnOnlyCollisionsCount=True)
		self.collided = collisions > 0
		if self.collided == True:
			self.previousCollided = collisions > 0
			return True
		else:
			self.previousCollided = collisions > 0
			return False
		
	def CheckCollisions(self,returnOnlyCollisionsCount=False,tag = 'None',returnOnlyCollidedGameObjects = False):
		"""
		Return True if collide or return number of collides
		if tag = 'None' will collide with all active gameObjects
		"""

		collisions = 0
		collided = []
		for gameObject in self.EasyGame.gameObjects:
			if gameObject.active and gameObject.collisionMode != 'none':
				if gameObject != self:
					if tag == 'None' or gameObject.tag == tag:
						if gameObject.collisionMode == 'circle':
							if Vector2(self.position.x+(self.scale.x/2),self.position.y+(self.scale.y/2)).distance((gameObject.position + Vector2(gameObject.scale.x/2,gameObject.scale.y/2))) <= self.radius + gameObject.radius:
								collisions += 1
								if returnOnlyCollidedGameObjects:
									collided.append(gameObject)
								if not returnOnlyCollisionsCount:
									break 
						if gameObject.collisionMode == 'box':
							if self.position.x+(self.scale.x) >= gameObject.position.x  and self.position.x  <= gameObject.position.x  + (gameObject.scale.x) and self.position.y  <= gameObject.position.y+(gameObject.scale.y ) and self.position.y  + (self.scale.y) >= gameObject.position.y :
								collisions += 1
								if returnOnlyCollidedGameObjects:
									collided.append(gameObject)
								if not returnOnlyCollisionsCount:
									break 

		if returnOnlyCollisionsCount:
			return collisions
		if returnOnlyCollidedGameObjects:
			return collided
		return collisions > 0  


class PhysicsGameObject(GameObject):
	def __init__(self,EasyGame,position=Vector2(0,0),scale=Vector2(25,25),sprite='data/textures/ball.png',radius='auto',offset=Vector2(0,0),collisionMode ='circle', tag = 'None',gravity=Vector2(0,9.81),initialVelocity = Vector2(0,0),physicsMode = 'simpliest',mass=1,bouncy=0.1,):
		super().__init__(EasyGame,position,scale,sprite,radius,offset,collisionMode, tag)
		self.gravity = gravity
		self.velocity = initialVelocity
		self.physicsMode = physicsMode
		self.EasyGame.physicsGameObjects.append(self)
		self.bouncy = bouncy
		self.mass = mass



	def UpdatePhysics(self):
		if self.physicsMode == 'gravity':
			self.velocity += self.gravity
			self.position = self.position + self.velocity * self.EasyGame.delta_time
			pass
		if self.physicsMode == 'simpliest':
			self.velocity += self.gravity
			# self.OnCollisionStay()
			# if self.collided:
			# 	self.velocity = Vector2(0,0)
			a = self.PhysicsCollisions()
			self.position = self.position + self.velocity * self.EasyGame.delta_time

	def PhysicsCollisions(self,tag = 'None'):
		"""
		Return True if collide or return number of collides
		if tag = 'None' will collide with all active gameObjects
		"""

		collisions = 0
		collided = []
		for gameObject in self.EasyGame.gameObjects:
			if gameObject.active and gameObject.collisionMode != 'none':
				if gameObject != self:
					if tag == 'None' or gameObject.tag == tag:
						if gameObject.collisionMode == 'circle':
							if Vector2(self.position.x+(self.scale.x/2),self.position.y+(self.scale.y/2)).distance((gameObject.position + Vector2(gameObject.scale.x/2,gameObject.scale.y/2))) <= self.radius + gameObject.radius:
								a = (gameObject.position - self.position).normalize() * (self.position.distance(gameObject.position))
								self.velocity -=  a
								#print('A',a)
								# Вектор от текущего объекта к другому
								collision_vector = gameObject.position - self.position
								# Нормаль столкновения (направление от текущего объекта к другому)
								normal = collision_vector.normalize()
								try:
									b = calculate_v1(self.velocity,gameObject.velocity,self.mass,gameObject.mass,self.bouncy,gameObject.bouncy,normal)
								except:
									b = calculate_v1(self.velocity,Vector2(0,0),self.mass,inf,self.bouncy,self.bouncy,normal)

								#print('B',b)
								self.velocity = b


						if gameObject.collisionMode == 'box':
							if self.position.x+(self.scale.x) >= gameObject.position.x  and self.position.x  <= gameObject.position.x  + (gameObject.scale.x) and self.position.y  <= gameObject.position.y+(gameObject.scale.y ) and self.position.y  + (self.scale.y) >= gameObject.position.y :
								try:
									LenVel = float(self.velocity.len() + gameObject.velocity.len())
								except:
									LenVel = float(self.velocity.len())
								# Upper
								if self.position.y + self.scale.y <= gameObject.position.y or self.position.y + self.scale.y <= gameObject.position.y + gameObject.scale.y*0.01*LenVel:
									if self.velocity.y > 0:
										self.velocity.y *= -self.bouncy
									print('Upper')
								# Lower
								if self.position.y >= gameObject.position.y + gameObject.scale.y or self.position.y + self.scale.y *0.01*LenVel >= gameObject.position.y + gameObject.scale.y:
									if self.velocity.y < 0:
										self.velocity.y *= -self.bouncy
									print('Lower')




if __name__ == "__main__":
	print(Vector2(3,5).normalize())

	size = (1280,720)


	game = EasyGame(size,cameraPosition=Vector2(-0,-0),cameraScale=Vector2(0.5,0.5))

	ball = GameObject(game,Vector2(0,10),Vector2(50,50),'data/textures/ball.png',collisionMode='circle',tag='ball',)
	ball1 = GameObject(game,Vector2(size[0]/2+200,size[1]/2),scale=Vector2(100,10),collisionMode='circle',tag='ball',sprite='data/textures/ball.png')
	ball2 = PhysicsGameObject(game,position=Vector2(0,10),collisionMode='circle',tag='ball',sprite='data/textures/ball.png',scale=Vector2(50,50))
	block = GameObject(game,position=Vector2(0,100),collisionMode='box',tag='box',sprite='data/textures/Block.png',scale=Vector2(700,100))
	button = Button(game,'data/textures/platform.png',Vector2(size[0]/2,size[1]/2),'Example Exit Button',get_font(25),"#d7fcd4","White",Vector2(600,150))
	img = Image(game,Vector2(500,500),'data/textures/Block.png')
	input_box = InputBox(game,Vector2(400,600),Vector2(50,75),get_font(50),'Example Input Box')
	lable = Lable(game,Vector2(200,100),'Example Lable',get_font(25),"#d7fcd4","White")

	running = True
	speed = 1000
	direction = 1
	threshold = 1000
	while running:
		
		ball1.position.x += direction * speed * game.delta_time
		b = (ball.position + (game.cameraScale * ball.scale)/2) * -1
		game.SetCameraPosition(b)

		if ball1.position.x >= threshold:
			ball1.position.x = threshold
			direction = -1  
		elif ball1.position.x <= -threshold:
			ball1.position.x = -threshold
			direction = 1 




		running = game.processEvents()
		if game.GetKeyState(pygame.K_w):
			ball.position.y -= 250 * game.delta_time
		if game.GetKeyState(pygame.K_a):
			ball.position.x -= 250 * game.delta_time
		if game.GetKeyState(pygame.K_s):
			ball.position.y += 250 * game.delta_time
		if game.GetKeyState(pygame.K_d):
			ball.position.x += 250 * game.delta_time

		if ball.OnCollisionStay():
			print('True')


		lable.setText(input_box.getText())
		game.UpdatePhysics()
		print(f'DeltaTime: {game.delta_time}')
		print(f'FPS: {1/game.delta_time}')
		print(f'Cursor Pos: {game.MOUSE_POS}')
		if button.clicked():
			pygame.quit()
			sys.exit()
		game.Render()
		pygame.display.update()
		

class Obj():
	def __init__(self,EasyGame,obj,position):
		self.EasyGame = EasyGame
		self.obj = obj
		self.obj_data = parse_obj("cube.obj")
		self.position = position
	
	def Update(self):
		pass

	def blit(self):
		pass