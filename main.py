import os, sys
import pygame
import game_view,ui,globals
import drawing
import sounds
from globals.types import Point

from OpenGL.arrays import numpymodule
from OpenGL.GL import *
from OpenGL.GLU import *

def Init():
    """Initialise everything. Run once on startup"""
    w,h = (1280,720)
    globals.screen                = Point(w,h)
    globals.screen_root           = ui.UIRoot(Point(0,0),globals.screen)
    globals.quad_buffer           = drawing.QuadBuffer(131072)
    globals.ui_buffer             = drawing.QuadBuffer(131072)
    globals.nonstatic_text_buffer = drawing.QuadBuffer(131072)
    globals.backdrop_buffer       = drawing.QuadBuffer(8)
    globals.colour_tiles          = drawing.QuadBuffer(131072)
    globals.mouse_relative_buffer = drawing.QuadBuffer(1024)
    globals.ground_buffer         = drawing.TriangleBuffer(131072)
    globals.sounds                = sounds.Sounds()
    

    globals.dirs = globals.types.Directories('resource')

    pygame.init()
    screen = pygame.display.set_mode((w,h),pygame.OPENGL|pygame.DOUBLEBUF)
    glClearColor(0.0, 0.0, 0.0, 1.0)
    pygame.display.set_caption('Dinosaurs must Die!')
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, w, 0, h,-10000,10000)
    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_TEXTURE_2D)
    glEnable(GL_BLEND)
    glEnable(GL_DEPTH_TEST);
    glAlphaFunc(GL_GREATER, 0.25);
    glEnable(GL_ALPHA_TEST);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(1.0,1.0,1.0,1.0)

    globals.text_manager = drawing.texture.TextManager()

def main():
    """Main loop for the game"""
    Init()

    globals.current_view = globals.game_view = game_view.GameView()

    done = False
    last = 0
    clock = pygame.time.Clock()

    while not done:
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        clock.tick(60)
        t = pygame.time.get_ticks()
        if t - last > 1000:
            #print 'FPS:',clock.get_fps()
            last = t
        #globals.current_time = t

        glLoadIdentity()
        globals.current_view.Update(t)
        globals.current_view.Draw()
        globals.screen_root.Draw()
        globals.text_manager.Draw()
        pygame.display.flip()

        eventlist = pygame.event.get()
        for event in eventlist:
            if event.type == pygame.locals.QUIT:
                done = True
                break
            elif (event.type == pygame.KEYDOWN):
                globals.current_view.KeyDown(event.key)
            elif (event.type == pygame.KEYUP):
                globals.current_view.KeyUp(event.key)
            else:
                try:
                    pos = Point(event.pos[0],globals.screen[1]-event.pos[1])
                except AttributeError:
                    continue
                if event.type == pygame.MOUSEMOTION:
                    rel = Point(event.rel[0],-event.rel[1])
                    handled = globals.screen_root.MouseMotion(pos,rel,False)
                    if handled:
                        globals.current_view.CancelMouseMotion()
                    globals.current_view.MouseMotion(pos,rel,True if handled else False)
                elif (event.type == pygame.MOUSEBUTTONDOWN):
                    for layer in globals.screen_root,globals.current_view:
                        handled,dragging = layer.MouseButtonDown(pos,event.button)
                        if handled and dragging:
                            globals.dragging = dragging
                            break
                        if handled:
                            break
                    
                elif (event.type == pygame.MOUSEBUTTONUP):
                    for layer in globals.screen_root,globals.current_view:
                        handled,dragging = layer.MouseButtonUp(pos,event.button)
                        if handled and not dragging:
                            globals.dragging = None
                        if handled:
                            break

if __name__ == '__main__':
    import logging
    try:
        logging.basicConfig(level=logging.DEBUG, filename='errorlog.log')
        #logging.basicConfig(level=logging.DEBUG)
    except IOError:
        #pants, can't write to the current directory, try using a tempfile
        pass

    try:
        main()
    except Exception, e:
        print 'Caught exception, writing to error log...'
        logging.exception("Oops:")
        #Print it to the console too...
        raise
