import Box2D as box2d
from globals.types import Point
import globals
import ui
import drawing
import cmath
import math
import os
import game_view
import modes
import random

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
        self.PhysUpdate()

    def GetPos(self):
        return Point(*self.body.position)/self.physics.scale_factor

    def PhysUpdate(self):
        for i in xrange(3):
            vertex = self.shape.vertices[i]
            screen_coords = Point(*self.body.GetWorldPoint(vertex))/self.physics.scale_factor
            self.triangle.vertex[i] = (screen_coords.x,screen_coords.y,10)
            self.triangle.tc[i] = (screen_coords.x/64.,screen_coords.y/64.)
        

class StaticBox(object):
    isBullet = False
    mass     = 1
    filter_group = None
    static   = True
    health   = 500
    def __init__(self,physics,bl,tr,tc = None):
        #Hardcode the dirt texture since right now all static things are dirt. I know I know.
        self.dead = False
        self.tc = tc
        if tc is not None:
            self.InitPolygons(tc)
            self.visible = True
        else:
            self.visible = False
        self.physics = physics
        self.bodydef = box2d.b2BodyDef()
        midpoint = (tr - bl)*0.5*physics.scale_factor
        self.bodydef.position = tuple((bl*physics.scale_factor) + midpoint)
        self.shape = self.CreateShape(midpoint)
        if not self.static:
            self.shape.userData = self
        if self.filter_group is not None:
            self.shape.filter.groupIndex = self.filter_group
        self.bodydef.isBullet = self.isBullet
        self.body = physics.world.CreateBody(self.bodydef)
        self.shape.density = self.mass
        self.shape.friction = 0.7
        self.shapeI = self.body.CreateShape(self.shape)
        self.child_joint = None
        self.parent_joint = None
        self.PhysUpdate()

    def Destroy(self):
        if self.static:
            #Don't ever destroy static things
            return
        if self.dead:
            return
        if self.parent_joint:
            #We're attached, so get rid of that before killing us
            self.parent_joint.UnGrapple()
            self.parent_joint = None
        self.shape.ClearUserData()
        self.physics.world.DestroyBody(self.body)
        self.dead = True
        self.quad.Disable()

    def Damage(self,amount):
        #can't damage static stuff
        return

    def CreateShape(self,midpoint):
        if self.dead:
            return
        shape = box2d.b2PolygonDef()
        shape.SetAsBox(*midpoint)
        return shape

    def InitPolygons(self,tc):
        if self.dead:
            return
        self.triangle1 = drawing.Triangle(globals.ground_buffer)
        self.triangle2 = drawing.Triangle(globals.ground_buffer)
        #self.triangles = self.triangle1,self.triangle2

    def GetPos(self):
        if self.dead:
            return
        return Point(*self.body.position)/self.physics.scale_factor

    def GetAngle(self):
        if self.dead:
            return
        return self.body.angle

    def PhysUpdate(self):
        if self.dead:
            return
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


class DynamicBox(StaticBox):
    static = False
    health = 30
    def __init__(self,physics,bl,tr,tc):
        super(DynamicBox,self).__init__(physics,bl,tr,tc)

        self.body.SetMassFromShapes()
        physics.AddObject(self)

    def InitPolygons(self,tc):
        if self.dead:
            return
        self.quad = drawing.Quad(globals.quad_buffer,tc = tc)

    def PhysUpdate(self):
        if self.dead:
            return
        #Just set the vertices

        for i,vertex in enumerate(self.shape.vertices):
            screen_coords = Point(*self.body.GetWorldPoint(vertex))/self.physics.scale_factor
            self.quad.vertex[(i+3)%4] = (screen_coords.x,screen_coords.y,10)

    def Damage(self,amount):
        if globals.game_view.ship.state in modes.ShipStates.TUTORIAL:
            return
        self.health -= amount
        if self.health < 0:
            self.Destroy()

class Crate(DynamicBox):
    def Damage(self,amount):
        if globals.game_view.ship.state in modes.ShipStates.TUTORIAL:
            return
        self.health -= amount
        if self.health < 0:
            index = None
            globals.sounds.explode.play()
            if hasattr(globals.current_view.mode,'BoxDestroyed'):
                globals.current_view.mode.BoxDestroyed(self)
            self.Destroy()

