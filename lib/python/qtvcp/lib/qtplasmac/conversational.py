'''
conversational.py

Copyright (C) 2019, 2020, 2021, 2022  Phillip A Carter
Copyright (C)       2020, 2021, 2022  Gregory D Carl

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc
51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'''

import os
from shutil import copy as COPY
from importlib import reload
from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QPushButton, QLabel, QLineEdit
from PyQt5.QtWidgets import QRadioButton, QButtonGroup, QComboBox, QCheckBox, QGroupBox
from qtvcp.core import Status, Action
from qtvcp.lib.qtplasmac import conv_settings as CONVSET
from qtvcp.lib.qtplasmac import conv_line as CONVLINE
from qtvcp.lib.qtplasmac import conv_circle as CONVCIRC
from qtvcp.lib.qtplasmac import conv_ellipse as CONVELLI
from qtvcp.lib.qtplasmac import conv_triangle as CONVTRIA
from qtvcp.lib.qtplasmac import conv_rectangle as CONVRECT
from qtvcp.lib.qtplasmac import conv_polygon as CONVPOLY
from qtvcp.lib.qtplasmac import conv_bolt as CONVBOLT
from qtvcp.lib.qtplasmac import conv_slot as CONVSLOT
from qtvcp.lib.qtplasmac import conv_star as CONVSTAR
from qtvcp.lib.qtplasmac import conv_gusset as CONVGUST
from qtvcp.lib.qtplasmac import conv_sector as CONVSECT
from qtvcp.lib.qtplasmac import conv_block as CONVBLCK

STATUS = Status()
ACTION = Action()

_translate = QCoreApplication.translate

def conv_setup(P, W):
    P.convSettingsChanged = False
    P.validShape = False
    P.savedSettings = {'origin':None, 'intext':None, 'in':None, 'out':None}
    W.preview = QPushButton(_translate('Conversational', 'PREVIEW'))
    W.undo = QPushButton(_translate('Conversational', 'RELOAD'))
    if not ACTION.prefilter_path:
        W.undo.setEnabled(False)
    conv_preview_button(P, W, False)
    P.convButtonState = {}
    P.convCommonButtons = ['new', 'save', 'send', 'settings']
    for w in P.convCommonButtons:
        P.convButtonState[w] = False
    if P.unitsPerMm == 1:
        P.unitCode = ['21', '0.25', 32]
    else:
        P.unitCode = ['20', '0.004', 1.26]
    P.ambles = 'G{} G64P{} G40 G49 G80 G90 G92.1 G94 G97'.format(P.unitCode[0], P.unitCode[1])
    CONVSET.load(P, W)
    # grid size is in inches
    W.conv_preview.grid_size = P.gridSize / P.unitsPerMm / 25.4
    W.conv_preview.set_current_view()
    W.conv_new.setEnabled(True)
    W.conv_save.setEnabled(False)
    W.conv_send.setEnabled(False)
    W.conv_settings.setEnabled(True)
    if ACTION.prefilter_path and P.fileOpened:
        COPY(P.filteredBkp, P.fNgc)
        COPY(P.filteredBkp, P.fNgcBkp)
        W.conv_preview.load(P.filteredBkp)
        W.conv_preview.set_current_view()
        conv_enable_tabs(P, W)
    else:
        conv_new_pressed(P, W, None)
    P.xOrigin = STATUS.get_position()[0][0]
    P.yOrigin = STATUS.get_position()[0][1]
    P.xSaved = '0.000'
    P.ySaved = '0.000'
    P.convBlock = [False, False]
    if not P.convWidgetsLoaded or P.developmentPin.get():
        conv_widgets(P, W)
    if not P.oldConvButton:
        conv_shape_request(P, W, 'conv_line', True)
    else:
        conv_shape_request(P, W, P.oldConvButton, True)

