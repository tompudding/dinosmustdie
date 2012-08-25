from OpenGL.GL import *
import random,numpy,cmath,math

import ui,globals,drawing,os
from globals.types import Point
import Box2D as box2d
import actors

class Viewpos(object):
    follow_threshold = 0
    max_away = 250
    def __init__(self,point):
        self.pos = point
        self.NoTarget()
        self.follow = None
        self.follow_locked = False

    def NoTarget(self):
        self.target        = None
        self.target_change = None
        self.start_point   = None
        self.target_time   = None
        self.start_time    = None

    def Set(self,point):
        self.pos = point
        self.NoTarget()

    def SetTarget(self,point,t,rate=2,callback = None):
        #Don't fuck with the view if the player is trying to control it
        self.target = point
        self.target_change = self.target - self.pos
        self.start_point   = self.pos
        self.start_time    = t
        self.duration      = self.target_change.length()/rate
        self.callback = callback
        if self.duration < 200:
            self.duration = 200
        self.target_time   = self.start_time + self.duration

    def Follow(self,t,actor):
        """
        Follow the given actor around.
        """
        self.follow        = actor
        self.follow_start  = t
        self.follow_locked = False

    def HasTarget(self):
        return self.target != None

    def Get(self):
        return self.pos

    def Update(self,t):
        if self.follow:
            if self.follow_locked:
                self.pos = self.follow.GetPos() - globals.screen*0.5
            else:
                #We haven't locked onto it yet, so move closer, and lock on if it's below the threshold
                target = self.follow.GetPos() - globals.screen*0.5
                diff = target - self.pos
                if diff.SquareLength() < self.follow_threshold:
                    self.pos = target
                    self.follow_locked = True
                else:
                    distance = diff.length()
                    if distance > self.max_away:
                        self.pos += diff.unit_vector()*(distance*1.02-self.max_away)
                        newdiff = target - self.pos
                    else:
                        self.pos += diff*0.02
                
        elif self.target:
            if t >= self.target_time:
                self.pos = self.target
                self.NoTarget()
                if self.callback:
                    self.callback(t)
                    self.callback = None
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

class ShipStates(object):
    TUTORIAL_MOVEMENT = 0
    TUTORIAL_SHOOTING = 1
    TUTORIAL_TOWING   = 2

gloop_name = 'Mar Might'

class Mode(object):
    """ Abstract base class to represent game modes """
    def __init__(self,parent):
        self.parent = parent
    
    def KeyDown(self,key):
        pass
    
    def KeyUp(self,key):
        pass

    def MouseButtonDown(self,key):
        return False,False

    def Update(self,t):
        pass

