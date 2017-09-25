# -*- coding: utf-8 -*-
"""
Demonstrate use of GLLinePlotItem to draw cross-sections of a surface.

"""
import sys
sys.path.append('./pyqtgraph/examples')

## Add path to library (just for examples; you do not need this)
import initExample

from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.opengl as gl
import pyqtgraph as pg
import numpy as np
from OpenGL.GL import glViewport

app = QtGui.QApplication([])


class RetinaFixedGLViewWidget(gl.GLViewWidget):
    ''' This code is copy-pasted from the original, but makes use of the width and height passed to resizeGL.
        This makes the ouput look correct on retina display macs.
    '''

    def resizeGL(self, width, height):
        self._width = width
        self._height = height

    def getViewport(self):
        vp = self.opts['viewport']
        if vp is None:
            return (0, 0, self._width, self._height)
        else:
            return vp

    def projectionMatrix(self, region=None):
        # Xw = (Xnd + 1) * width/2 + X
        if region is None:
            region = (0, 0, self._width, self._height)
        
        x0, y0, w, h = self.getViewport()
        dist = self.opts['distance']
        fov = self.opts['fov']
        nearClip = dist * 0.001
        farClip = dist * 1000.

        r = nearClip * np.tan(fov * 0.5 * np.pi / 180.)
        t = r * h / w

        # convert screen coordinates (region) to normalized device coordinates
        # Xnd = (Xw - X0) * 2/width - 1
        ## Note that X0 and width in these equations must be the values used in viewport
        left  = r * ((region[0]-x0) * (2.0/w) - 1)
        right = r * ((region[0]+region[2]-x0) * (2.0/w) - 1)
        bottom = t * ((region[1]-y0) * (2.0/h) - 1)
        top    = t * ((region[1]+region[3]-y0) * (2.0/h) - 1)

        tr = QtGui.QMatrix4x4()
        tr.frustum(left, right, bottom, top, nearClip, farClip)
        return tr




w = RetinaFixedGLViewWidget()
w.opts['distance'] = 40
w.show()
w.setWindowTitle('pyqtgraph example: GLLinePlotItem')

gx = gl.GLGridItem()
gx.rotate(90, 0, 1, 0)
gx.translate(-10, 0, 0)
w.addItem(gx)
gy = gl.GLGridItem()
gy.rotate(90, 1, 0, 0)
gy.translate(0, -10, 0)
w.addItem(gy)
gz = gl.GLGridItem()
gz.translate(0, 0, -10)
w.addItem(gz)

def fn(x, y):
    return np.cos((x**2 + y**2)**0.5)

n = 51
y = np.linspace(-10,10,n)
x = np.linspace(-10,10,100)
for i in range(n):
    yi = np.array([y[i]]*100)
    d = (x**2 + yi**2)**0.5
    z = 10 * np.cos(d) / (d+1)
    pts = np.vstack([x,yi,z]).transpose()
    plt = gl.GLLinePlotItem(pos=pts, color=pg.glColor((i,n*1.3)), width=(i+1)/10., antialias=True)
    w.addItem(plt)
    

# The width and height as the widget sees them
print(type(w.width()), type(w.height()))


## Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
