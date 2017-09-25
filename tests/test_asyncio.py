import asyncio
import sys
import time

from asyncio import coroutine


count = 0

def echo_input(loop):
    ''' Read characters from standard in until we have a complete word, i.e. received a recognised separator token
        after a string of characters. Print these separated strings.
    '''
    # FIXME for debugging
    global count

    # Get a single token
    separators = (' ', '\n', '\t')

    buf = ''
    while True:
        c = sys.stdin.read(1)
        if c == '':
            # We have reached the end of the file when we get the empty string

            # We have to remember to do something with whatever we have left in the buffer
            if len(buf) > 0:
                print('MOO({}): "{}"'.format(count, buf))
            loop.stop()
            return

        if c in separators:
            # We have a separator! Do something with the buffer content if it isn't empty, then reset
            if len(buf) > 0:
                print('.', end='')
                # print('MOO({}): "{}"'.format(count, buf))
                count += 1
                buf = ''
            return

        # Append the character to the buffer
        buf += c
        
@coroutine
def do_stuff():
    ''' Simple coroutine to do some things '''
    while True:
        yield from asyncio.sleep(0.01)
        # Hard work
        time.sleep(1)
        print('I did some work')
        # yield


def main():
    # The basic event loop
    loop = asyncio.get_event_loop()

    # Read tokens from stdin ... 
    loop.add_reader(sys.stdin, echo_input, loop)

    # ... while doing some other work at the same time
    loop.run_until_complete(do_stuff())

    # Start program execution -- will continue until the UI terminates us
    # loop.run_forever()

    # Tidy up once we've stopped
    loop.close()



if __name__ == '__main__':
    main()