class Intro(Mode):
    text = "The universe runs on a gloopy black yeast extract known as {gloop}. Farming it is difficult, but scientists postulate that a hypothetical species known as humans may be the only creature in the universe able to withstand {gloop}'s addictiveness enough to create it on an industrial scale.\n\n  Level 1 - Create 10 kilotons of {gloop}\n     Subgoal 1 - Use primordial ooze to evolve the disgusting species \"Humans\"\n\n\n                   Press any key to continue".format(gloop = gloop_name)
    def __init__(self,parent):
        self.stage  = IntroStages.STARTED
        self.parent = parent
        bl = Point(0.5,0.125)
        self.letter_duration = 20
        self.start = None
        self.menu_text = ui.TextBox(parent   = parent,
                                    bl       = bl,
                                    tr       = bl + Point(0.1,0.125),
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
            #self.parent.mode = None

    def Startup(self,t):
        self.menu_text.EnableChars(0)
        return IntroStages.TEXT

    def TextDraw(self,t):
        if not self.skipped_text and self.elapsed < len(self.menu_text.text)*self.letter_duration:
            num_enabled = int(self.elapsed/self.letter_duration)
            self.menu_text.EnableChars(num_enabled)
        elif self.continued:
            self.parent.viewpos.SetTarget(self.parent.ship.GetPos()-(globals.screen*0.5),t,rate = 0.4,callback = self.Scrolled)
            #self.parent.viewpos.Follow(t,self.parent.ship)
            return IntroStages.COMPLETE
        return IntroStages.TEXT

    def Scrolled(self,t):
        """When the view has finished scrolling, marry it to the ship"""
        self.parent.viewpos.Follow(t,self.parent.ship)
        self.menu_text.Disable()
    
    def Scroll(self,t):
        pass
#        if not self.parent.viewpos.HasTarget():
#            self.menu_text.Disable()
#            return IntroStages.COMPLETE
#        else:
#            return IntroStages.SCROLL


class MyContactListener(box2d.b2ContactListener):
    physics = None
    def __init__(self): 
        super(MyContactListener, self).__init__() 
    def Add(self, point):
        """Handle add point"""
        print 'a',dir(point.shape1)
    def Persist(self, point):
        """Handle persist point"""
        #print 'b',point.shape1
        pass
    def Remove(self, point):
        """Handle remove point"""
        #print 'c',point
        pass
    def Result(self, point):
        """Handle results"""
        #print 'd',point
        pass

        

class Physics(object):
    scale_factor = 0.1
    def __init__(self,parent):
        self.contact_listener = MyContactListener()
        self.parent = parent
        self.worldAABB=box2d.b2AABB()
        self.worldAABB.lowerBound = (-100,-globals.screen.y-100)
        self.worldAABB.upperBound = (100 + self.parent.absolute.size.x*self.scale_factor,100 + self.parent.absolute.size.y*self.scale_factor + 100)
        self.gravity = (0,-10)
        self.doSleep = True
        self.world = box2d.b2World(self.worldAABB, self.gravity, self.doSleep)
        self.world.SetContactListener(self.contact_listener)
        self.timeStep = 1.0 / 60.0
        self.velocityIterations = 10
        self.positionIterations = 8
        self.objects = []
    
    def AddObject(self,obj):
        self.objects.append(obj)

    def Step(self):
        self.contacts = []
        self.world.Step(self.timeStep, self.velocityIterations, self.positionIterations)
        for contact in self.contacts:
            #print contact
            pass
        for obj in self.objects:
            obj.Update()

class Keys(object):
    UP    = 1
    LEFT  = 2
    RIGHT = 4
    ALL   = UP | LEFT | RIGHT

class GameMode(Mode):
    def __init__(self,parent):
        self.parent = parent
        self.thrust = None
        self.rotate = None
        self.pi2 = math.pi/2
        self.ooze_boxes = []
        self.up_keys = [0x111,ord('w')]
        self.left_keys = [0x114,ord('a')]
        self.right_keys = [0x113,ord('d')]
        self.parent.ship.SetText('Use the W and D keys to rotate the ship, and A to provide thrust') 
        self.parent.ship.state = ShipStates.TUTORIAL_MOVEMENT
        self.tutorial_handlers = {ShipStates.TUTORIAL_MOVEMENT : self.TutorialMovement,
                                  ShipStates.TUTORIAL_SHOOTING : self.TutorialShooting,
                                  ShipStates.TUTORIAL_TOWING   : self.TutorialTowing}
        self.all_time_key_mask = 0
        self.key_mask = 0
        
        #Add in 15 ooze boxes
        for i in xrange(15):
            bl = Point(random.random()*self.parent.absolute.size.x*0.9,
                       self.parent.max_floor_height + random.random()*400)
            self.ooze_boxes.append( actors.DynamicBox(self.parent.physics,
                                                      bl = bl,
                                                      tr = bl + Point(50,50),
                                                      tc = parent.atlas.TextureCoords(os.path.join(globals.dirs.sprites,'crate.png'))) )
                                               
            
        
    def KeyDown(self,key):
        
        #if key in [13,27,32]: #return, escape, space
        if key in self.up_keys:
            #Apply force to the ship
            self.thrust = 2100
            self.all_time_key_mask |= Keys.UP
            self.key_mask          |= Keys.UP
        if key in self.left_keys:
            self.all_time_key_mask |= Keys.LEFT
            self.key_mask          |= Keys.LEFT
        if key in self.right_keys:
            self.all_time_key_mask |= Keys.RIGHT
            self.key_mask          |= Keys.RIGHT
        #elif key == 0x

    def KeyUp(self,key):
        if key in self.up_keys:
            self.thrust = None
            self.key_mask          &= ~Keys.UP
        if key in self.left_keys:
            self.key_mask          &= ~Keys.LEFT
        if key in self.right_keys:
            self.key_mask          &= ~Keys.RIGHT

    def MouseButtonDown(self,pos,button):
        if button == 1:
            self.parent.ship.Fire(pos)
        return False,False

    def TutorialMovement(self,t):
        if self.all_time_key_mask == Keys.ALL:
            self.parent.ship.SetText('Aim with the mouse and left click to shoot',wait=0)
            self.parent.ship.state = ShipStates.TUTORIAL_SHOOTING

    def TutorialShooting(self,t):
        pass

    def TutorialTowing(self,t):
        pass

    def Update(self,t):
        self.parent.ship.Update(t)
        try:
            self.tutorial_handlers[self.parent.ship.state](t)
        except KeyError:
            pass
        if self.thrust:
            angle = self.parent.ship.body.angle + self.pi2
            vector = cmath.rect(self.thrust,angle)
            self.parent.ship.body.ApplyForce((vector.real,vector.imag),self.parent.ship.body.position)
        rotate = 0
        if self.key_mask&Keys.LEFT:
            rotate += 0.05
        if self.key_mask&Keys.RIGHT:
            rotate -= 0.05
            #self.parent.ship.body.ApplyTorque(self.rotate)
        if rotate:
            self.parent.ship.body.angle = self.parent.ship.body.angle + rotate
            self.parent.ship.body.angularVelocity = 0

class GameView(ui.RootElement):
    def __init__(self):
        super(GameView,self).__init__(Point(0,0),Point(globals.screen.x*10,globals.screen.y*8))
        self.atlas = drawing.texture.TextureAtlas('tiles_atlas_0.png','tiles_atlas.txt')
        self.uielements = {}
        #backdrop_tc = [[0,0],[0,1],[5,1],[5,0]]
        #self.atlas.TransformCoords('starfield.png',backdrop_tc) 
        #self.backdrop   = drawing.Quad(globals.quad_buffer,tc = backdrop_tc)
        self.backdrop_texture = drawing.texture.Texture('starfield.png')
        self.ground_texture   = drawing.texture.Texture(os.path.join('sprites','dirt.png'))
        self.backdrop  = drawing.Quad(globals.backdrop_buffer,tc = numpy.array([(0,0),(0,4),(5,4),(5,0)]))
        self.backdrop.SetVertices(Point(0,0),
                                  self.absolute.size,
                                  drawing.constants.DrawLevels.grid)
        self.viewpos = Viewpos(Point(globals.screen.x*5,globals.screen.y))
        self.t = None
        self.physics = Physics(self)
        dirt_x = self.absolute.size.x/(self.ground_texture.width*2.0)
        dirt_y = (globals.screen.y+50)/(self.ground_texture.height*2.0)
        dirt_tc = [[0,0],[0,dirt_y],[dirt_x,dirt_y],[dirt_x,0]]
        #self.floor = StaticBox(self.physics,
        #                       bl = Point(0,-globals.screen.y),
        #                       tr = Point(self.absolute.size.x,50),
        #                       tc = dirt_tc)
        self.walls = [actors.StaticBox(self.physics,
                                       bl = Point(0,0),
                                       tr = Point(1,self.absolute.size.y)),
                      actors.StaticBox(self.physics,
                                       bl = Point(self.absolute.size.x,0),
                                       tr = Point(self.absolute.size.x+1,self.absolute.size.y)),
                      actors.StaticBox(self.physics,
                                       bl = Point(0,self.absolute.size.y),
                                       tr = Point(self.absolute.size.x,self.absolute.size.y+1)) ]
        self.max_floor_height = max_height = 400
        min_height = 100
        min_diff   = 30
        self.ship   = actors.PlayerShip(self,
                                        self.physics,
                                        bl = Point(self.absolute.size.x*0.55,max_height+20),
                                        tr = Point(self.absolute.size.x*0.55+50,max_height+20+50),
                                        tc = self.atlas.TextureCoords(os.path.join(globals.dirs.sprites,'ship.png')))
        
        self.land_heights = [(0,50)]
        self.landscape = []
        pos,height = self.land_heights[0]
        
        while pos < self.absolute.size.x:
            y_diff  = random.normalvariate(0,50)
            x_diff  = 100+random.random()*100
            if abs(y_diff) < min_diff:
                y_diff *= min_diff/float(abs(y_diff))
            pos    += x_diff
            height += y_diff
            if height > max_height:
                height = max_height - (2*y_diff)
            if height < min_height:
                height = min_height - (2*y_diff)
            self.land_heights.append( (pos,height) )

        #Now create a triangle and a quad for each land point
        for i in xrange(1,len(self.land_heights)):
            bottom_x,bottom_y = self.land_heights[i-1]
            top_x,top_y = self.land_heights[i]
            if bottom_y > top_y:
                self.landscape.append(actors.StaticTriangle(self.physics,
                                                            (Point(bottom_x,top_y),
                                                             Point(top_x,top_y),
                                                             Point(bottom_x,bottom_y))))
                self.landscape.append(actors.StaticBox(self.physics,
                                                       bl = Point(bottom_x,-globals.screen.y),
                                                       tr = Point(top_x,top_y),
                                                       tc = True))

            else:
                self.landscape.append(actors.StaticTriangle(self.physics,
                                                            (Point(bottom_x,bottom_y),
                                                             Point(top_x,bottom_y),
                                                             Point(top_x,top_y))))
                self.landscape.append(actors.StaticBox(self.physics,
                                                       bl = Point(bottom_x,-globals.screen.y),
                                                       tr = Point(top_x,bottom_y),
                                                       tc = True))
                                                
        #raise SystemExit
            
        
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
        

        #Draw the world backdrop...

        #Draw the ground triangles
        glBindTexture(GL_TEXTURE_2D, self.ground_texture.texture)
        glTranslatef(-self.viewpos.pos.x,-self.viewpos.pos.y,0)
        glVertexPointerf(globals.ground_buffer.vertex_data)
        glTexCoordPointerf(globals.ground_buffer.tc_data)
        glColorPointer(4,GL_FLOAT,0,globals.ground_buffer.colour_data)
        glDrawElements(GL_TRIANGLES,globals.ground_buffer.current_size,GL_UNSIGNED_INT,globals.ground_buffer.indices)
        
        #Draw the world items
        glBindTexture(GL_TEXTURE_2D, self.atlas.texture.texture)
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

        glBindTexture(GL_TEXTURE_2D, self.backdrop_texture.texture)
        #glLoadIdentity()
        #glScalef(0.9,0.9,1)
        #glTranslatef(-self.viewpos.pos.x,-self.viewpos.pos.y,0)
        glVertexPointerf(globals.backdrop_buffer.vertex_data)
        glTexCoordPointerf(globals.backdrop_buffer.tc_data)
        glColorPointer(4,GL_FLOAT,0,globals.backdrop_buffer.colour_data)
        glDrawElements(GL_QUADS,4,GL_UNSIGNED_INT,globals.backdrop_buffer.indices)

        
        
    def KeyDown(self,key):
        self.mode.KeyDown(key)

    def KeyUp(self,key):
        self.mode.KeyUp(key)

    def MouseButtonDown(self,pos,button):
        if self.mode:
            pos = self.viewpos.pos + pos
            return self.mode.MouseButtonDown(pos,button)
        else:
            return False,False

    def Update(self,t):
        if self.t == None:
            self.t = t
        self.physics.Step()

        self.viewpos.Update(t)
        if self.mode:
            self.mode.Update(t)

        self.Draw()
