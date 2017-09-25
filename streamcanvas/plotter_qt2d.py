''' An implementation of the plotter components in Qt via pyqtgraph '''

import numpy
import random
import re
import sys

import pyqtgraph
from pyqtgraph.GraphicsScene import GraphicsScene
from pyqtgraph.Qt import QtGui, QtCore

from streamcanvas.communication import read_response_and_data, update_gobbler_dropping_mode
from streamcanvas.constants import *
from streamcanvas.options import DisplayMode, OPTIONS
from streamcanvas.utils import pairs, sc_print


class StreamCanvasWindow(pyqtgraph.GraphicsWindow):
    ''' A graphics window with additional controls needed by StreamCanvas '''

    def __init__(self, controller):
        super().__init__()
        self._controller = controller
        self._quit_keys = (QtCore.Qt.Key_Escape, QtCore.Qt.Key_Q)
        # TODO fiddle with range adjusting, aspect fixing?
        # TODO maintain aspect on resize?
        # self.setAspectLocked(True)
        # self.setRange(QtCore.QRectF(-10, -10, 30, 30))

    def keyPressEvent(self, event):
        if event.key() in self._quit_keys:
            sc_print('Quitting')
            app = QtGui.QApplication.instance()
            app.quit()

        # The 'p' key will (un)pause. Specifically it will trigger the transitions
        #    live           -> inspect_drop
        #    inspect_drop   -> live
        #    inspect_nodrop -> live
        elif event.key() == QtCore.Qt.Key_P:
            current_to_new_mode = {DisplayMode.live: DisplayMode.inspect_drop,
                                   DisplayMode.inspect_drop: DisplayMode.live,
                                   DisplayMode.inspect_nodrop: DisplayMode.live}

            new_mode = current_to_new_mode[OPTIONS.mode]
            sc_print('Switching to', new_mode)
            OPTIONS.mode = new_mode

            # We may have updated the dropping mode, so inform the gobbler
            update_gobbler_dropping_mode()

        # If we're in either of the inspection modes, this should cause us to request a new frame, unless we're
        # still part way through receiving one, in which case it should do nothing
        elif event.key() == QtCore.Qt.Key_N:
            # Do nothing in live mode
            if OPTIONS.mode is DisplayMode.live:
                return

            advance_made = self._controller.request_frame_advance()
            if advance_made and OPTIONS.verbose:
                sc_print('Advancing frame')