class Bullet(DynamicBox):
    pass

class PlayerBullet(Bullet):
    isBullet = True
    damage = 10
    bullet_shape = Point(20,20)
    def __init__(self,parent,physics,bl,tr,tc,filter_group,mass):
        self.parent = parent
        self.filter_group = filter_group
        self.mass = mass
        super(PlayerBullet,self).__init__(physics,bl,tr,tc)

class SeekingMissile(Bullet):
    isBullet = True
    damage = 20
    bullet_shape = Point(20,20)
    def __init__(self,parent,physics,bl,tr,tc,filter_group,mass):
        self.parent = parent
        self.target = globals.game_view.ship
        self.filter_group = filter_group
        self.mass = mass
        super(SeekingMissile,self).__init__(physics,bl,tr,globals.game_view.atlas.TextureCoords(os.path.join(globals.dirs.sprites,'beam.png')))

    def Destroy(self):
        if self.parent:
            self.parent.DeleteBullet(self)
        super(SeekingMissile,self).Destroy()

    def PhysUpdate(self):
        super(SeekingMissile,self).PhysUpdate()
        #Apply a thrust in the direction of the target
        target_pos = self.target.GetPos()
        self.pos = self.GetPos()
        if not target_pos or not self.pos:
            return
        diff = target_pos - self.pos
        direction = self.GetAngle() + (math.pi/2)
        distance,angle = cmath.polar(complex(diff.x,diff.y))
        #angle = (angle - (math.pi/2) - self.GetAngle())%(math.pi*2)
        angle = (angle - direction)%(math.pi*2)
        
        if angle < (math.pi):
            #need to turn right, but by how much?
            amount = angle/math.pi
        else:
            amount = -(2*math.pi - angle)/math.pi

        desired_av = 10*amount
        f = 1 - abs(amount)
        current_speed = Point(*self.body.linearVelocity)
        if f < 0.8 or current_speed.length() > 80:
            desired_velocity = 0
            #Apply a force in the direction we're not going to slow us down
            force = Point(-current_speed.x,-current_speed.y)
            self.body.ApplyForce(tuple(force),self.body.position)
        else:
            desired_velocity = 1
            thrust = 20
            vector = cmath.rect(thrust,direction)
            self.body.ApplyForce((vector.real,vector.imag),self.body.position)

        
        torque = (desired_av - self.body.angularVelocity)
        self.body.ApplyTorque(torque)


class ShootingThing(DynamicBox):
    wait_for_bullets = False
    straight_up = False
    def Fire(self,pos):
        diff = pos - self.GetPos()
        distance,angle = cmath.polar(complex(diff.x,diff.y))
        angle = (angle - (math.pi/2) - self.GetAngle())%(math.pi*2)
        #0 = pi*2 is straight ahead, pi is behind.
        #so 0.75 pi to 1.25 pi is disallowed
        if angle <= self.min_shoot and angle >= self.max_shoot:
            return
        if distance < self.min_shoot_distance:
            #If you aim too close then the shots go wild
            return 
        if distance > self.max_shoot_distance:
            return
        if self.cooldown > self.t:
            return
        self.sound.play()
        self.fired = True
        self.cooldown = self.t + self.cooldown_time
        #if distance >= self.max_distance:
        #    return
        for offset in self.cannon_positions:
            if self.wait_for_bullets and len(self.bullets) >= self.max_bullets:
                continue
            bpos = Point(*self.body.GetWorldPoint(tuple(offset*self.physics.scale_factor)))/self.physics.scale_factor
            bullet = self.bullet_type(self,self.physics,bpos,bpos+self.bullet_type.bullet_shape,tc = self.parent.atlas.TextureCoords(os.path.join(globals.dirs.sprites,'blast.png')),filter_group = self.filter_group,mass = self.bullet_mass)
            #print dir(bullet.body)
            if self.straight_up:
                pass
            else:
                bullet.body.linearVelocity = tuple(Point(*self.body.linearVelocity) + (pos - bpos).unit_vector()*self.bullet_velocity)
            self.bullets.append(bullet)
            if len(self.bullets) > self.max_bullets:
                bullet = self.bullets.pop(0)
                bullet.Destroy()


