import pygame
class Snake():
    def __init__(self):
        self.score = 0
        self.head = [45,45]
        self.body = [[45,45],[34,45],[23,45]]
    def moove(self,control):
        if control.flag_direction == "RIGHT":
            self.head[0] += 11
        if control.flag_direction == "LEFT":
            self.head[0] -= 11
        if control.flag_direction == "DOWN":
            self.head[1] += 11
        if control.flag_direction == "UP":
            self.head[1] -= 11

    def animation(self):
        #Head ahead and tail gets back
        self.body.insert(0,list(self.head))
        self.body.pop()

    def draw_snake(self,window):
        for segment in self.body:
            pygame.draw.rect(window, (0, 209, 3), pygame.Rect(segment[0], segment[1], 10, 10))

    def check_end_window(self):
        #Checking if snake reached the level`s edge
        if self.head[0] == 419:
            self.head[0] = 23
        elif self.head[0] == 12:
            self.head[0] = 419
        elif self.head[1] == 23:
            self.head[1] = 419
        elif self.head[1] == 419:
            self.head[1] = 34


    def eat(self,food,gui):
        #Snake eating
        if self.head == food.food_position:
            self.body.append(food.food_position)
            food.get_food_position(gui)
            gui.get_new_indicator()

    def check_barrier(self,gui):
        #Be careful with barriers!
        if self.head in gui.barrier:
            self.body.pop()
            gui.indicator.pop()
            #print(len(gui.indicator))
            #print(gui.game)

        if self.head in self.body[1:]:
            self.body.pop()
            gui.indicator.pop()
            #print(len(gui.indicator))
            #print(gui.game)
    def count_score(self,food,gui):
        if self.head == food.food_position:
            self.score += 10
        elif self.head in gui.barrier or self.head in self.body[1:]:
            self.score -= 10
