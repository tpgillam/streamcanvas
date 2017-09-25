''' Test a multiple process asycio formulation. The first process will gobble stdin, and the second will do some
    hard work (simulated with a sleep...) with a given piece of data, and when it's done it will request more.

    TODO : there is noise on exit when terminated with the keyboard (although not too much).
'''

import asyncio
import sys
import time

from argparse import ArgumentParser
from asyncio import coroutine


NEXT_FRAME_SIGNAL = 'x'


count = 0
CURRENT_FRAME = None


def read_frames(loop):
    ''' Read characters from standard in until we have a complete word, i.e. received a recognised separator token
        after a string of characters. Ensure we keep at least the latest of these tokens.
    '''
    # FIXME for debugging
    global count
    global CURRENT_FRAME

    # Get a single token
    separators = (' ', '\n', '\t')

    buf = ''
    # The infinite loop is manually broken when we've read a whole token.
    # TODO is there a way better than reading one character at a time?
    while True:
        c = sys.stdin.read(1)
        if c == '':
            # We have reached the end of the file when we get the empty string

            # We have to remember to do something with whatever we have left in the buffer
            if len(buf) > 0:
                # print('.', file=sys.stderr, end='')
                CURRENT_FRAME = '{} {}'.format(count, buf)
            loop.stop()
            return

        if c in separators:
            # We have a separator! Do something with the buffer content if it isn't empty, then reset
            if len(buf) > 0:
                # print('.', file=sys.stderr, end='')
                CURRENT_FRAME = '{} {}'.format(count, buf)
                count += 1
                buf = ''
            return

        # Append the character to the buffer
        buf += c

        
@coroutine
def frame_sender(loop, worker_process):
    ''' Listen to the output from worker stdout, and when we're told to advance to the next frame, deliver it on the
        worker's stdin
    '''
    while True:
        # Since we're here, we know that we can read from this file. This will yield bytes
        buf = yield from worker_process.stdout.read(1)
        # convert buf to a string
        buf = buf.decode('ascii')

        print('Decoding signal', file=sys.stderr)

        if buf == '':
            # We've quit the worker process, so we will terminate too
            loop.stop()
            return
        elif buf == NEXT_FRAME_SIGNAL:
            # Send the next frame! We use the drain coroutine to allow the event loop to actually perform this
            # operation as soon as convenient
            print('Writing new frame! : {}'.format(CURRENT_FRAME), file=sys.stderr)
            worker_process.stdin.write('{}\n'.format(CURRENT_FRAME).encode('ascii'))
            yield from worker_process.stdin.drain()
        else:
            raise ValueError('Unrecognised command: {}'.format(buf))
    
@coroutine
def create_and_run_worker(loop):
    ''' Create the worker subprocess, then send data to it as requested '''
    # Create the worker process
    # TODO in production code the '--worker' wants to be a constant of some sort
    command_and_args = [sys.executable] + sys.argv + ['--worker']
    worker_process_create = asyncio.create_subprocess_exec(*command_and_args, 
                                                           stdout=asyncio.subprocess.PIPE, 
                                                           stdin=asyncio.subprocess.PIPE)
    worker_process = yield from worker_process_create

    # Send data as requested
    try:
        yield from frame_sender(loop, worker_process)
    except KeyboardInterrupt:
        # We're quite happy to quit on keyboard interrupt
        worker_process.terminate()
        pass


def run_gobbler():
    ''' We are the process that gobbles standard input '''
    # The basic event loop
    loop = asyncio.get_event_loop()

    # Read tokens from stdin
    loop.add_reader(sys.stdin, read_frames, loop)

    # Create and run the worker
    try:
        loop.run_until_complete(create_and_run_worker(loop))
    except KeyboardInterrupt:
        # We're quite happy to quit on keyboard interrupt
        pass

    # Tidy up once we've stopped
    loop.close()


def run_worker():
    ''' We are the process that does hard work with a given token from standard input '''
    try:
        while True:
            # Indicate that we want the next frame
            sys.stdout.write(NEXT_FRAME_SIGNAL)
            sys.stdout.flush()

            # Receive the next frame - for convenience it is guaranteed to be newline delimited
            frame_command = sys.stdin.readline()

            # Do some hard work...
            time.sleep(1)

            # ... and show the results
            # This is ugly. The point is that we want to use stdout as a control channel.
            # TODO reverse the two?
            print('MOO: {}'.format(frame_command.strip()), file=sys.stderr)
    except KeyboardInterrupt:
        # We're quite happy to quit on keyboard interrupt
        pass



def main():
    parser = ArgumentParser()
    parser.add_argument('--worker', action='store_true', help='Reserved option to start the worker process. '
                                                              'Do not call manually')
    args = parser.parse_args()

    if args.worker:
        run_worker()
    else:
        run_gobbler()


if __name__ == '__main__':
    main()