class Trex(ShootingThing):
    mass          = 1
    health        = 100
    cooldown_time = 1000
    filter_group  = -2
    min_shoot     = 1.2*math.pi
    max_shoot     = 0.8*math.pi
    min_shoot_distance = 0
    max_shoot_distance = 2000
    max_bullets = 2
    bullet_mass = 0.04
    bullet_velocity = 80
    bullet_type = PlayerBullet
    cannon_positions = [Point(20,5)]
    sprite = 'trex.png'
    def __init__(self,parent,physics,bl,tr):
        self.parent = parent
        tc = self.parent.atlas.TextureCoords(os.path.join(globals.dirs.sprites,self.sprite))
        super(Trex,self).__init__(physics,bl,tr,tc)
        self.cooldown = 0
        self.bullets = []
        self.sound = globals.sounds.dino_blast
        self.sound.set_volume(0.01)
        self.death_sounds = globals.sounds.dino_die1,globals.sounds.dino_die2,globals.sounds.dino_die3

    def Damage(self,amount):
        if self.dead:
            return
        self.parent.ship.AddScore(amount)
        if globals.game_view.ship.state in [modes.ShipStates.TUTORIAL_MOVEMENT,
                                            modes.ShipStates.TUTORIAL_SHOOTING,
                                            modes.ShipStates.TUTORIAL_GRAPPLE,
                                            modes.ShipStates.TUTORIAL_TOWING]:
            return
        self.health -= amount
        if self.health < 0:
            random.choice(self.death_sounds).play()
            #globals.current_view.mode.BoxDestroyed(self)
            self.parent.RemoveTrex(self)
            self.Destroy()

    def Update(self,t):
        self.t = t
        if self.dead:
            return
        #If the player is above us in a 180 degree arc we'll try shooting at it
        player_pos = self.parent.ship.GetPos()
        if not player_pos:
            return
        self.Fire(player_pos)  

class Stegosaurus(Trex):
    bullet_type = SeekingMissile
    bullet_velocity = 10
    cooldown_time = 5000
    max_bullets = 1
    wait_for_bullets = True
    sprite = 'steg.png'

    def DeleteBullet(self,bullet):
        index = None
        for i,item in enumerate(self.bullets):
            if item is bullet:
                index = i
                break
        if index is not None:
            del self.bullets[index]
        

