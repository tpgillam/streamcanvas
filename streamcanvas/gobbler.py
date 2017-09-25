''' Asyncio-based gobbler of stdin, which will start a plotter and deliver frames to it as requested '''

import asyncio
import sys
import time

from asyncio import coroutine
from enum import Enum

from streamcanvas.communication import send_response_and_data
from streamcanvas.constants import *
from streamcanvas.options import OPTIONS
from streamcanvas.utils import sc_print


class OptionsStore:
    ''' Store the global options that should be passed along to the plotter '''

    def __init__(self):
        self._data = ''
        self._options_ready = False

    def add_arguments_to_data(self, args):
        ''' Add any pertinent settings from the arguments to the data '''
        for option_name, default_value in OPTIONS.items():
            new_value = getattr(args, option_name)
            # Include the value only if it differs from the default
            if new_value != default_value:

                # Note that if the value is a string, we include it in quotation marks
                if isinstance(new_value, str):
                    contains_single_quote = "'" in new_value
                    contains_double_quote = '"' in new_value
                    if contains_double_quote and contains_single_quote:
                        raise RuntimeError("Value can't contain both double and single quotes")
                    elif contains_single_quote:
                        new_value = '"{}"'.format(new_value)
                    else:
                        new_value = "'{}'".format(new_value)

                # If it's an enum value then we just use its name
                elif isinstance(new_value, Enum):
                    new_value = new_value.name


                self._data += ' {} {}'.format(option_name, new_value)

    def add_token(self, token):
        ''' Add a token from the input stream ready to be processed '''
        # If we have start or end tokens, don't add them to the stream, but do set whether the options are ready
        if token == TOKEN_END_OPTIONS:
            self._options_ready = True
            return
        elif token == TOKEN_START_OPTIONS:
            return
        self._data += ' ' + token

    def no_options_tokens_coming(self):
        ''' Tell the store not to expect any options tokens; we therefore say that we have absorbed everything
            required
        '''
        self._options_ready = True

    def get_response_and_data(self):
        ''' If ready, return the options as a string along with appropriate response, otherwise indicate that they
            are not ready by specifying RESPONSE_OPTIONS_NOT_READY
        '''
        if self._options_ready:
            return (RESPONSE_OPTIONS, self._data)
        return (RESPONSE_OPTIONS_NOT_READY, '')

_OPTIONS_STORE = OptionsStore()


class FrameStore:
    ''' A store for one or multiple frames, which can be specified.

        If store_all_frames is False, then we store two frames - one that is complete, and one that is being filled.
        Frames are stored as strings of tokens, separated by a space. store_all_frames can be changed at runtime, and
        will alter subsequent behaviour of end_frame().
    '''

    def __init__(self):
        # We start out by storing all frames, and will then be told later by the plotter whether we can start dropping
        self.store_all_frames = True
        self.complete_frames = []
        self.frame_in_progress = ''

        # Indicates that we have delivered part of a frame, but not all of it
        self._part_way_through_delivering_frame = False

        # Indicates that we are still receiving data for a partial frame. If this is True, we should obtain
        # more of a partial frame from frame_in_progress, else the remainder is saved to _remainder_of_partial_frame
        self._still_receiving_data_for_partial_frame = False

        # This will hold the remainder of a frame that is part way through being given
        self._remainder_of_partial_frame = ''

    def add_token(self, token):
        ''' Add a token to the current frame '''
        self.frame_in_progress += ' ' + token
        if token == TOKEN_END_OF_FRAME:
            self._end_frame()

    def _end_frame(self):
        ''' Indicate that any tokens arriving after this point belong to a new frame '''
        # If we're part-way through a partial frame, update things appropriately. We don't touch complete_frames
        # in this case.
        if self._still_receiving_data_for_partial_frame:
            self._remainder_of_partial_frame = self.frame_in_progress
            self.frame_in_progress = ''
            self._still_receiving_data_for_partial_frame = False
            return

        # Drop the old complete frames if necessary
        if not self.store_all_frames:
            del self.complete_frames[:]
        self.complete_frames.append(self.frame_in_progress)
        self.frame_in_progress = ''

    def get_response_and_data(self, signal):
        ''' Given the current state of the store, when more data is requested calculate what response we should give,
            and what data should be sent to the plotter
        '''
        if signal == SIGNAL_MORE_OF_SAME_FRAME:
            # Test for inconsistent state
            if not self._part_way_through_delivering_frame:
                raise RuntimeError("We are asked to deliver more of a frame, but we haven't given one!")

            if self._still_receiving_data_for_partial_frame:
                response = RESPONSE_CONTINUE_PARTIAL_FRAME
                data = self.frame_in_progress
                self.frame_in_progress = ''
            else:
                # This is the last segment of the frame, we are done delivering this frame
                response = RESPONSE_END_PARTIAL_FRAME
                data = self._remainder_of_partial_frame
                self._remainder_of_partial_frame = ''
                self._part_way_through_delivering_frame = False

        # In all other cases we want the next complete frame, or the *start* of the next complete frame if not yet fully
        # available.

        elif len(self.complete_frames) > 0:
            # If we have a complete frame, then send that, and remove from the pending list
            response = RESPONSE_COMPLETE_FRAME
            data = self.complete_frames[0]
            del self.complete_frames[0]
            # If we were part way through delivering a frame, that's no longer the case
            self._part_way_through_delivering_frame = False

        else:
            # ... but if we don't have a complete frame, then send what we currently have of the next frame.

            # TODO - there's an edge case here. We can return a new partial frame, then get asked for a *new* frame,
            # but in fact return a further part of the same partial frame
            data = self.frame_in_progress
            if len(data) == 0:
                response = RESPONSE_NO_NEXT_FRAME
            else:
                response = RESPONSE_BEGIN_PARTIAL_FRAME
                self.frame_in_progress = ''
                self._part_way_through_delivering_frame = True
                self._still_receiving_data_for_partial_frame = True
        return response, data