class StreamGraphicsObject(QtGui.QGraphicsObject):
    ''' A graphics view that understands streamcanvas protocol '''
    def __init__(self, controller):
        super().__init__()
        self._controller = controller
        self._frame_data = ''

        GraphicsScene.registerObject(self)

        # This will be a list of function calls that expect to be called with the painter object only
        self._painter_function_calls = []

        # The current view rectangle should increase as things are drawn. This is also used as the bounding rectangle,
        # since pyqtgraph setRange appears to do strange things if the bounding rect varies independently of the
        # view rect.
        # We *must* have a default bounding rectangle before we have any data, otherwise Qt will fall over.
        self._current_view_rect = QtCore.QRectF(0, 0, 1, 1)

        # Specify the point extent as a QPoint - think of this as a delta that we add and subtract
        self._point_extent = QtCore.QPointF(OPTIONS.point_extent, OPTIONS.point_extent)

    def paint(self, painter, *args):
        ''' Draw the current frame (or the subset of it that we have) '''
        for call in self._painter_function_calls:
            call(painter)

    def boundingRect(self):
        ''' Return the bounding rectangle around the contents we are drawing '''
        return self._current_view_rect

    def set_new_frame(self, frame_data):
        ''' Take data for a new frame '''
        self._frame_data = frame_data
        self._update_painter_calls()

    def append_to_existing_frame(self, frame_data):
        ''' Append the given data to an existing frame '''
        self._frame_data += ' ' + frame_data
        self._update_painter_calls()

    def _update_painter_calls(self):
        ''' Cache the painter function calls that we need to make to redraw the widget '''
        # Store the limits of everything we plot. This starts out as a null rectangle, which will also be invalid
        bounds = QtCore.QRectF()
        calls = []
        name_to_points_cache = {}

        for command, data in self._command_and_data_pairs():

            # Default to not creating a call -- it will be added to the list only if it is set to a non-None value
            call = None

            # Set the pen colour. At the moment expects float  RGB values between 0 and 1
            if command == 'colour':
                # TODO support other colour types
                rgbtmp = ([int(float(x)*255) for x in data]+[int(0),int(0),int(0)])[0:3]
                rgb = (x for x in rgbtmp)
                pen = pyqtgraph.mkPen(*rgb)
                call = lambda painter, pen=pen: painter.setPen(pen)

            # Draw a rectangle
            elif command == 'rect':
                rect = QtCore.QRectF(*(float(x) for x in data))
                bounds = bounds.united(rect)
                call = lambda painter, rect=rect: painter.drawRect(rect)

            # Draw an ellipse
            elif command == 'ellipse':
                rect = QtCore.QRectF(*(float(x) for x in data))
                bounds = bounds.united(rect)
                call = lambda painter, rect=rect: painter.drawEllipse(rect)

            # Draw a circle defined by centre, and radius
            elif command == 'circle':
                x, y = float(data[0]), float(data[1])
                centre = QtCore.QPointF(x, y)
                radius = float(data[2])
                bound_rect = QtCore.QRectF(x - radius, y - radius, 2 * radius, 2 * radius)
                bounds = bounds.united(bound_rect)
                call = lambda painter, centre=centre, radius=radius: painter.drawEllipse(centre, radius, radius)

            # Draw a point
            elif command == 'point':
                point = QtCore.QPointF(*(float(x) for x in data))
                bounds = self._unite_rectangle_with_point(bounds, point)
                call = lambda painter, point=point: painter.drawPoint(point)

            # Draw a multi-segment line
            elif command == 'line':
                points = [QtCore.QPointF(float(x), float(y)) for x, y in pairs(data, distinct=True)]
                for point in points:
                    bounds = self._unite_rectangle_with_point(bounds, point)
                call = lambda painter, points=points: painter.drawPolyline(*points)

            # Draw a multi-segment line, closed back to the start
            elif command == 'lineclosed':
                points = [QtCore.QPointF(float(x), float(y)) for x, y in pairs(data, distinct=True)]
                for point in points:
                    bounds = self._unite_rectangle_with_point(bounds, point)
                call = lambda painter, points=points: painter.drawPolygon(*points)

            # Pen creation and moving commands
            elif command == 'pen':
                name = data.pop(0)
                points = [QtCore.QPointF(float(x), float(y)) for x, y in pairs(data, distinct=True)]
                if name not in name_to_points_cache:
                    name_to_points_cache[name] = []
                name_to_points_cache[name].extend(points)

            elif command == 'break':
                name = data.pop(0)
                # Move the line cache to a unique name
                unique_name = None
                while unique_name is None:
                    candidate_name = str(random.randint(0, 10000000))
                    if not candidate_name in name_to_points_cache:
                        unique_name = candidate_name
                name_to_points_cache[unique_name] = name_to_points_cache[name]
                del name_to_points_cache[name]

            if call is not None:
                calls.append(call)

        # Create calls for any pen objects
        for points in name_to_points_cache.values():
            for point in points:
                bounds = self._unite_rectangle_with_point(bounds, point)
            call = lambda painter, points=points: painter.drawPolyline(*points)
            calls.append(call)


        # Store the calls
        self._painter_function_calls = calls

        # The current viewing rectangle will only ever be expanded. It starts out as None, at which point we just
        # set it to what we've been given
        old_view_rect = self._current_view_rect
        self._current_view_rect = self._current_view_rect.united(bounds)
        if old_view_rect != self._current_view_rect:
            self._controller.win.setRange(self._current_view_rect, padding=0)

        # sc_print(self._current_view_rect)

    def _unite_rectangle_with_point(self, rect, point):
        ''' Given a Qt rectangle, return the expanded rectangle that contains this point. If the rectangle already
            contains the point return the same object.
        '''
        point_extent_rect = QtCore.QRectF(point - self._point_extent, point + self._point_extent)
        return rect.united(point_extent_rect)

    def _command_and_data_pairs(self):
        ''' Split the current frame data into pairs and yield in the form of (command, data). For example:

            circle[0 0 1]   --> ('circle', ['0', '0', '1'])
            reset_pen[]     --> ('reset_pen', [])

            We don't support commands without arguments, e.g. "reset_pen", since this creates ambiguity when we have
            a partial frame -- we could return ('circle', None), and we don't want the caller to have to deal with this
            case for every command.
        '''
        # Split at spaces (outside of brackets) or at brackets themselves
        # TODO removing newlines completely may not be desired, we could perhaps do better
        frame_data = self._frame_data.replace('\n', ' ')
        tokens = [token for token in re.split("( |\[.*?\])", frame_data) if token.strip()]

        command = None
        data = None
        for token in tokens:
            # If command would be an end of frame, we should definitely stop. If data would be an end of frame
            # we ignore the command, since we expect every command to have some data associated with it
            if token == TOKEN_END_OF_FRAME:
                break

            if command is None:
                # We need a new command
                command = token
                continue
            elif data is None:
                token = token.lstrip('[').rstrip(']')
                data = [piece for piece in re.split("( |\\\".*?\\\"|'.*?')", token) if piece.strip()]

            if command is not None and data is not None:
                yield command, data
                command = data = None