class PlayerShip(ShootingThing):
    max_shoot = 0.5*math.pi
    min_shoot = 1.5*math.pi
    max_distance = 300
    max_grapple  = 175
    min_shoot_distance = 30
    max_shoot_distance = 60000
    mass      = 3
    filter_group = -1
    cooldown_time = 400
    health = 10000000
    max_bullets = 10
    bullet_mass = 0.08
    bullet_velocity = 200
    bullet_type = PlayerBullet
    cannon_positions = [Point(20,5),Point(-20,5)]
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
        self.grapple_quad = drawing.Quad(globals.quad_buffer,tc = parent.atlas.TextureCoords(os.path.join(globals.dirs.sprites,'grapple.png')))
        self.beam_quad = drawing.Quad(globals.quad_buffer,tc = parent.atlas.TextureCoords(os.path.join(globals.dirs.sprites,'beam.png')))
        self.beam_quad.Disable()
        self.beam = False
        self.beam_power = 0
        self.beam_fired = False
        self.last_beam_update = 0
        self.grapple_quad.Disable()
        self.letter_duration = 30
        self.text_start = None
        self.fired = False
        self.joint = False
        self.t = 0
        self.grappled = False
        self.detached = False
        super(PlayerShip,self).__init__(physics,bl,tr,tc)
        self.bullets = []
        self.cooldown = 0
        self.text_limit = None
        self.sound = globals.sounds.blast
        self.sound.set_volume(0.4)
        self.health_text = ui.TextBox(parent = globals.screen_root,
                                      bl     = Point(0,0.9),
                                      tr     = Point(0.2,0.95)    ,
                                      text   = ' ',
                                      scale  = 2)
        self.score_text = ui.TextBox(parent = globals.screen_root,
                                      bl     = Point(0,0.85),
                                      tr     = Point(0.2,0.9)    ,
                                      text   = ' ',
                                      scale  = 2)
        self.beam_power_text = ui.TextBox(parent = globals.screen_root,
                                      bl     = Point(0,0.8),
                                      tr     = Point(0.3,0.85)    ,
                                      text   = ' ',
                                      scale  = 2)
        self.number_enemies_text = ui.TextBox(parent = globals.screen_root,
                                      bl     = Point(0,0.75),
                                      tr     = Point(0.3,0.80)    ,
                                      text   = ' ',
                                      scale  = 2)
        self.AdjustBeamPower(1000)
        self.SetHealth(500)
        globals.sounds.hurt.set_volume(0.2)
        self.SetScore(0)

    def Update(self,t = None):
        self.t = t
        selfpos = self.GetPos()
        if not selfpos:
            return
        self.text.SetPos(self.parent.GetRelative(selfpos))
        if self.text_start == None and t is not None:
            self.text_start = t+self.text_wait
        if t is not None:
            elapsed = t - self.text_start
            if elapsed > len(self.text.text)*self.letter_duration:
                self.text.EnableChars()
                if self.text_limit is not None and elapsed > self.text_limit:
                    self.SetText(' ',wait=0)
            elif elapsed > 0:
                num_enabled = int(float(elapsed)/self.letter_duration)
                self.text.EnableChars(num_enabled)

        self.AdjustBeamPower(3)
        if self.beam:
            self.AdjustBeamPower(-10)
            if self.beam_power <= 0:
                self.StopBeam()

        if self.beam:
            self.beam_fired = True
            self.beam_quad.Enable()
            angle = self.GetAngle()
            unit_vector = cmath.rect(1000,angle + math.pi/2)
            unit_vector = Point(unit_vector.real,unit_vector.imag)
            i = 0
            left_part  = Point(*self.body.GetWorldPoint(tuple(Point(-2,0.5))))/self.parent.physics.scale_factor
            right_part = Point(*self.body.GetWorldPoint(tuple(Point(2,0.5))))/self.parent.physics.scale_factor
            left_distant = left_part + unit_vector
            right_distant = right_part + unit_vector
            for i,vertex in enumerate((left_part,left_distant,right_distant,right_part,)):
                self.beam_quad.vertex[i] = (vertex.x,vertex.y,20)

            #Are we damaging anybody
            for item in self.parent.enemies + self.parent.game_mode.ooze_boxes:
                targets = [item]
                if hasattr(item,'bullets'):
                    targets.extend(item.bullets)
                for enemy in targets:
                    enemy_pos = enemy.GetPos()
                    if not enemy_pos:
                        continue
                    signs = []
                    for a,b in ((left_part,left_distant),(right_part,right_distant)):
                        sign = (b.x - a.x)*(enemy_pos.y-a.y) - (b.y - a.y)*(enemy_pos.x-a.x)
                        signs.append(sign)
                    if signs[0]*signs[-1] < 0:
                        #i.e the two signs were different, i.e the thing was on the different side of each line
                        #i.e it's between the lines
                        #Is it in front though?
                        a = left_part
                        b = right_part
                        sign = (b.x - a.x)*(enemy_pos.y-a.y) - (b.y - a.y)*(enemy_pos.x-a.x)
                        if sign > 0:
                            distance = (enemy_pos - left_part).length()
                            if distance < 600:
                                self.AddScore(10)
                                enemy.Damage(5)
                    

        else:
            self.beam_quad.Disable()
 

        #Set the vertices of the grapple_quad
        if not self.grappled:
            return
        #It's not quite as simple as converting physics vertices to quad vertices since the physics engine
        #isn't keeping track of the vertices we want to use. Instead get them from the bodies in question
        for i,(body,offset) in enumerate(((self.body,Point(-0.2,0)),
                                          (self.body,Point(0.2,0)),
                                          (self.touching.GetBody(),self.contact + Point(-0.2,0)),
                                          (self.touching.GetBody(),self.contact + Point(0.2,0)))):
            screen_coords = Point(*body.GetWorldPoint(tuple(offset)))/self.parent.physics.scale_factor
            self.grapple_quad.vertex[i] = (screen_coords.x,screen_coords.y,10)


    def UnGrapple(self):
        self.physics.world.DestroyJoint(self.joint)
        self.joint = None
        self.detached = True
        self.grapple_quad.Disable()
        self.touching = None
        self.contact = None
        self.grappled = False
        if self.child_joint:
            self.child_joint.parent_joint = None
            self.child_joint = None
            globals.sounds.ungrapple.play()

    def FireBeam(self):
        if self.beam == False:
            globals.sounds.beam.play()
            self.beam = True

    def StopBeam(self):
        if self.beam == True:
            globals.sounds.beam.stop()
            self.beam = False

    def Grapple(self,pos):
        if self.joint:
            self.UnGrapple()
            return
        diff = pos - self.GetPos()
        distance,angle = cmath.polar(complex(diff.x,diff.y))
        angle = (angle - (math.pi/2) - self.GetAngle())%(math.pi*2)
        #0 = pi*2 is straight ahead, pi is behind.
        #so 0.75 pi to 1.25 pi is allowed
        if not (angle <= self.min_shoot and angle >= self.max_shoot):
            return
        if distance > self.max_grapple:
            return

        #We need to determine if this point is in any objects...
        #We'll create a small AABB around the point, and get the list of potentially intersecting shapes,
        #then test each one to see if the point is inside it
        aabb = box2d.b2AABB()
        phys_pos = pos*self.physics.scale_factor
        #First of all make sure it's not inside us
        trans = box2d.b2XForm()
        trans.SetIdentity()
        p = phys_pos - Point(*self.body.position)
        if self.shapeI.TestPoint(trans,tuple(p)):
            return

        aabb.lowerBound.Set(phys_pos.x-0.1,phys_pos.y-0.1)
        aabb.upperBound.Set(phys_pos.x+0.1,phys_pos.y+0.1)
        (count,shapes) = self.physics.world.Query(aabb,10)
        for shape in shapes:
            trans = box2d.b2XForm()
            trans.SetIdentity()
            p = phys_pos - Point(*shape.GetBody().position)
            if shape.TestPoint(trans,tuple(p)):
                self.touching = shape
                self.contact  = p
                break
        else:
            self.touching = None
            self.contact  = None
        if not self.touching:
            return
        globals.sounds.grapple.play()
        #Tell the other body that it's in a joint with us so that 
        target = self.touching.userData
        if target == None:
            self.touching = None
            self.contact = None
            return

        target.parent_joint = self
        self.child_joint    = target

        joint = box2d.b2DistanceJointDef()
        joint.Initialize(self.body,self.touching.GetBody(),self.body.GetWorldCenter(),tuple(phys_pos))
        joint.collideConnected = True
        self.joint = self.physics.world.CreateJoint(joint)
        self.grappled = True
        self.grapple_quad.Enable()
            
    def SetText(self,text,wait = 1000,limit = None):
        self.text.SetText(text)
        self.text.EnableChars(0)
        self.text_start = None
        self.text_wait = wait
        if limit is not None:
            self.text_limit = limit

    def SetHealth(self,value):
        if value < 0:
            value = 0
        self.health = value
        self.health_text.SetText('health: %d' % self.health)

    def SetScore(self,value):
        self.score = value
        self.score_text.SetText('score: %d' % self.score)

    def SetEnemies(self,value):
        self.num_enemies = value
        self.number_enemies_text.SetText('Dinosaurs : %s' % self.num_enemies)

    def AddScore(self,value):
        if globals.game_view.ship.state in modes.ShipStates.TUTORIAL:
            return
        self.SetScore(self.score + value)

    def AdjustBeamPower(self,amount):
        self.beam_power += amount
        if self.beam_power < 0:
            self.beam_power = 0
        if self.beam_power > 1000:
            self.beam_power = 1000
        if self.t - self.last_beam_update > 100:
            self.beam_power_text.SetText('beam power : %d' % self.beam_power)
            self.last_beam_update = self.t

    def Damage(self,amount):
        if self.dead:
            return
        if globals.game_view.ship.state != modes.ShipStates.DESTROY_DINOS:
            return
        self.SetHealth(self.health - amount)
        globals.sounds.hurt.play()
        if self.health <= 0:
            globals.sounds.player_die.play()
            #globals.current_view.mode.BoxDestroyed(self)
            self.parent.mode = modes.GameOver(self.parent,win = False,score = self.score)

    def Disable(self):
        self.health_text.Disable()
        self.score_text.Disable()
        self.number_enemies_text.Disable()
        self.beam_power_text.Disable()

    def Enable(self):
        self.health_text.Enable()
        self.score_text.Enable()
        self.number_enemies_text.Enable()
        self.beam_power_text.Enable()
