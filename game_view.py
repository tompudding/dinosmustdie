from OpenGL.GL import *
import random,numpy

import ui,globals,drawing
from globals.types import Point

class Viewpos(object):
    def __init__(self,point):
        self.pos = point
        self.NoTarget()

    def NoTarget(self):
        self.target        = None
        self.target_change = None
        self.start_point   = None
        self.target_time   = None
        self.start_time    = None

    def Set(self,point):
        self.pos = point
        self.NoTarget()

    def SetTarget(self,point,t,rate=2):
        #Don't fuck with the view if the player is trying to control it
        self.target = point
        self.target_change = self.target - self.pos
        self.start_point   = self.pos
        self.start_time    = t
        self.duration      = self.target_change.length()/rate
        if self.duration < 200:
            self.duration = 200
        self.target_time   = self.start_time + self.duration

    def HasTarget(self):
        return self.target != None

    def Get(self):
        return self.pos

    def Update(self,t):
        if self.target:
            if t >= self.target_time:
                self.pos = self.target
                self.NoTarget()
            elif t < self.start_time: #I don't think we should get this
                return
            else:
                partial = float(t-self.start_time)/self.duration
                partial = partial*partial*(3 - 2*partial) #smoothstep
                self.pos = (self.start_point + (self.target_change*partial)).to_int()

class IntroStages(object):
    STARTED  = 0
    TEXT     = 1
    SCROLL   = 2
    COMPLETE = 3


class GameView(ui.RootElement):
    def __init__(self):
        super(GameView,self).__init__(Point(0,0),globals.screen)
        self.texture = drawing.texture.Texture('starfield.png')
        self.uielements = {}
        self.backdrop   = drawing.Quad(globals.quad_buffer,tc = drawing.constants.full_tc)
        self.backdrop.SetVertices(Point(0,0),
                                  globals.screen*2,
                                  0)
        self.viewpos = Viewpos(Point(0,globals.screen.y))
        self.t = None

    def Draw(self):
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture.texture)
        glLoadIdentity()
        glTranslatef(-self.viewpos.pos.x,-self.viewpos.pos.y,0)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        
        glVertexPointerf(globals.quad_buffer.vertex_data)
        glTexCoordPointerf(globals.quad_buffer.tc_data)
        glColorPointer(4,GL_FLOAT,0,globals.quad_buffer.colour_data)
        glDrawElements(GL_QUADS,4,GL_UNSIGNED_INT,globals.quad_buffer.indices)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisable(GL_TEXTURE_2D)
        
        glVertexPointerf(globals.ui_buffer.vertex_data)
        glTexCoordPointerf(globals.ui_buffer.tc_data)
        glColorPointer(4,GL_FLOAT,0,globals.ui_buffer.colour_data)
        glDrawElements(GL_QUADS,globals.ui_buffer.current_size,GL_UNSIGNED_INT,globals.ui_buffer.indices)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        glEnable(GL_TEXTURE_2D)

    def KeyDown(self,key):
        return  

    def Intro(self,t):
        """For now, just scroll the background a bit"""
        if self.intro_stage == IntroStages.STARTED:
            self.viewpos.SetTarget(Point(0,0),t,rate = 0.4)
            self.intro_stage = IntroStages.SCROLL
        elif self.intro_stage == IntroStages.SCROLL:
            if not self.viewpos.HasTarget():
                self.intro_stage = IntroStages.COMPLETE

        self.Draw()


    def Update(self,t):
        if self.t == None:
            self.intro_stage = IntroStages.STARTED
            self.intro_start = t
            self.t = t

        self.viewpos.Update(t)

        if self.intro_stage != IntroStages.COMPLETE:
            return self.Intro(t)


        self.Draw()