def conv_new_pressed(P, W, button):
    if button and (W.conv_save.isEnabled() or W.conv_send.isEnabled() or P.convPreviewActive):
        head = _translate('HandlerClass', 'Unsaved Shape')
        btn1 = _translate('HandlerClass', 'CONTINUE')
        btn2 = _translate('HandlerClass', 'CANCEL')
        msg0 = _translate('HandlerClass', 'You have an unsaved, unsent, or active previewed shape')
        msg1 = _translate('HandlerClass', 'If you continue it will be deleted')
        if not P.dialog_show_yesno(QMessageBox.Warning, '{}'.format(head), '{}\n\n{}\n'.format(msg0, msg1), '{}'.format(btn1), '{}'.format(btn2)):
            return
    if P.oldConvButton == 'conv_line':
        if W.lType.currentText() == _translate('Conversational', 'LINE POINT ~ POINT'):
            CONVLINE.set_line_point_to_point(P, W)
        elif W.lType.currentText() == _translate('Conversational', 'LINE BY ANGLE'):
            CONVLINE.set_line_by_angle(P, W)
        elif W.lType.currentText() == _translate('Conversational', 'ARC 3P'):
            CONVLINE.set_arc_3_points(P, W)
        elif W.lType.currentText() == _translate('Conversational', 'ARC 2P +RADIUS'):
            CONVLINE.set_arc_2_points_radius(P, W)
        elif W.lType.currentText() == _translate('Conversational', 'ARC ANGLE +RADIUS'):
            CONVLINE.set_arc_by_angle_radius(P, W)
    with open(P.fNgc, 'w') as outNgc:
        outNgc.write('(new conversational file)\nM2\n')
    COPY(P.fNgc, P.fTmp)
    COPY(P.fNgc, P.fNgcBkp)
    W.conv_preview.load(P.fNgc)
    W.conv_save.setEnabled(False)
    W.conv_send.setEnabled(False)
    P.validShape = False
    conv_preview_button(P, W, False)
    conv_enable_tabs(P, W)

def conv_save_pressed(P, W):
    head = _translate('HandlerClass', 'Save Error')
    with open(P.fNgc, 'r') as inFile:
        for line in inFile:
            if '(new conversational file)' in line:
                msg0 = _translate('HandlerClass', 'An empty file cannot be saved')
                P.dialog_show_ok(QMessageBox.Warning, '{}'.format(head), '{}\n'.format(msg0))
                return
    P.vkb_show()
    dlg = QFileDialog(W)
    dlg.setOptions(QFileDialog.DontUseNativeDialog)
    dlg.setAcceptMode(QFileDialog.AcceptSave)
    dlg.setNameFilters(['G-Code Files (*.ngc *.nc *.tap)', 'All Files (*)'])
    dlg.setDefaultSuffix('ngc')
    dlg.setDirectory(P.programPrefix)
    name = ''
    if dlg.exec_():
        name = dlg.selectedFiles()[0]
    if name:
        COPY(P.fNgc, name)
        W.conv_save.setEnabled(False)
        conv_enable_tabs(P, W)
    P.vkb_show(True)

def conv_settings_pressed(P, W):
    P.color_button_image(P.oldConvButton, P.foreColor)
    W[P.oldConvButton].setStyleSheet(\
            'QPushButton {{ background: {0} }} \
             QPushButton:pressed {{ background: {0} }}'.format(P.backColor))
    for w in P.convCommonButtons:
        P.convButtonState[w] = W['conv_{}'.format(w)].isEnabled()
        W['conv_{}'.format(w)].setEnabled(False)
    conv_clear_widgets(P, W, True)
    if P.developmentPin.get():
        reload(CONVSET)
    CONVSET.widgets(P, W, P.CONV)
    CONVSET.show(P, W)

def conv_send_pressed(P, W):
    COPY(P.fNgcBkp, P.fNgcSent)
    W.conv_send.setEnabled(False)
    W.conv_save.setEnabled(False)
    conv_enable_tabs(P, W)
    P.vkb_hide()
    ACTION.OPEN_PROGRAM(P.fNgcSent)

def conv_block_pressed(P, W):
    if not P.convSettingsChanged:
        if P.convPreviewActive and not conv_active_shape(P, W):
            return
        head = _translate('HandlerClass', 'Array Error')
        with open(P.fNgc) as inFile:
            for line in inFile:
                if '(new conversational file)' in line:
                    msg0 = _translate('HandlerClass', 'An empty file cannot be arrayed, rotated, or scaled')
                    P.dialog_show_ok(QMessageBox.Warning, '{}'.format(head), '{}\n'.format(msg0))
                    return
                # see if we can do something about NURBS blocks down the track
                # elif 'g5.2' in line.lower() or 'g5.3' in line.lower():
                #     head = _translate('HandlerClass', 'Scale Error')
                #     msg0 = _translate('HandlerClass', 'Cannot scale a GCode NURBS block')
                #     P.dialog_show_ok(QMessageBox.Warning, '{}'.format(head), '{}\n\n{}'.format(msg0, line))
                #     return
                elif 'M3' in line or 'm3' in line:
                    break
    conv_shape_request(P, W, W.sender().objectName(), False)