# Store a single global instance of the frame store
_FRAME_STORE = FrameStore()


class StoreSelector:
    ''' Send tokens either to the options store or the frame store, as appropriate '''

    def __init__(self):
        self._just_started = True
        self._in_options = False

    def add_token(self, token):
        ''' Add a token to the appropriate store '''
        # Don't do anything with empty tokens
        if len(token) == 0:
            return

        # If this is the first token we absorb, see if it is an instruction to start options. If it is then start
        # options, otherwise signal to the options store not to expect any
        if self._just_started:
            self._just_started = False
            if token == TOKEN_START_OPTIONS:
                self._in_options = True
            else:
                _OPTIONS_STORE.no_options_tokens_coming()

        if self._in_options:
            _OPTIONS_STORE.add_token(token)
            # If this is the last options token, come out of options mode
            if token == TOKEN_END_OPTIONS:
                self._in_options = False
        else:
            _FRAME_STORE.add_token(token)


_STORE_SELECTOR = StoreSelector()


# Constants that we cache for performance
# Separators of tokens
_SEPARATORS = (' ', '\n', '\t')

# We ignore everything that is within a comment.
_COMMENT_START = '#'
_COMMENT_END = '\n'

# When we're within a delimiter pair we keep absorbing the token
_OPENING_TO_CLOSING_DELIMITER = {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}
_CLOSING_DELIMITERS = set(_OPENING_TO_CLOSING_DELIMITER.values())
_STRING_DELIMITERS = ('"', "'")


def _closing_string(buf, delimiter_stack, character):
    ''' Return True iff we are in a string, and the character is about to close it '''
    if len(delimiter_stack) == 0:
        return False
    delimiter = delimiter_stack[-1]
    return delimiter in _STRING_DELIMITERS and (character == delimiter)


def _in_string(buf, delimiter_stack, character):
    ''' Return True iff we're currently in the middle of a string constant that we're not about to close with
        character. We make the assumption that you close the string with the same type of quote with which it was
        opened.
    '''
    if len(delimiter_stack) == 0:
        return False
    delimiter = delimiter_stack[-1]
    return delimiter in _STRING_DELIMITERS and not (character == delimiter)


