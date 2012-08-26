from OpenGL.GL import *
import random,numpy,cmath,math,pygame

import ui,globals,drawing,os,copy
from globals.types import Point
import Box2D as box2d
import actors
import game_view

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

    def MouseButtonDown(self,pos,button):
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
            self.parent.mode = self.parent.game_mode = GameMode(self.parent)
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

class Keys(object):
    UP    = 1
    LEFT  = 2
    RIGHT = 4
    ALL   = UP | LEFT | RIGHT

class ShipStates(object):
    TUTORIAL_MOVEMENT = 0
    TUTORIAL_SHOOTING = 1
    TUTORIAL_GRAPPLE  = 2
    TUTORIAL_TOWING   = 3
    DESTROY_CRATES    = 4
    WAIT_SPACE        = 5
    DINO_TEXT         = 6
    DESTROY_DINOS     = 7
    TUTORIAL = set([TUTORIAL_MOVEMENT,TUTORIAL_SHOOTING,TUTORIAL_GRAPPLE,TUTORIAL_TOWING])

class GameMode(Mode):
    def __init__(self,parent):
        self.parent            = parent
        self.thrust            = None
        self.rotate            = None
        self.pi2               = math.pi/2
        self.ooze_boxes        = []
        self.up_keys           = [0x111,ord('w')]
        self.left_keys         = [0x114,ord('a')]
        self.right_keys        = [0x113,ord('d')]
        self.parent.ship.SetText('Use the W and D keys to rotate the ship, and A to provide thrust') 
        self.parent.ship.state = ShipStates.TUTORIAL_MOVEMENT
        self.tutorial_handlers = {ShipStates.TUTORIAL_MOVEMENT : self.TutorialMovement,
                                  ShipStates.TUTORIAL_SHOOTING : self.TutorialShooting,
                                  ShipStates.TUTORIAL_GRAPPLE  : self.TutorialGrapple,
                                  ShipStates.TUTORIAL_TOWING   : self.TutorialTowing,
                                  ShipStates.DESTROY_CRATES    : self.LevelDestroyCrates,
                                  ShipStates.DESTROY_DINOS     : self.LevelDestroyDinos}
        self.all_time_key_mask = 0
        self.key_mask          = 0
        self.num_boxes         = 3
        self.skip_text         = ui.TextBox(parent = globals.screen_root,
                                            bl     = Point(0.8,0.8),
                                            tr     = Point(1,1)    ,
                                            text   = 'Press Q to skip tutorial',
                                            scale  = 2)
        
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
        if key == ord('q'):
            if self.parent.ship.state in ShipStates.TUTORIAL:
                self.EndTutorial()
        if key == pygame.locals.K_SPACE:
            if self.parent.ship.state == ShipStates.WAIT_SPACE:
                self.parent.ship.state = ShipStates.DINO_TEXT
                self.StartDinos()
        #elif key == 0x

    def KeyUp(self,key):
        if key in self.up_keys:
            self.thrust = None
            self.key_mask          &= ~Keys.UP
        if key in self.left_keys:
            self.key_mask          &= ~Keys.LEFT
        if key in self.right_keys:
            self.key_mask          &= ~Keys.RIGHT

    def StartDinos(self):
        self.parent.mode = Titles(self.parent)

    def MouseButtonDown(self,pos,button):
        if button == 1:
            self.parent.ship.Fire(pos)
        if button == 3:
            self.parent.ship.Grapple(pos)
        return False,False

    def TutorialMovement(self,t):
        if self.all_time_key_mask == Keys.ALL:
            self.parent.ship.SetText('Aim with the mouse and left click to shoot',wait=0)
            self.parent.ship.state = ShipStates.TUTORIAL_SHOOTING
            self.parent.ship.fired = False

    def TutorialShooting(self,t):
        if self.parent.ship.fired:
            self.parent.ship.SetText('Grapple by right-clicking on a target behind your ship',wait=0)
            self.parent.ship.state = ShipStates.TUTORIAL_GRAPPLE
            self.parent.ship.grappled = False

    def TutorialGrapple(self,t):
        if self.parent.ship.grappled:
            self.parent.ship.SetText('Detach the grapple by right clicking again',wait=0)
            self.parent.ship.state = ShipStates.TUTORIAL_TOWING
            self.parent.ship.detached = False

    def TutorialTowing(self,t):
        if self.parent.ship.detached:
            self.EndTutorial()

    def EndTutorial(self):
        self.parent.ship.SetText('Great! Now to get evolution started, lift some crates of primordial goo into the air and destroy them!',wait=0,limit=6000)
        self.skip_text.Disable()
        self.parent.ship.state = ShipStates.DESTROY_CRATES

    def LevelDestroyCrates(self,t):
        pass

    def LevelDestroyDinos(self,t):
        pass

    def BoxDestroyed(self,box):
        if self.parent.ship.state != ShipStates.DESTROY_CRATES:
            #We don't care
            return
        #temporary cheat:
        if 0:
            p = box.GetPos()
            target = 750
            if not p:
                #Not sure when this would happen
                return
            if p.y < target:
                self.parent.ship.SetText('That was too low by %2.f metres, try again but higher!' % (target - p.y),wait=0,limit=6000)
                return
            self.num_boxes -= 1
            if self.num_boxes > 0:
                self.parent.ship.SetText('Good! %d box%s left!' % (self.num_boxes,'' if self.num_boxes == 1 else 'es'),wait=0,limit=4000)
        else:
            self.parent.ship.SetText('Great. Press <space> to wait 3 billion years for life to evolve',wait=0)
            self.parent.ship.state = ShipStates.WAIT_SPACE
                                     
            

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

