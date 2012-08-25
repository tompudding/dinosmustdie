from OpenGL.GL import *
import random,numpy,cmath,math

import ui,globals,drawing,os
from globals.types import Point
import Box2D as box2d

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
                        print distance,newdiff.length()
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

class StaticBox(object):
    def __init__(self,physics,bl,tr,tc = None):
        #Hardcode the dirt texture since right now all static things are dirt. I know I know.
        if tc != None:
            self.InitPolygons(tc)
            self.visible = True
        else:
            self.visible = False
        self.physics = physics
        self.bodydef = box2d.b2BodyDef()
        midpoint = (tr - bl)*0.5*physics.scale_factor
        self.bodydef.position = tuple((bl*physics.scale_factor) + midpoint)
        self.shape = box2d.b2PolygonDef()
        self.shape.SetAsBox(*midpoint)
        self.body = physics.world.CreateBody(self.bodydef)
        self.shape.density = 1
        self.shape.friction = 0.7
        self.body.CreateShape(self.shape)
        self.Update()

    def InitPolygons(self,tc):
        self.triangle1 = drawing.Triangle(globals.ground_buffer,tc = [tc[0],tc[3],tc[2]])
        self.triangle2 = drawing.Triangle(globals.ground_buffer,tc = [tc[2],tc[1],tc[0]])
        #self.triangles = self.triangle1,self.triangle2

    def GetPos(self):
        return Point(*self.body.position)/self.physics.scale_factor

    def Update(self):
        if not self.visible:
            return
        for triangle,vertex_list in ((self.triangle1,(0,1,2)),(self.triangle2,(2,3,0))):
            v = 0
            for i in vertex_list:
                vertex = self.shape.vertices[i]
                screen_coords = Point(*self.body.GetWorldPoint(vertex))/self.physics.scale_factor
                triangle.vertex[v] = (screen_coords.x,screen_coords.y,10)
                v += 1

class StaticTriangle(object):
    def __init__(self,physics,vertices):
        self.physics = physics
        self.bodydef = box2d.b2BodyDef()
        self.triangle = drawing.Triangle(globals.ground_buffer)
        #I don't think it matters much, but set the position to the average of the 3 points
        midpoint = ((vertices[0] + vertices[1] + vertices[2])*self.physics.scale_factor)/3.0
        self.bodydef.position = tuple(midpoint)
        self.shape = box2d.b2PolygonDef()
        self.shape.setVertices([ list(vertex*self.physics.scale_factor - midpoint) for vertex in vertices ])
        self.body = physics.world.CreateBody(self.bodydef)
        self.shape.density = 1
        self.shape.friction = 0.5
        self.body.CreateShape(self.shape)
        self.Update()

    def GetPos(self):
        return Point(*self.body.position)/self.physics.scale_factor

    def Update(self):
        for i in xrange(3):
            vertex = self.shape.vertices[i]
            screen_coords = Point(*self.body.GetWorldPoint(vertex))/self.physics.scale_factor
            self.triangle.vertex[i] = (screen_coords.x,screen_coords.y,10)
            self.triangle.tc[i] = (screen_coords.x/64.,screen_coords.y/64.)
        

class DynamicBox(StaticBox):
    def __init__(self,physics,bl,tr,tc):
        super(DynamicBox,self).__init__(physics,bl,tr,tc)

        self.body.SetMassFromShapes()
        physics.AddObject(self)

    def InitPolygons(self,tc):
        self.quad = drawing.Quad(globals.quad_buffer,tc = tc)


    def Update(self):
        #Just set the vertices
        
        #bl = (Point(*self.body.GetWorldPoint(self.shape.vertices[0])))/self.physics.scale_factor
        #tr = (Point(*self.body.GetWorldPoint(self.shape.vertices[2])))/self.physics.scale_factor
        #tr = (Point(*self.shape.vertices[2]) + Point(*self.body.position))/self.physics.scale_factor
        for i,vertex in enumerate(self.shape.vertices):
            screen_coords = Point(*self.body.GetWorldPoint(vertex))/self.physics.scale_factor
            self.quad.vertex[(i+3)%4] = (screen_coords.x,screen_coords.y,10)
        #print self.body.angle,bl
        #print bl,tr
        #print self.body.position
        #self.quad.SetVertices(bl,tr,10)

        