class StreamCanvasGUI:
    ''' The GUI used by stream canvas - holds the Qt application and window, and performs periodic updates. '''

    def __init__(self):
        self._last_response = RESPONSE_NO_NEXT_FRAME        # Initialise thus so we request a full frame next
        self._create_window()
        self._populate_gui()
        self._start_updates()

    def _create_window(self):
        self.app = QtGui.QApplication([])
        self.win = StreamCanvasWindow(self)
        self.win.setWindowTitle(OPTIONS.window_title)
        self.win.resize(OPTIONS.window_width, OPTIONS.window_height)
        self.win.show()
        # This is needed to bring the window to the foreground
        self.win.raise_()

    def _populate_gui(self):
        ''' Create plots and other things in the GUI '''
        self.view_box = pyqtgraph.ViewBox()
        self.win.setCentralItem(self.view_box)
        # TODO Since the graphics object does code parsing it needs to interact with the view window. Seems ugly
        self.stream_graphics_object = StreamGraphicsObject(self)
        self.view_box.addItem(self.stream_graphics_object)
        self.grid_item = pyqtgraph.GridItem()
        self.view_box.addItem(self.grid_item)

    def _start_updates(self):
        ''' Start the timer-based updating of view contents'''
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(OPTIONS.window_update_time_ms)

    def update(self):
        ''' Create new frames '''
        mode = OPTIONS.mode

        # If we're in inspect modes, we shouldn't advance to the next frame in an update
        if (mode in (DisplayMode.inspect_nodrop, DisplayMode.inspect_drop)
                and self._last_response in (RESPONSE_COMPLETE_FRAME, RESPONSE_END_PARTIAL_FRAME)):
            return

        self._request_frame_data()

    def request_frame_advance(self):
        ''' If we are currently in possession of a complete frame, request a new one. Return True if we did get a new
            frame, False otherwise
        '''
        # We haven't got a complete frame yet, try again later
        if self._last_response not in (RESPONSE_COMPLETE_FRAME, RESPONSE_END_PARTIAL_FRAME):
            return False

        self._request_frame_data()

        # Return True to indicate that we advanced the frame
        return True

    def _request_frame_data(self):
        ''' Perform the request to the gobbler, and apply the updates to the canvas '''
        # We request a complete frame if we have already received a complete frame, otherwise we try to finish
        # the frame that we started
        if self._last_response in (RESPONSE_COMPLETE_FRAME, RESPONSE_END_PARTIAL_FRAME, RESPONSE_NO_NEXT_FRAME):
            signal = SIGNAL_NEXT_FRAME
        else:
            signal = SIGNAL_MORE_OF_SAME_FRAME

        response, data = self._read_response_and_data(signal)

        # Either start a fresh frame, or append to existing data as appropriate
        if response in (RESPONSE_COMPLETE_FRAME, RESPONSE_BEGIN_PARTIAL_FRAME):
            self.stream_graphics_object.set_new_frame(data)
        elif response in (RESPONSE_CONTINUE_PARTIAL_FRAME, RESPONSE_END_PARTIAL_FRAME):
            self.stream_graphics_object.append_to_existing_frame(data)
        # Do nothing in the case that there wasn't any more data to give us

        # We save the last response so we know what to request next time
        self._last_response = response

        # Make sure we can see the updates!
        self.view_box.update()

    def _read_response_and_data(self, signal):
        ''' Send signal to the parent process, and return the response code and data that we receive back '''
        # Indicate that we want the next frame
        try:
            response, data = read_response_and_data(signal)
        except BrokenPipeError:
            # If the gobbler has broken, shut down
            self.app.quit()
            return None, None
        return response, data

    def run(self):
        ''' Start the application '''
        self.app.exec_()

