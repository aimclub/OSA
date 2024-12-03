import pygame
class Music():
    def __init__(self):
        self.now_plays = pygame.mixer.music.load("compositions/tracktwo.mp3")
    def ambient(self):
        pygame.mixer.music.play(loops=-1)
