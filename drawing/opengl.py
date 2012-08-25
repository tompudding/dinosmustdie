import numpy

class QuadBuffer(object):
    num_vertices = 4
    def __init__(self,size):
        self.vertex_data  = numpy.zeros((size*self.num_vertices,3),numpy.float32)
        self.tc_data      = numpy.zeros((size*self.num_vertices,2),numpy.float32)
        self.colour_data = numpy.ones((size*self.num_vertices,4),numpy.float32) #RGBA default is white opaque
        self.indices      = numpy.zeros(size*self.num_vertices,numpy.uint32)  #de
        self.size = size
        for i in xrange(size*self.num_vertices):
            self.indices[i] = i
        self.current_size = 0
        self.max_size     = size*self.num_vertices
        self.vacant = []

    def next(self):
        if len(self.vacant) > 0:
            #for a vacant one we blatted the indices, so we should reset those...
            out = self.vacant.pop()
            for i in xrange(self.num_vertices):
                self.indices[out+i] = out+i
            return out
            
        out = self.current_size
        self.current_size += self.num_vertices
        if self.current_size >= self.max_size:
            raise carpets
            # self.max_size *= 2
            # self.vertex_data.resize( (self.max_size,3) )
            # self.tc_data.resize    ( (self.max_size,2) )
        return out

    def truncate(self,n):
        self.current_size = n
        for i in xrange(self.size*self.num_vertices):
            self.indices[i] = i
        self.vacant = []

    def RemoveQuad(self,index):
        self.vacant.append(index)
        for i in xrange(self.num_vertices):
            self.indices[index+i] = 0

class TriangleBuffer(QuadBuffer):
    num_vertices = 3


class PolyVertex(object):
    def __init__(self,index,buffer):
        self.index = index
        self.buffer = buffer
    
    def __getitem__(self,i):
        if isinstance(i,slice):
            start,stop,stride = i.indices(len(self.buffer)-self.index)
            return self.buffer[self.index+start:self.index+stop:stride]
        return self.buffer[self.index + i]

    def __setitem__(self,i,value):
        if isinstance(i,slice):
            start,stop,stride = i.indices(len(self.buffer)-self.index)
            self.buffer[self.index + start:self.index+stop:stride] = value
        else:
            self.buffer[self.index + i] = value

class Quad(object):
    num_vertices = 4
    def __init__(self,source,vertex = None,tc = None,colour_info = None,index = None):
        if index == None:
            self.index = source.next()
        else:
            self.index = index
        self.source = source
        self.vertex = PolyVertex(self.index,source.vertex_data)
        self.tc     = PolyVertex(self.index,source.tc_data)
        self.colour = PolyVertex(self.index,source.colour_data)
        if vertex != None:
            self.vertex[0:self.num_vertices] = vertex
        if tc != None:
            self.tc[0:self.num_vertices] = tc
        self.old_vertices = None
        self.deleted = False

    def Delete(self):
        self.source.RemoveQuad(self.index)
        self.deleted = True

    def Disable(self):
        #It still gets drawn, but just in a single dot in a corner.
        #not very efficient!
        #don't disable again if already disabled
        if self.deleted:
            return
        if self.old_vertices == None:
            self.old_vertices = numpy.copy(self.vertex[0:self.num_vertices])
            for i in xrange(self.num_vertices):
                self.vertex[i] = (0,0,0)

    def Enable(self):
        if self.deleted:
            return
        if self.old_vertices != None:
            for i in xrange(self.num_vertices):
                self.vertex[i] = self.old_vertices[i]
            self.old_vertices = None

    def SetVertices(self,bl,tr,z):
        if self.deleted:
            return
        assert(self.num_vertices == 4)
        setvertices(self.vertex,bl,tr,z)
        if self.old_vertices != None:
            self.old_vertices = numpy.copy(self.vertex[0:self.num_vertices])
            for i in xrange(self.num_vertices):
                self.vertex[i] = (0,0,0)
    
    def SetColour(self,colour):
        if self.deleted:
            return
        setcolour(self.colour,colour,self.num_vertices)

    def SetColours(self,colours):
        if self.deleted:
            return
        for current,target in zip(self.colour,colours):
            for i in xrange(self.num_vertices):
                current[i] = target[i]

    def SetTextureCoordinates(self,tc):
        self.tc[0:self.num_vertices] = tc

class Triangle(Quad):
    num_vertices = 3

def setvertices(vertex,bl,tr,z):
    vertex[0] = (bl.x,bl.y,z)
    vertex[1] = (bl.x,tr.y,z)
    vertex[2] = (tr.x,tr.y,z)
    vertex[3] = (tr.x,bl.y,z)

def setcolour(colour,value,num_vertices):
    for i in xrange(num_vertices):
        for j in xrange(num_vertices):
            colour[i][j] = value[j]

def setcolours(colour,values,num_vertices):
    for i in xrange(num_vertices):
        for j in xrange(num_vertices):
            colour[i][j] = values[i][j]