def read_frames(loop):
    ''' Read characters from standard in until we have a complete word, i.e. received a recognised separator token
        after a string of characters. Ensure we keep at least the latest of these tokens.
    '''
    # For clarity, we keep state information about being in comments separate from the delimiter pair stack.
    in_comment = False

    # Whenever we see an opening delimiter, we pop it onto the stack.
    delimiter_stack = []

    buf = ''
    # The infinite loop is manually broken when we've read a whole token.
    while True:
        character = sys.stdin.read(1)

        # We have reached the end of the file when we get the empty string. We won't exit as we will still
        # keep the plotter alive once the input stream finishes. We wait to be killed.
        if character == '':
            # TODO, we could just add this to the separator list and handle it in the same way? See if we need
            # the knowledge that we're done anywhere else.
            _STORE_SELECTOR.add_token(buf)
            return

        # If we're in a comment, and we see the end-of-comment indicator, we're done. The next pass will start
        # on the new token.
        elif in_comment and character == _COMMENT_END:
            return

        # If we're in a comment and we see any other character, ignore it
        elif in_comment:
            continue

        # If we're within a string delimiter that we're not closing then we are happy to absorb any old rubbish
        elif _in_string(buf, delimiter_stack, character):
            pass

        # We're not in a comment, and we're not in a string. If we see the comment start indicator we start a comment.
        # Since each infinite loop is intended to capture one token we *must* ensure that we break upon finishing a
        # comment.
        elif character == _COMMENT_START:
            _STORE_SELECTOR.add_token(buf)
            in_comment = True
            continue

        # We have an opening separator! We push it onto the delimiter stack, but also let it be added to the buffer
        # Note that we need to ensure that we're not closing a string at this point. If closing a string we want
        # to fall through to the logic below
        elif character in _OPENING_TO_CLOSING_DELIMITER and not _closing_string(buf, delimiter_stack, character):
            delimiter_stack.append(character)

        # We have a closing separator!
        elif character in _CLOSING_DELIMITERS:
            if len(delimiter_stack) == 0 or _OPENING_TO_CLOSING_DELIMITER[delimiter_stack[-1]] != character:
                raise RuntimeError("Unmatched closing delimiter {} in '{}'".format(character, buf))
            # We know this is the correct delimiter, so pop it off the stack
            delimiter_stack.pop()

        # We have a separator, and we're not within a comment or delimiter! Flush the complete token and finish.
        elif character in _SEPARATORS and len(delimiter_stack) == 0:
            _STORE_SELECTOR.add_token(buf)
            return

        # Append the character to the buffer
        buf += character


@coroutine
def frame_sender(loop, plotter_process):
    ''' Listen to the output from plotter stdout, and when we're told to advance to the next frame, deliver it on the
        plotter's stdin
    '''
    while True:
        # Since we're here, we know that we can read from this file. This will yield bytes
        signal = yield from plotter_process.stdout.read(1)
        # convert buf to a string
        signal = signal.decode('ascii')

        # Send more data along with the appropriate response
        if signal == SIGNAL_NEXT_FRAME or signal == SIGNAL_MORE_OF_SAME_FRAME:
            response, data = _FRAME_STORE.get_response_and_data(signal)

        # Send the options to the process
        elif signal == SIGNAL_SEND_OPTIONS:
            response, data = _OPTIONS_STORE.get_response_and_data()

        # Are we switching dropping modes? Change the behaviour of the frame store appropriately
        elif signal == SIGNAL_ENTER_DROP_MODE:
            _FRAME_STORE.store_all_frames = False
            response, data = RESPONSE_ACKNOWLEDGE, ''

        elif signal == SIGNAL_ENTER_NODROP_MODE:
            _FRAME_STORE.store_all_frames = True
            response, data = RESPONSE_ACKNOWLEDGE, ''

        # We've quit the plotter process, so we will terminate too
        elif signal == '':
            return

        else:
            raise ValueError('Unrecognised signal: {}'.format(signal))

        # Send data back to the plotter as required. We send a response and a number of lines of data to expect
        send_response_and_data(plotter_process.stdin, response, data)

        # We use the drain coroutine to allow the event loop to actually perform this operation now
        yield from plotter_process.stdin.drain()


@coroutine
def create_and_run_plotter(loop):
    ''' Create the plotter subprocess, then send data to it as requested '''
    # Create the plotter process
    command_and_args = [sys.executable] + sys.argv + [PLOTTER_ARGUMENT]
    plotter_process_create = asyncio.create_subprocess_exec(*command_and_args,
                                                            stdout=asyncio.subprocess.PIPE,
                                                            stdin=asyncio.subprocess.PIPE)
    plotter_process = yield from plotter_process_create

    # Send data as requested
    yield from frame_sender(loop, plotter_process)

    # Once we've finished sending data, we can quit the plotter
    try:
        plotter_process.terminate()
    except (OSError, ProcessLookupError):
        # The plotter may have quit on its own accord, in which case don't try to quit it again
        pass


def gobbler_main(args):
    ''' Entry point for the gobbler '''
    # Add arguments to the options store
    _OPTIONS_STORE.add_arguments_to_data(args)

    # The basic event loop
    loop = asyncio.get_event_loop()

    # Read tokens from stdin
    loop.add_reader(sys.stdin, read_frames, loop)

    # Create and run the plotter
    try:
        loop.run_until_complete(create_and_run_plotter(loop))
    except KeyboardInterrupt:
        # We're quite happy to quit on keyboard interrupt
        pass

    # Tidy up once we've stopped
    loop.close()

