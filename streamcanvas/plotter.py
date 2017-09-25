''' A plotter that expects to interact with a gobbler via stdin & stdout '''

import sys
import time

from streamcanvas.communication import read_response_and_data, update_gobbler_dropping_mode
from streamcanvas.constants import RESPONSE_OPTIONS, RESPONSE_OPTIONS_NOT_READY, SIGNAL_SEND_OPTIONS
from streamcanvas.options import OPTIONS
from streamcanvas.plotter_qt2d import StreamCanvasGUI


def _update_options():
    ''' Update the options from the gobbler '''
    while True:
        response, data = read_response_and_data(SIGNAL_SEND_OPTIONS)
        if response == RESPONSE_OPTIONS:
            break
        elif response == RESPONSE_OPTIONS_NOT_READY:
            time.sleep(0.1)
        else:
            raise RuntimeError("Unknown response when wanting options: {}".format(response))

    # Apply options to the global configuration
    OPTIONS.apply_data(data)


def plotter_main():
    ''' Entry point for the plotter '''
    _update_options()

    # Tell the gobbler what sort of dropping mode to use, based on the options
    update_gobbler_dropping_mode()

    gui = StreamCanvasGUI()
    gui.run()

