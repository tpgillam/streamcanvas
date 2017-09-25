#!/usr/bin/env python
''' The main entry point for streamcanvas -- either starts a gobbler or a plotter process '''

# Stop those horrible quit message boxes from OSX:
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

from argparse import ArgumentParser
from enum import Enum

from streamcanvas.constants import PLOTTER_ARGUMENT
from streamcanvas.gobbler import gobbler_main
from streamcanvas.options import OPTIONS
from streamcanvas.plotter import plotter_main
from streamcanvas.utils import sc_print


def add_options_arguments(parser):
    ''' Add arguments to the argument parser for the global options '''
    for option_name, default in OPTIONS.items():
        # Use a more standard hyphen rather than underscore
        argument_name = '--{}'.format(option_name.replace('_', '-'))
        type_ = OPTIONS.type(option_name)

        # If type is an enum, wrap it in something that knows how to convert a string to an enum
        if issubclass(type_, Enum):
            type_creator = lambda str_: type_[str_]
        else:
            type_creator = type_

        parser.add_argument(argument_name, default=default, type=type_creator, help=OPTIONS.help(option_name))
        # TODO for boolean options automatically convert to flags?


def main():
    parser = ArgumentParser()
    parser.add_argument(PLOTTER_ARGUMENT, action='store_true', help='Reserved option to start the plotter process. '
                                                                    'Do not call manually. By default we start the '
                                                                    'gobbler.')
    add_options_arguments(parser)
    args = parser.parse_args()

    if getattr(args, PLOTTER_ARGUMENT.lstrip('-')):
        # We don't pass arguments to the plotter; the gobbler gives what is necessary via a pipe
        plotter_main()
    else:
        gobbler_main(args)


if __name__ == '__main__':
    main()

