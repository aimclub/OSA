import pygame
import random

class Food:
    def __init__(self):

        self.food_position = []

    def get_food_position(self,gui):
        #For getting random position for food
        self.food_position = random.choice(gui.field)

    def draw_food(self,window):
        #Draws food
        pygame.draw.rect(window, pygame.Color("Yellow"), pygame.Rect(self.food_position[0], self.food_position[1], 10, 10))