class TitleStages(object):
    STARTED  = 0
    TEXT     = 1
    SCROLL   = 2
    COMPLETE = 3
    WAIT     = 4


class Titles(Mode):
    blurb = "After waiting for 3 billion years you starting to seriously fancy some gloopy {gloop}. Unfortunately for you (and the galaxy) you have overslept by 100 million years and without your guiding tentacle Dinosaurs have risen to dominate the planet. Dinosaurs *hate* {gloop}, and so...".format(gloop = gloop_name)
    def __init__(self,parent):
        self.parent          = parent
        self.start           = None
        self.skipped_text    = False
        self.continued       = False
        self.letter_duration = 20
        self.blurb_text      = None
        self.stage           = TitleStages.STARTED
        self.handlers        = {TitleStages.STARTED : self.Startup,
                                TitleStages.TEXT    : self.TextDraw,
                                TitleStages.SCROLL  : self.Wait,
                                TitleStages.WAIT    : self.Wait}


    def Update(self,t):
        if self.start == None:
            self.start = t
        self.elapsed = t - self.start
        self.stage = self.handlers[self.stage](t)
        if self.stage == TitleStages.COMPLETE:
            #Lets add some dinosaurs
            for i in xrange(20):
                self.parent.AddTrex()
            self.parent.ship.state = ShipStates.DESTROY_DINOS
            self.parent.mode = self.parent.game_mode

    def Startup(self,t):
        self.view_target = Point(self.parent.ship.GetPos().x-globals.screen.x*0.5,globals.screen.y*2)
        self.parent.viewpos.SetTarget(self.view_target,
                                      t,
                                      rate = 0.4,
                                      callback = self.Scrolled)
        return TitleStages.WAIT

    def Wait(self,t):
        return self.stage

    def SkipText(self):
        if self.blurb_text:
            self.skipped_text = True
            self.blurb_text.EnableChars()
            self.title_text.Enable()


    def Scrolled(self,t):
        print 'Scrolled!'
        bl = self.parent.GetRelative(self.view_target)
        tr = bl + self.parent.GetRelative(globals.screen)
        self.blurb_text = ui.TextBox(parent = self.parent,
                                     bl     = bl         ,
                                     tr     = tr         ,
                                     text   = self.blurb ,
                                     textType = drawing.texture.TextTypes.WORLD_RELATIVE,
                                     scale  = 3)
        self.title_text = ui.TextBox(parent = self.parent,
                                     bl     = bl + self.parent.GetRelative(Point(globals.screen.x*0.25,0)),
                                     tr     = bl + self.parent.GetRelative(Point(globals.screen.x,globals.screen.y*0.6)),
                                     text   = 'Dinosaurs\n   Must\n   Die!!!',
                                     textType = drawing.texture.TextTypes.WORLD_RELATIVE,
                                     scale  = 8)
        self.start = t
        self.blurb_text.EnableChars(0)
        self.title_text.Disable()
        self.stage = TitleStages.TEXT

    def TextDraw(self,t):
        if not self.skipped_text:
            if self.elapsed < len(self.blurb_text.text)*self.letter_duration:
                num_enabled = int(self.elapsed/self.letter_duration)
                self.blurb_text.EnableChars(num_enabled)
            elif self.elapsed - len(self.blurb_text.text)*self.letter_duration > 1000:
                self.title_text.Enable()
                self.skipped_text = True
        elif self.continued:
            self.parent.viewpos.SetTarget(self.parent.ship.GetPos()-(globals.screen*0.5),t,rate = 0.4,callback = self.ScrolledDown)
            #self.parent.viewpos.Follow(t,self.parent.ship)
            return TitleStages.COMPLETE
        return TitleStages.TEXT

    def ScrolledDown(self,t):
        """When the view has finished scrolling, marry it to the ship"""
        self.parent.viewpos.Follow(t,self.parent.ship)
        self.blurb_text.Delete()
        self.title_text.Delete()

    def KeyDown(self,key):
        #if key in [13,27,32]: #return, escape, space
        if not self.skipped_text:
            self.SkipText()
        else:
            self.continued = True

    def MouseButtonDown(self,pos,button):
        self.KeyDown(0)
        return False,False



    
    def Draw(self):
        pass