def conv_shape_request(P, W, shape, material):
    if shape == 'conv_line': module = CONVLINE
    elif shape == 'conv_circle': module = CONVCIRC
    elif shape == 'conv_ellipse': module = CONVELLI
    elif shape == 'conv_triangle': module = CONVTRIA
    elif shape == 'conv_rectangle': module = CONVRECT
    elif shape == 'conv_polygon': module = CONVPOLY
    elif shape == 'conv_bolt': module = CONVBOLT
    elif shape == 'conv_slot': module = CONVSLOT
    elif shape == 'conv_star': module = CONVSTAR
    elif shape == 'conv_gusset': module = CONVGUST
    elif shape == 'conv_sector': module = CONVSECT
    elif shape == 'conv_block': module = CONVBLCK
    else: return
    if P.developmentPin.get():
        reload(module)
    if not P.convSettingsChanged:
        if P.convPreviewActive and not conv_active_shape(P, W):
            return
        conv_preview_button(P, W, False)
    if material:
        W.conv_material.show()
    else:
        W.conv_material.hide()
    # we use exception handlers here as there may be no signals connected
    try:
        W.conv_material.currentTextChanged.disconnect()
    except:
        pass
    try:
        W.preview.pressed.disconnect()
    except:
        pass
    try:
        W.undo.pressed.disconnect()
    except:
        pass
    conv_button_color(P, W, shape)
    W.conv_settings.setEnabled(True)
    W.preview.setEnabled(True)
    if P.validShape:
        W.undo.setEnabled(True)
    W.add.setEnabled(False)
    conv_clear_widgets(P, W)
    # common starting parameters
    if P.convSettingsChanged == 0:
        W.intExt.setText('EXTERNAL')
        P.intExt = True
    if P.convSettingsChanged <= 1:
        if P.origin:
            W.centLeft.setText('CENTER')
        else:
            W.centLeft.setText('BTM LEFT')
        W.liEntry.setText('{}'.format(P.leadIn))
        W.loEntry.setText('{}'.format(P.leadOut))
    # call the shape
    module.widgets(P, W, P.CONV)
    P.convSettingsChanged = False

def conv_preview_button(P, W, state):
    P.convPreviewActive = state
    conv_enable_tabs(P, W)
    if state:
        W.preview.setStyleSheet('QPushButton {{ color: {} }} \
                                      QPushButton:disabled {{ color: {} }}' \
                                      .format(P.estopColor, P.disabledColor))
        W.conv_save.setEnabled(False)
        W.conv_send.setEnabled(False)
        W.undo.setText(_translate('HandlerClass', 'UNDO'))
    else:
        W.preview.setStyleSheet('QPushButton {{ color: {} }} \
                                      QPushButton:disabled {{ color: {} }}' \
                                      .format(P.foreColor, P.disabledColor))
        if P.validShape:
            W.conv_save.setEnabled(True)
            W.conv_send.setEnabled(True)
        W.undo.setText(_translate('HandlerClass', 'RELOAD'))
        if P.convWidgetsLoaded:
            W.add.setEnabled(False)

def conv_active_shape(P, W):
    btn1 = _translate('HandlerClass', 'CONTINUE')
    btn2 = _translate('HandlerClass', 'CANCEL')
    head = _translate('HandlerClass', 'Active Preview')
    msg0 = _translate('HandlerClass', 'You have an active previewed shape')
    msg1 = _translate('HandlerClass', 'If you continue it will be deleted')
    response = P.dialog_show_yesno(QMessageBox.Warning, '{}'.format(head), '{}\n\n{}\n'.format(msg0, msg1), '{}'.format(btn1), '{}'.format(btn2))
    if response:
        conv_undo_shape(P, W)
        conv_preview_button(P, W, False)
    return response

def conv_button_color(P, W, button):
    if P.oldConvButton:
        P.color_button_image(P.oldConvButton, P.foreColor)
        W[P.oldConvButton].setStyleSheet(\
                'QPushButton {{ background: {0} }} \
                 QPushButton:pressed {{ background: {0} }}'.format(P.backColor))
    P.oldConvButton = button
    P.color_button_image(button, P.backColor)
    W[button].setStyleSheet(\
            'QPushButton {{ background: {0} }} \
             QPushButton:pressed {{ background: {0} }}'.format(P.foreColor))

