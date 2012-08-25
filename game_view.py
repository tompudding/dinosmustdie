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

gloop_name = 'Mar Might'

class Intro(object):
    text = "The universe runs on a gloopy black yeast extract known as {gloop}. Farming it is difficult, but scientists postulate that a hypothetical species known as humans may be the only creature in the universe able to withstand {gloop}'s addictiveness enough to create it on an industrial scale.\n\n  Level 1 - Create 10 kilotons of {gloop}\n     Subgoal 1 - Use primordial ooze to evolve the disgusting species \"Humans\"\n\n\n                   Press any key to continue".format(gloop = gloop_name)
    def __init__(self,parent):
        self.stage  = IntroStages.STARTED
        self.parent = parent
        bl = Point(0,1)
        self.letter_duration = 20
        self.start = None
        self.menu_text = ui.TextBox(parent   = parent,
                                    bl       = bl,
                                    tr       = bl + Point(1,1),
                                    text     = self.text,
                                    textType = drawing.texture.TextTypes.WORLD_RELATIVE,
                                    scale    = 3)
        self.handlers = {IntroStages.STARTED : self.Startup,
                         IntroStages.TEXT    : self.TextDraw,
                         IntroStages.SCROLL  : self.Scroll}
        self.skipped_text = False
        self.continued = False

    def SkipText(self):
        self.skipped_text = True
        self.menu_text.EnableChars()

    def KeyDown(self,key):
        #if key in [13,27,32]: #return, escape, space
        if not self.skipped_text:
            self.SkipText()
        else:
            self.continued = True

    def MouseButtonDown(self,pos,button):
        self.KeyDown(0)
        return False,False

    def Update(self,t):
        """For now, just scroll the background a bit"""
        if self.start == None:
            self.start = t
        self.elapsed = t - self.start
        self.stage = self.handlers[self.stage](t)
        if self.stage == IntroStages.COMPLETE:
            self.parent.mode = GameMode(self.parent)

    def Startup(self,t):
        self.menu_text.EnableChars(0)
        return IntroStages.TEXT

    def TextDraw(self,t):
        if not self.skipped_text and self.elapsed < len(self.menu_text.text)*self.letter_duration:
            num_enabled = int(self.elapsed/self.letter_duration)
            self.menu_text.EnableChars(num_enabled)
        elif self.continued:
            self.parent.viewpos.SetTarget(Point(0,0),t,rate = 0.4)
            return IntroStages.SCROLL
        return IntroStages.TEXT

    
    def Scroll(self,t):
        if not self.parent.viewpos.HasTarget():
            self.menu_text.Disable()
            return IntroStages.COMPLETE
        else:
            return IntroStages.SCROLL


class GameView(ui.RootElement):
    
    def __init__(self):
        super(GameView,self).__init__(Point(0,0),globals.screen)
        self.texture = drawing.texture.Texture('starfield.png')
        self.uielements = {}
        self.backdrop   = drawing.Quad(globals.quad_buffer,tc = drawing.constants.full_tc)
        self.backdrop.SetVertices(Point(0,0),
                                  globals.screen*2,
                                  drawing.constants.DrawLevels.grid)
        self.viewpos = Viewpos(Point(0,globals.screen.y))
        self.t = None
        
        self.mode = Intro(self)

    def Draw(self):

        #for i,q in enumerate(self.menu_text.quads):
        #    print i,q.index
        #print globals.nonstatic_text_buffer.indices[:24]
            
        
        glLoadIdentity()
        #Draw the UI
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
#        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
#        glVertexPointerf(globals.ui_buffer.vertex_data)
#        glTexCoordPointerf(globals.ui_buffer.tc_data)
#        glColorPointer(4,GL_FLOAT,0,globals.ui_buffer.colour_data)
#        glDrawElements(GL_QUADS,globals.ui_buffer.current_size,GL_UNSIGNED_INT,globals.ui_buffer.indices)

        glEnable(GL_TEXTURE_2D)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        

        #Draw the world...
        glBindTexture(GL_TEXTURE_2D, self.texture.texture)
        glTranslatef(-self.viewpos.pos.x,-self.viewpos.pos.y,0)
        glVertexPointerf(globals.quad_buffer.vertex_data)
        glTexCoordPointerf(globals.quad_buffer.tc_data)
        glColorPointer(4,GL_FLOAT,0,globals.quad_buffer.colour_data)
        glDrawElements(GL_QUADS,globals.quad_buffer.current_size,GL_UNSIGNED_INT,globals.quad_buffer.indices)

        #Draw the world text
        glBindTexture(GL_TEXTURE_2D, globals.text_manager.atlas.texture.texture)
        glVertexPointerf(globals.nonstatic_text_buffer.vertex_data)
        glTexCoordPointerf(globals.nonstatic_text_buffer.tc_data)
        glColorPointer(4,GL_FLOAT,0,globals.nonstatic_text_buffer.colour_data)
        glDrawElements(GL_QUADS,globals.nonstatic_text_buffer.current_size,GL_UNSIGNED_INT,globals.nonstatic_text_buffer.indices)
        
        
    def KeyDown(self,key):
        self.mode.KeyDown(key)

    def MouseButtonDown(self,pos,button):
        return self.mode.MouseButtonDown(pos,button)

    def Update(self,t):
        if self.t == None:
            self.t = t

        self.viewpos.Update(t)
        self.mode.Update(t)

        self.Draw()
