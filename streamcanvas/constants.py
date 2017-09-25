''' Constants needed for basic operation of gobbler and plotter '''


# The argument to streamcanvas with which we start the plotter
PLOTTER_ARGUMENT = '--plotter'


# Signals that the plotter can pass to the gobbler
SIGNAL_SEND_OPTIONS = 'a'                 # Give us the global options
SIGNAL_NEXT_FRAME = 'n'                   # Give us the next frame, complete or incomplete
SIGNAL_MORE_OF_SAME_FRAME = 'm'           # Give us more of the frame that you previously gave us
SIGNAL_ENTER_DROP_MODE = 'd'              # Allow yourself to drop frames
SIGNAL_ENTER_NODROP_MODE = 'e'            # You must keep all the frames!


# Response codes that the gobbler can pass to the signaller
RESPONSE_ACKNOWLEDGE = '-'                # I did the thing that you told me to do, don't expect any data
RESPONSE_OPTIONS = 'a'                    # You asked for options, here they are
RESPONSE_OPTIONS_NOT_READY = 'b'          # You asked for options, but you should try again in a bit
RESPONSE_COMPLETE_FRAME = 'f'
RESPONSE_NO_NEXT_FRAME = 'o'              # You asked for a new frame, but there is none
RESPONSE_BEGIN_PARTIAL_FRAME = 'p'
RESPONSE_CONTINUE_PARTIAL_FRAME = 'c'     # I am returning more of a partial frame, but still not done
RESPONSE_END_PARTIAL_FRAME = 'e'          # I am returning the remainder of a partial frame


# The special end-of-frame token
TOKEN_END_OF_FRAME = 'approve'
TOKEN_START_OPTIONS = 'options'
TOKEN_END_OPTIONS = 'endoptions'