# this doesn't seem to be used
#def conv_enable_buttons(P, W, state):
#    for button in ['new', 'save', 'settings', 'send']:
#        W['conv_{}'.format(button)].setEnabled(state)

def conv_restore_buttons(P, W):
    for button in P.convCommonButtons:
        W['conv_{}'.format(button)].setEnabled(P.convButtonState[button])

def conv_enable_tabs(P, W):
    if W.conv_save.isEnabled() or P.convPreviewActive:
        for n in range(W.main_tab_widget.count()):
            if n != 1:
                W.main_tab_widget.setTabEnabled(n, False)
    else:
        for n in range(W.main_tab_widget.count()):
            W.main_tab_widget.setTabEnabled(n, True)
            # enabling tabs causes issues with the gcode widgets margin styles
            # so we refresh the style here as a workaround
            W.gcode_editor.setStyleSheet( \
                    'EditorBase{{ qproperty-styleColorMarginText: {} }}'.format(P.foreColor))
            W.gcode_display.setStyleSheet( \
                    'EditorBase{{ qproperty-styleColorMarginText: {} }}'.format(P.foreColor))

def conv_entry_changed(P, W, widget, overcut=False):
    name = widget.objectName()
    # enable/disable overcut
    if overcut:
        value = W.hdEntry.text() if overcut == 'bolt' else W.dEntry.text()
        try:
            dia = float(value)
        except:
            dia = 0
        if dia >= P.holeDiameter or dia == 0 or (P.intExt and overcut != 'bolt'):
            W.overcut.setChecked(False)
            W.overcut.setEnabled(False)
            W.ocEntry.setEnabled(False)
        else:
            W.overcut.setEnabled(True)
            W.ocEntry.setEnabled(True)
    if widget.text():
        if name in ['intEntry', 'hsEntry', 'cnEntry', 'rnEntry']:
            good = '0123456789'
        elif name in ['xsEntry', 'ysEntry', 'aEntry', 'coEntry', 'roEntry']:
            good = '-.0123456789'
        else:
            good = '.0123456789'
        out = ''
        for t in widget.text():
            if t in good and not(t == '-' and len(out) > 0) and not(t == '.' and t in out):
                out += t
        widget.setText(out)
        if widget.text() in ['', '.', '-', '-.']:
            return True
        try:
            a = float(widget.text())
            reply = False
        except:
            head = _translate('HandlerClass', 'Numeric Entry Error')
            msg0 = _translate('HandlerClass', 'An invalid entry has been detected')
            P.dialog_show_ok(QMessageBox.Warning, '{}'.format(head), '{}\n'.format(msg0))
            widget.setText('0')
            reply = True
        return reply
    else:
        return True
    if name == 'gsEntry':
        # grid size is in inches
        W.conv_preview.grid_size = float(widget.text()) / P.unitsPerMm / 25.4
        W.conv_preview.set_current_view()

def conv_is_float(entry):
    try:
        return True, float(entry)
    except:
        reply = -1 if entry else 0
        return False, reply

def conv_is_int(entry):
    try:
        return True, int(entry)
    except:
        reply = -1 if entry else 0
        return False, reply

def conv_undo_shape(P, W):
    # setup for a reload if required
    if not P.convPreviewActive:
        head = _translate('HandlerClass', 'Reload Request')
        btn1 = _translate('HandlerClass', 'CONTINUE')
        btn2 = _translate('HandlerClass', 'CANCEL')
        if ACTION.prefilter_path:
            name = os.path.basename(ACTION.prefilter_path)
            msg0 = _translate('HandlerClass', 'The original file will be loaded')
            msg1 = _translate('HandlerClass', 'If you continue all changes will be deleted')
            if not P.dialog_show_yesno(QMessageBox.Warning, '{}'.format(head), '{}:\n\n{}\n\n{}\n'.format(msg0, name, msg1), '{}'.format(btn1), '{}'.format(btn2)):
                return(True)
        else:
            msg0 = _translate('HandlerClass', 'An empty file will be loaded')
            msg1 = _translate('HandlerClass', 'If you continue all changes will be deleted')
            if not P.dialog_show_yesno(QMessageBox.Warning, '{}'.format(head), '{}\n\n{}\n'.format(msg0, msg1), '{}'.format(btn1), '{}'.format(btn2)):
                return(True)
        if ACTION.prefilter_path:
            COPY(ACTION.prefilter_path, P.fNgcBkp)
        else:
            with open(P.fNgcBkp, 'w') as outNgc:
                outNgc.write('(new conversational file)\nM2\n')
        P.validShape = False
        W.preview.setEnabled(True)
        W.undo.setEnabled(False)
        W.conv_save.setEnabled(False)
        W.conv_send.setEnabled(False)
    # undo the shape
    if os.path.exists(P.fNgcBkp):
        COPY(P.fNgcBkp, P.fNgc)
        W.conv_preview.load(P.fNgc)
        W.conv_preview.set_current_view()
        W.add.setEnabled(False)
        if not P.validShape:
            W.undo.setEnabled(False)
        if not P.convBlock[1]:
            P.convBlock[0] = False
        conv_preview_button(P, W, False)
        conv_enable_tabs(P, W)

