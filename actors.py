import Box2D as box2d
from globals.types import Point
import globals
import ui
import drawing

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
        self.triangle1 = drawing.Triangle(globals.ground_buffer)
        self.triangle2 = drawing.Triangle(globals.ground_buffer)
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
                triangle.tc[v]     = (screen_coords.x/64.,screen_coords.y/64.)
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

class PlayerShip(DynamicBox):
    def __init__(self,parent,physics,bl,tr,tc):
        self.parent = parent
        relative_bl = parent.GetRelative(tr + Point(10,10))
        relative_tr = parent.GetRelative(tr + Point(400,150))
        self.text   = ui.TextBox(parent   = parent,
                                 bl       = relative_bl,
                                 tr       = relative_tr,
                                 text     = ' ',
                                 textType = drawing.texture.TextTypes.WORLD_RELATIVE,
                                 scale    = 2)
        self.letter_duration = 30
        self.text_start = None
        super(PlayerShip,self).__init__(physics,bl,tr,tc)

    def Update(self,t = None):
        super(PlayerShip,self).Update()
        self.text.SetPos(self.parent.GetRelative(self.GetPos()))
        if self.text_start == None and t != None:
            self.text_start = t+self.text_wait
        if t != None:
            elapsed = t - self.text_start
            print elapsed
            if elapsed > len(self.text.text)*self.letter_duration:
                self.text.EnableChars()
            elif elapsed > 0:
                num_enabled = int(float(elapsed)/self.letter_duration)
                self.text.EnableChars(num_enabled)
            
    def SetText(self,text,wait = 1000):
        self.text.SetText(text)
        self.text.EnableChars(0)
        self.text_start = None
        self.text_wait = wait
