from OpenGL.GL import *
import random,numpy,cmath,math,pygame

import ui,globals,drawing,os,copy
from globals.types import Point
import Box2D as box2d
import actors
import modes

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
        self.follow        = None
        self.follow_start  = 0
        self.follow_locked = False
        self.target        = point
        self.target_change = self.target - self.pos
        self.start_point   = self.pos
        self.start_time    = t
        self.duration      = self.target_change.length()/rate
        self.callback      = callback
        if self.duration < 200:
            self.duration  = 200
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
                fpos = self.follow.GetPos()
                if not fpos:
                    return
                target = fpos - globals.screen*0.5
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


class fwContactPoint:
    """
    Structure holding the necessary information for a contact point.
    All of the information is copied from the contact listener callbacks.
    """
    shape1 = None
    shape2 = None
    normal = None
    position = None
    velocity = None
    id  = None
    state = 0


class MyContactListener(box2d.b2ContactListener):
    physics = None
    def __init__(self): 
        super(MyContactListener, self).__init__() 
    def Add(self, point):
        """Handle add point"""
        if not self.physics:
            return
        cp          = fwContactPoint()
        cp.shape1   = point.shape1
        cp.shape2   = point.shape2
        cp.position = point.position.copy()
        cp.normal   = point.normal.copy()
        cp.id       = point.id
        #cp.state    = state

            #print self.physics.contacts
        self.physics.contacts.append(cp)
        #print 'a',self.physics
        #print 'a',dir(point.shape1)
        
    def Persist(self, point):
        """Handle persist point"""
        #print 'b',point.shape1
        pass
    def Remove(self, point):
        """Handle remove point"""
        # if not self.physics:
        #     return
        # print 'aaa'
        # cp          = fwContactPoint()
        # cp.shape1   = point.shape1
        # cp.shape2   = point.shape2
        # cp.position = point.position.copy()
        # cp.normal   = point.normal.copy()
        # cp.id       = point.id
        # for contact in self.physics.contacts:
        #     if contact == cp:
        #         print 'x'
        #         raise SystemExit
        pass
    def Result(self, point):
        """Handle results"""
        #print 'd',point
        pass

        

class Physics(object):
    scale_factor = 0.1
    def __init__(self,parent):
        self.contact_listener = MyContactListener()
        self.contact_listener.physics = self
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
            if isinstance(contact.shape1.userData,actors.PlayerBullet):
                bullet = contact.shape1
                target = contact.shape2
            elif isinstance(contact.shape2.userData,actors.PlayerBullet):
                bullet = contact.shape2
                target = contact.shape1
            else:
                bullet = None
                target = None
            if bullet:
                bullet.userData.Destroy()
                if target.userData != None:
                    target.userData.Damage(10)
                #print 'Bullet Collision!'
        for obj in self.objects:
            obj.PhysUpdate()


class GameView(ui.RootElement):
    def __init__(self):
        super(GameView,self).__init__(Point(0,0),Point(globals.screen.x*10,globals.screen.y*8))
        self.atlas = globals.atlas = drawing.texture.TextureAtlas('tiles_atlas_0.png','tiles_atlas.txt')
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
        self.paused = False
        self.viewpos = Viewpos(Point(globals.screen.x*5,globals.screen.y))
        self.t = None
        self.physics = Physics(self)
        self.enemies = []
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
                                        tr = Point(self.absolute.size.x*0.55+50,max_height+20+43),
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
            
        
        self.mode = modes.Intro(self)
        #self.mode = modes.GameOver(self,False,7)
        #self.game_mode = modes.GameMode(self)
        #self.mode = modes.Titles(self)

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
        if not self.paused:
            self.physics.Step()

        self.viewpos.Update(t)
        if self.mode:
            self.mode.Update(t)

        if not self.paused:
            for enemy in self.enemies:
                enemy.Update(t)

        self.Draw()

    def Pause(self):
        self.paused = True

    def GetFloorHeight(self,x):
        for i,(pos,height) in enumerate(self.land_heights):
            if pos > x:
                break
        else:
            #Er, they asked for off the right of the screen?
            return 0
        if i == 0:
            #They asked for off the left of the screen
            return 0
        prev_x,prev_height = self.land_heights[i-1]
        partial = (pos-x)/float(pos -prev_x)
        return prev_height + partial*(height-prev_height)

    def AddTrex(self):
        x = 0.1 + (random.random()*self.absolute.size.x*0.9)
        bl = Point(x,self.GetFloorHeight(x))
        self.enemies.append( actors.Trex(self,
                                         self.physics,
                                         bl = bl,
                                         tr = bl + Point(50,50)) )

    def RemoveTrex(self,trex):
        for i in xrange(len(self.enemies)):
            if trex is self.enemies[i]:
                del self.enemies[i]
                break
        self.ship.AddScore(129)
        if len(self.enemies) == 0:
            self.mode = modes.GameOver(self,win = True,score = self.ship.score)
