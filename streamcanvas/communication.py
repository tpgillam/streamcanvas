''' Functions for performing communication between plotter and gobbler '''

import sys

from itertools import chain

from streamcanvas.constants import RESPONSE_ACKNOWLEDGE, SIGNAL_ENTER_DROP_MODE, SIGNAL_ENTER_NODROP_MODE
from streamcanvas.options import DisplayMode, OPTIONS


def send_response_and_data(stream, response, data):
    ''' Send the given signal and data, on the given stream which may contain multiple lines '''
    data_lines = data.split('\n')
    response_and_num_lines = '{} {}'.format(response, len(data_lines))

    for line_to_send in chain((response_and_num_lines,), data_lines):
        stream.write('{}\n'.format(line_to_send).encode('ascii'))


def read_response_and_data(signal):
    ''' Read and return a response and data from the gobbler after sending the given signal. Doesn't catch exceptions'''
    sys.stdout.write(signal)
    sys.stdout.flush()

    # We first get a response based on what data is available, and then some data
    response, num_lines = sys.stdin.readline().strip().split()
    data = ''
    for _ in range(int(num_lines)):
        data += sys.stdin.readline()
    data = data.strip()

    return response, data


def update_gobbler_dropping_mode():
    ''' Send a signal to the gobbler based on the current options '''
    if OPTIONS.mode in (DisplayMode.live, DisplayMode.inspect_drop):
        signal = SIGNAL_ENTER_DROP_MODE
    elif OPTIONS.mode == DisplayMode.inspect_nodrop:
        signal = SIGNAL_ENTER_NODROP_MODE
    else:
        raise RuntimeError("Unknown display mode: {}".format(OPTIONS.mode))

    response, _ = read_response_and_data(signal)
    if response != RESPONSE_ACKNOWLEDGE:
        raise RuntimeError("Expected acknowledge, got '{}'".format(response))