def conv_add_shape_to_file(P, W):
    COPY(P.fNgc, P.fNgcBkp)
    try:
        if W.xsEntry.text():
            P.xSaved = W.xsEntry.text()
    except:
        pass
    try:
        if W.ysEntry.text():
            P.ySaved = W.ysEntry.text()
    except:
        pass
    # try:
    #     P.oSaved = W.centLeft.isChecked()
    # except:
    #     pass
    P.validShape = True
    W.add.setEnabled(False)
    W.conv_save.setEnabled(True)
    W.conv_send.setEnabled(True)
    conv_preview_button(P, W, False)
    conv_enable_tabs(P, W)

def conv_accept(P, W):
    P.validShape = True
    conv_preview_button(P, W, False)
    COPY(P.fNgc, P.fNgcBkp)
    W.conv_preview.load(P.fNgc)
    W.add.setEnabled(False)
    W.conv_save.setEnabled(True)
    W.conv_send.setEnabled(True)
    conv_enable_tabs(P, W)

def conv_clear_widgets(P, W, settings=False):
    for i in reversed(range(W.entries.count())):
        widget = W.entries.itemAt(i).widget()
        name = widget.objectName()
        if settings:
            if name == 'liEntry':
                P.savedSettings['in'] = widget.text()
            if name == 'loEntry':
                P.savedSettings['out'] = widget.text()
            if name == 'centLeft':
                P.savedSettings['origin'] = widget.text()
            if name == 'intExt':
                P.savedSettings['intext'] = widget.text()
        else:
            if isinstance(widget, QLineEdit) and \
               name not in ['liEntry', 'loEntry', 'xsEntry', 'ysEntry']:
                widget.setText('')
            if name in ['aEntry', 'oxEntry', 'oyEntry', 'rtEntry', 'coEntry', 'roEntry']:
                widget.setText('0.0')
            elif name in ['caEntry']:
                widget.setText('360')
            elif name in ['cnEntry', 'rnEntry']:
                widget.setText('1')
            elif name in ['scEntry']:
                name.setText('1.0')
            elif name in ['ocEntry']:
                widget.setText('{}'.format(4 * P.unitsPerMm))
        W.entries.removeWidget(widget)
        widget.setParent(None)
        try:
            widget.disconnect()
        except:
            pass

def conv_auto_preview_button(P, W, button):
    if button == 'intext':
        text = 'INTERNAL' if W.intExt.text() == 'EXTERNAL' else 'EXTERNAL'
        W.intExt.setText(text)
        P.intExt = True if text == 'EXTERNAL' else False
        W.intExt.setChecked(False)
    elif button == 'center':
        text = 'CENTER' if W.centLeft.text() == 'BTM LEFT' else 'BTM LEFT'
        W.centLeft.setText(text)
        W.centLeft.setChecked(False)

