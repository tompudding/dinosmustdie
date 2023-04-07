import sys, pygame, glob, os
import globals

from pygame.locals import *
import pygame.mixer

pygame.mixer.init()


class Sounds(object):
    def __init__(self):
        path = globals.pyinst.get_path()
        for filename in glob.glob(os.path.join(path, "*.wav")):
            # print filename
            sound = pygame.mixer.Sound(filename)
            sound.set_volume(0.6)
            name = os.path.basename(os.path.splitext(filename)[0])
            setattr(self, name, sound)
