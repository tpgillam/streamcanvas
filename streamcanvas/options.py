''' Contains the Options class '''

import shlex

from collections import OrderedDict
from enum import Enum

from streamcanvas.utils import pairs, sc_print


class _Option:
    ''' Represents a single option. The default value can be None, which necessitates the separate type argument;
        by default it is set to the same type as the argument
    '''

    def __init__(self, value, help_, type_=None):
        self.value = value
        self.help_ = help_
        if type_ is None:
            type_ = type(value)
        self.type_ = type_


class DisplayMode(Enum):
    ''' Represents the types of display mode '''

    live = 0              # Live updating
    inspect_drop = 1      # Pause after each incoming frame, in the background drop all frames
    inspect_nodrop = 2    # Pause after each incoming frame, never miss a frame


class _Options:
    ''' Configurable options for the stream canvas. These are things that can be set by command line arguments or via an
        options block at the start of the command stream.

        Iterating over options yields the names of all options.
    '''

    def __init__(self):
        self._options = OrderedDict([
                ('window_title', _Option('StreamCanvas', 'Title of the display window')),
                ('window_width', _Option(400, 'Width of the display window')),
                ('window_height', _Option(400, 'Height of the display window')),
                ('window_update_time_ms', _Option(50, 'Plot refresh time (ms)')),
                ('mode', _Option(DisplayMode.live, 'Display mode: live, inspect_drop, inspect_nodrop')),
                ('verbose', _Option(False, 'Should we log in verbose mode?')),

                # Options controlling drawing
                ('point_extent', _Option(0.001, 'The "size" of a point when considering viewing range.')),
                ])

    def apply_data(self, data):
        ''' Apply the given data - a string - to the options herein and update values appropriately. If the same
            option appears multiple times, the last time of appearance will take precedence
        '''
        # This is a clever variant on the normal split that maintains quoted substrings
        for option_name, value_string in pairs(shlex.split(data), distinct=True):
            sc_print('Option: {}: {}'.format(option_name, value_string))
            self._apply_datum(option_name, value_string)

    def _apply_datum(self, option_name, value_string):
        ''' Apply the given option name and value to the options '''
        type_ = self._options[option_name].type_
        if issubclass(type_, Enum):
            # If the type is an enum, do a string lookup
            cast_value = type_[value_string]
        else:
            # Otherwise assume the constructor can handle it
            cast_value = type_(value_string)
        self._options[option_name].value = cast_value

    def __getattr__(self, option_name):
        return self._options[option_name].value

    def __setattr__(self, option_name, value):
        if option_name == '_options':
            # We want to be able to set this normally
            return super().__setattr__(option_name, value)
        self._options[option_name].value = value

    def __iter__(self):
        for option_name in self._options:
            yield option_name

    def items(self):
        ''' Generate option items '''
        for option_name in self:
            yield option_name, getattr(self, option_name)

    def help(self, option_name):
        ''' Return the help string for the given option name '''
        return self._options[option_name].help_

    def type(self, option_name):
        ''' Return the type of the given option '''
        return self._options[option_name].type_


# Just keep the one global instance
OPTIONS = _Options()

