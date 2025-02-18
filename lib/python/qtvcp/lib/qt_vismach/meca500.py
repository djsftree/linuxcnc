#!/usr/bin/python3
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

#--------------------------------------------------------------------------
# Visualization model of the 6axis Mecademic Meca500 Robot
#--------------------------------------------------------------------------

import os
import hal
from qtvcp.lib.qt_vismach.qt_vismach import *
from typing import Any, List

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'meca500_obj')

NUM_JOINTS = 6
NUM_LINKS = 7

COL_MACH =  [0.9, 0.9, 0.9,  1]  # Greyish?
COL_RED =   [  1,   0,   0,  1]
COL_BLUE =  [  0,   0,   1,  1]
COL_GREEN = [  0,   1,   0,  1]

COL_X_AXIS = COL_RED
COL_Y_AXIS = COL_GREEN
COL_Z_AXIS = COL_BLUE

X_TRANS = [0,      0,    0,  61.5,  58.5,  70.0,   0,   0]
Z_TRANS = [0,    135,  135,     38,    0,     0,   0,   100]

COLOURS = [COL_MACH] * NUM_LINKS
# Link Debugging Colour
COLOURS[4] = [0.2, 0.6, 0.2, 1]

TH_ROT = [0, 1, 1, 1, 1, 1, 1, 0]
X_ROT =  [0, 0, 0, 0, 1, 0, 1, 0]
Y_ROT =  [0, 0, 1, 1, 0, 1, 0, 0]
Z_ROT =  [0, 1, 0, 0, 0, 0, 0, 0]

def print_debug(msg):
    print(f"MECAGUI: {msg}")


c = hal.component("meca500gui")
for i in range(NUM_JOINTS):
    c.newpin(f"joint{i + 1}", hal.HAL_FLOAT, hal.HAL_IN)
c.newpin("tool_length", hal.HAL_FLOAT, hal.HAL_IN)
c.newpin("plotclear", hal.HAL_BIT, hal.HAL_IN)
c.ready()

work = Capture()
tooltip = Capture()
tool = Capture()
tool = Collection([tooltip, tool])

# create visual tool coordinates axes	
xaxis = Color(COL_X_AXIS, [CylinderX(0, 2, 70, 2)])
yaxis = Color(COL_Y_AXIS, [CylinderY(0, 2, 70, 2)])
zaxis = Color(COL_Z_AXIS, [CylinderZ(0, 2, 70, 2)])
finger1 = Collection([tool, xaxis, yaxis, zaxis])

# debug use the joint6 fixed surface as tool tip
# finger1 = Translate([finger1], 84.82, -12.5, 21)

try:  # Expect files in working directory
    links: List[Any] = [None] * 8
    links[7] = AsciiOBJ(filename=f"{MODEL_DIR}/spindle_assembly.obj")
    links[7] = Color(COL_MACH, [links[7]])
    print_debug(f"Loaded: {MODEL_DIR}/spindle_assembly.obj")

    for i in range(NUM_LINKS):
        links[i] = load_file(f"{MODEL_DIR}/meca500_link{i + 1}.obj")
        links[i] = Color(COLOURS[i], [links[i]])
        print_debug(f"Loaded: {MODEL_DIR}/meca500_link{i + 1}.obj ")

    table = AsciiOBJ(filename=f"{MODEL_DIR}/meca500_table.obj")
    print_debug(f"Loaded: {MODEL_DIR}/meca500_table.obj")
except Exception as detail:
    print(detail)
    raise SystemExit("meca500 requires files in models directory")


# create spindle assembly
links[7] = Collection([finger1, links[7]])
links[7] = HalRotate([links[7]], c, f"joint{6}", TH_ROT[6], X_ROT[6], Y_ROT[6], Z_ROT[6])

fingerL = Collection([xaxis, yaxis, zaxis])

for i in range(NUM_LINKS - 1, 0, -1):
	
	links[i] = Collection([links[i+1], links[i], fingerL])
	links[i] = Translate([links[i]], X_TRANS[i], 0, Z_TRANS[i])
	links[i] = HalRotate([links[i]], c, f"joint{i}", TH_ROT[i], X_ROT[i], Y_ROT[i], Z_ROT[i])

links[0] = Translate([links[0]], 0, 0, 91)
meca500 = Collection([links[1], links[0]])

# create table with a debug finger
xaxis0 = Color(COL_X_AXIS, [CylinderX(0, 2, 200, 2)])
yaxis0 = Color(COL_Y_AXIS, [CylinderY(0, 2, 200, 2)])
zaxis0 = Color(COL_Z_AXIS, [CylinderZ(0, 2, 300, 2)])
coordw = Collection([xaxis0, yaxis0, zaxis0])
table = Color(COL_MACH, [table])
table = Collection([table, coordw])

myhud = Hud()
myhud.debug_track = 1
myhud.show("right-click to reset. scroll for Z")

model = Collection([tooltip, meca500, table, work])

# we want to embed with qtvcp so build a window to display
# the model
class Window(QWidget):

    def __init__(self):
        super(Window, self).__init__()
        self.glWidget = GLWidget()
        v = self.glWidget
        v.set_latitudelimits(-180, 180)

        v.hud = myhud
        # HUD needs to know where to draw
        v.hud.app = v

        world = Capture()

        v.model = Collection([model, world])
        size = 75
        v.distance = size * 3
        v.near = size * 0.01
        v.far = size * 10.0
        v.tool2view = tooltip
        v.world2view = world
        v.work2view = work

        mainLayout = QHBoxLayout()
        mainLayout.setContentsMargins(0,0,0,0)
        mainLayout.addWidget(self.glWidget)
        self.setLayout(mainLayout)


# but it you call this directly it should work too
# It just makes a qtvcp5 window that is defined in qt_vismach.py
# parameter list:
# final model name must include all parts you want to use
# tooltip (special for tool tip inclusuion)
# work (special for work part inclusion)
# size of screen (bigger means more zoomed out to show more of machine)
# hud None if no hud
# last 2 is where view point source is.

if __name__ == '__main__':
    main(model, tooltip, work, size=75, hud=myhud, lat=-75, lon=215)
