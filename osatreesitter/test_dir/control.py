import pygame
from pygame.locals import *

class Control:
    def __init__(self):
        self.flag_game = True
        self.flag_direction = "RIGHT"
        self.flag_pause = True

    def control(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.flag_game = False
            elif event.type == KEYDOWN:
                if event.key == K_RIGHT and self.flag_direction != "LEFT":
                    self.flag_direction = "RIGHT"
                elif event.key == K_LEFT and self.flag_direction != "RIGHT":
                    self.flag_direction = "LEFT"
                elif event.key == K_DOWN and self.flag_direction != "UP":
                    self.flag_direction = "DOWN"
                elif event.key == K_UP and self.flag_direction != "DOWN":
                    self.flag_direction = "UP"
                elif event.key == K_x:
                    self.flag_game = False
                elif event.key == K_RETURN:
                    if self.flag_pause:
                        self.flag_pause = False
                    elif self.flag_pause == False:
                        self.flag_pause = True