class Physics(object):
    scale_factor = 0.1
    def __init__(self,parent):
        self.parent = parent
        self.worldAABB=box2d.b2AABB()
        self.worldAABB.lowerBound = (-100,-globals.screen.y-100)
        self.worldAABB.upperBound = (100 + self.parent.absolute.size.x*self.scale_factor,100 + self.parent.absolute.size.y*self.scale_factor + 100)
        self.gravity = (0,-10)
        self.doSleep = True
        self.world = box2d.b2World(self.worldAABB, self.gravity, self.doSleep)
        self.timeStep = 1.0 / 60.0
        self.velocityIterations = 10
        self.positionIterations = 8
        self.objects = []
    
    def AddObject(self,obj):
        self.objects.append(obj)

    def Step(self):
        self.world.Step(self.timeStep, self.velocityIterations, self.positionIterations)
        for obj in self.objects:
            obj.Update()

class GameMode(Mode):
    def __init__(self,parent):
        self.parent = parent
        self.thrust = None
        self.rotate = None
        self.pi2 = math.pi/2
        
    def KeyDown(self,key):
        #if key in [13,27,32]: #return, escape, space
        if key == 0x111:
            #Apply force to the ship
            self.thrust = 700
        if key == 0x114:
            self.rotate = 0.05
        if key == 0x113:
            self.rotate = -0.05
        #elif key == 0x

    def KeyUp(self,key):
        print key
        if key == 0x111:
            self.thrust = None
        if key == 0x114 or key == 0x113:
            self.rotate = None

    def MouseButtonDown(self,pos,button):
        return False,False

    def Update(self,t):
        if self.thrust:
            angle = self.parent.ship.body.angle + self.pi2
            vector = cmath.rect(self.thrust,angle)
            self.parent.ship.body.ApplyForce((vector.real,vector.imag),self.parent.ship.body.position)
        if self.rotate:
            #self.parent.ship.body.ApplyTorque(self.rotate)
            self.parent.ship.body.angle = self.parent.ship.body.angle + self.rotate
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
        print dirt_tc
        self.floor = StaticBox(self.physics,
                               bl = Point(0,-globals.screen.y),
                               tr = Point(self.absolute.size.x,50),
                               tc = dirt_tc)
        self.walls = [StaticBox(self.physics,
                                bl = Point(0,0),
                                tr = Point(1,self.absolute.size.y),
                                tc = None),
                      StaticBox(self.physics,
                                bl = Point(self.absolute.size.x,0),
                                tr = Point(self.absolute.size.x+1,self.absolute.size.y),
                                tc = None),
                      StaticBox(self.physics,
                                bl = Point(0,self.absolute.size.y),
                                tr = Point(self.absolute.size.x,self.absolute.size.y+1),
                                tc = None) ]
        self.temp = StaticTriangle(self.physics,
                                   (Point(0,0),
                                    Point(500,0),
                                    Point(500,500)))
                                   
        self.ship   = DynamicBox(self.physics,
                                bl = Point(self.absolute.size.x*0.55,100),
                                tr = Point(self.absolute.size.x*0.55+50,150),
                                tc = self.atlas.TextureCoords(os.path.join(globals.dirs.sprites,'ship.png')))

        self.land_heights = [(0,50)]
        pos,height = self.land_heights[0]
        while pos < self.absolute.size.x:
            y_diff  = random.normalvariate(50,20)
            x_diff  = random.random()*50
            pos    += x_diff
            height += y_diff
            self.land_heights.append( (pos,height) )

        #Now create a triangle and a quad for each land point
        for i in xrange(1,len(self.land_heights)):
            pos,height = self.land_heights[i-1]
            next_pos,next_height = self.land_heights[i]
            

        print self.land_heights
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
        glBindTexture(GL_TEXTURE_2D, self.backdrop_texture.texture)
        glTranslatef(-self.viewpos.pos.x,-self.viewpos.pos.y,0)
        glVertexPointerf(globals.backdrop_buffer.vertex_data)
        glTexCoordPointerf(globals.backdrop_buffer.tc_data)
        glColorPointer(4,GL_FLOAT,0,globals.backdrop_buffer.colour_data)
        glDrawElements(GL_QUADS,4,GL_UNSIGNED_INT,globals.backdrop_buffer.indices)

        #Draw the ground triangles
        glBindTexture(GL_TEXTURE_2D, self.ground_texture.texture)
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
        
        
    def KeyDown(self,key):
        self.mode.KeyDown(key)

    def KeyUp(self,key):
        self.mode.KeyUp(key)

    def MouseButtonDown(self,pos,button):
        print self.viewpos.pos + pos
        if self.mode:
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