# create all required widgets without showing them
def conv_widgets(P, W):
    # common
    W.centLeft = QPushButton(_translate('Conversational', 'BTM LEFT'), objectName='centLeft')
    W.centLeft.setCheckable(True)
    W.intExt = QPushButton(_translate('Conversational', 'EXTERNAL'), objectName='intExt')
    W.intExt.setCheckable(True)
    W.liLabel = QLabel(_translate('Conversational', 'LEAD IN'))
    W.liEntry = QLineEdit(str(P.leadIn), objectName='liEntry')
    W.loLabel = QLabel(_translate('Conversational', 'LEAD OUT'))
    W.loEntry = QLineEdit(str(P.leadOut), objectName='loEntry')
    W.ctLabel = QLabel(_translate('Conversational', 'CUT TYPE'))
    W.spLabel = QLabel(_translate('Conversational', 'START'))
    W.xsLabel = QLabel(_translate('Conversational', 'X ORIGIN'))
    W.xsEntry = QLineEdit(str(P.xSaved), objectName='xsEntry')
    W.ysLabel = QLabel(_translate('Conversational', 'Y ORIGIN'))
    W.ysEntry = QLineEdit(str(P.ySaved), objectName='ysEntry')
    W.overcut = QPushButton(_translate('Conversational', 'OVER CUT'))
    W.overcut.setEnabled(False)
    W.overcut.setCheckable(True)
    W.ocLabel = QLabel(_translate('Conversational', 'OC LENGTH'))
    W.ocEntry = QLineEdit(objectName='ocEntry')
    W.ocEntry.setEnabled(False)
    W.ocEntry.setText('{}'.format(4 * P.unitsPerMm))
    W.add = QPushButton(_translate('Conversational', 'ADD'))
    W.lDesc = QLabel('')
    W.iLabel = QLabel()
    W.iLabel.setAlignment(Qt.AlignRight | Qt.AlignTop)
    W.aLabel = QLabel(_translate('Conversational', 'ANGLE'))
    W.aEntry = QLineEdit('0.0', objectName='aEntry')
    W.dLabel = QLabel(_translate('Conversational', 'DIAMETER'))
    W.dEntry = QLineEdit(objectName='')
    W.hdLabel = QLabel(_translate('Conversational', 'HOLE DIA'))
    W.hdEntry = QLineEdit()
    W.hLabel = QLabel('') # shared with different uses
    W.hEntry = QLineEdit() # shared with different uses
    W.caLabel = QLabel(_translate('Conversational', 'CIRCLE ANG'))
    W.caEntry = QLineEdit('360', objectName='caEntry')
    W.wLabel = QLabel(_translate('Conversational', 'WIDTH'))
    W.wEntry = QLineEdit(objectName='')
    W.rLabel = QLabel(_translate('Conversational', 'RADIUS'))
    W.rButton = QPushButton(_translate('Conversational', 'RADIUS'))
    W.rEntry = QLineEdit('')
    W.sLabel = QLabel() # shared with different uses
    W.sEntry = QLineEdit() # shared with different uses
    W.mCombo = QComboBox()
    W.mCombo.addItem(_translate('Conversational', 'CIRCUMSCRIBED'))
    W.mCombo.addItem(_translate('Conversational', 'INSCRIBED'))
    W.mCombo.addItem(_translate('Conversational', 'SIDE LENGTH'))
    W.r1Button = QPushButton(_translate('Conversational', 'RADIUS 1'))
    W.r1Entry = QLineEdit()
    W.r2Button = QPushButton(_translate('Conversational', 'RADIUS 2'))
    W.r2Entry = QLineEdit()
    W.r3Button = QPushButton(_translate('Conversational', 'RADIUS 3'))
    W.r3Entry = QLineEdit()
    W.r4Button = QPushButton(_translate('Conversational', 'RADIUS 4'))
    W.r4Entry = QLineEdit()
    W.lLabel = QLabel(_translate('Conversational', 'LENGTH'))
    W.lEntry = QLineEdit()
    W.pLabel = QLabel(_translate('Conversational', 'POINTS'))
    W.pEntry = QLineEdit(objectName='intEntry')
    W.odLabel = QLabel(_translate('Conversational', 'OUTER DIA'))
    W.odEntry = QLineEdit()
    W.idLabel = QLabel(_translate('Conversational', 'INNER DIA'))
    W.idEntry = QLineEdit()
    W.shLabel = QLabel(_translate('Conversational', 'SHAPE')) # shared with different uses
    # triangle
    W.AaLabel = QLabel(_translate('Conversational', 'A ANGLE'))
    W.AaEntry = QLineEdit()
    W.BaLabel = QLabel(_translate('Conversational', 'B ANGLE'))
    W.BaEntry = QLineEdit()
    W.CaLabel = QLabel(_translate('Conversational', 'C ANGLE'))
    W.CaEntry = QLineEdit()
    W.AlLabel = QLabel(_translate('Conversational', 'a LENGTH'))
    W.AlEntry = QLineEdit()
    W.BlLabel = QLabel(_translate('Conversational', 'b LENGTH'))
    W.BlEntry = QLineEdit()
    W.ClLabel = QLabel(_translate('Conversational', 'c LENGTH'))
    W.ClEntry = QLineEdit()
    # block
    W.ccLabel = QLabel(_translate('Conversational', 'COLUMNS'))
    W.cnLabel = QLabel(_translate('Conversational', 'NUMBER'))
    W.cnEntry = QLineEdit('1', objectName='cnEntry')
    W.coEntry = QLineEdit('0.0', objectName='coEntry')
    W.coLabel = QLabel(_translate('Conversational', 'OFFSET'))
    W.rrLabel = QLabel(_translate('Conversational', 'ROWS'))
    W.rnLabel = QLabel(_translate('Conversational', 'NUMBER'))
    W.rnEntry = QLineEdit('1', objectName='rnEntry')
    W.roEntry = QLineEdit('0.0', objectName='coEntry')
    W.roLabel = QLabel(_translate('Conversational', 'OFFSET'))
    W.oLabel = QLabel(_translate('Conversational', 'ORIGIN'))
    W.oxLabel = QLabel(_translate('Conversational', 'X OFFSET'))
    W.oxEntry = QLineEdit('0.0', objectName='xsEntry')
    W.oyEntry = QLineEdit('0.0', objectName='ysEntry')
    W.oyLabel = QLabel(_translate('Conversational', 'Y OFFSET'))
    W.ptLabel = QLabel(_translate('Conversational', 'PATTERN'))
    W.scLabel = QLabel(_translate('Conversational', 'SCALE'))
    W.scEntry = QLineEdit('1.0', objectName='scEntry')
    W.rtEntry = QLineEdit('0.0', objectName='aEntry')
    W.rtLabel = QLabel(_translate('Conversational', 'ROTATION'))
    W.mirror = QPushButton(_translate('Conversational', 'MIRROR'))
    W.flip = QPushButton(_translate('Conversational', 'FLIP'))
    # lines and arcs
    W.lType = QComboBox()
    W.label1 = QLabel()
    W.entry1 = QLineEdit()
    W.label2 = QLabel()
    W.entry2 = QLineEdit()
    W.label3 = QLabel()
    W.entry3 = QLineEdit()
    W.label4 = QLabel()
    W.entry4 = QLineEdit()
    W.label5 = QLabel()
    W.entry5 = QLineEdit()
    W.label6 = QLabel()
    W.entry6 = QLineEdit()
    W.g23Arc = QPushButton('CW - G2')
    W.g23Arc.setCheckable(True)
    # settings
    W.preLabel = QLabel(_translate('Conversational', 'PREAMBLE'))
    W.preEntry = QLineEdit()
    W.pstLabel = QLabel(_translate('Conversational', 'POSTAMBLE'))
    W.pstEntry = QLineEdit()
    W.llLabel = QLabel(_translate('Conversational', 'LEAD LENGTHS'))
    W.shEntry = QLineEdit()
    W.hsEntry = QLineEdit()
    W.hsLabel = QLabel(_translate('Conversational', 'SPEED %'))
    W.pvLabel = QLabel(_translate('Conversational', 'PREVIEW'))
    W.gsLabel = QLabel(_translate('Conversational', 'GRID SIZE'))
    W.gsEntry = QLineEdit()
    W.save = QPushButton(_translate('Conversational', 'SAVE'))
    W.reload = QPushButton(_translate('Conversational', 'RELOAD'))
    W.cExit = QPushButton(_translate('Conversational', 'EXIT'))
    if not W.lType.count():
        W.lType.addItem(_translate('Conversational', 'LINE POINT ~ POINT'))
        W.lType.addItem(_translate('Conversational', 'LINE BY ANGLE'))
        W.lType.addItem(_translate('Conversational', 'ARC 3P'))
        W.lType.addItem(_translate('Conversational', 'ARC 2P +RADIUS'))
        W.lType.addItem(_translate('Conversational', 'ARC ANGLE +RADIUS'))
    if not W.mCombo.count():
        W.mCombo.addItem(_translate('Conversational', 'CIRCUMSCRIBED'))
        W.mCombo.addItem(_translate('Conversational', 'INSCRIBED'))
        W.mCombo.addItem(_translate('Conversational', 'SIDE LENGTH'))
    P.convWidgetsLoaded = True
