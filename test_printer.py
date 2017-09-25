#!/usr/bin/env python
import random
import sys
import time

i = 1
try:
    print('# Comment at start of stream')
    print('options window_width 600 window_height 500 window_title "Ellipse"')
    # print('options window_width 800')
    print('# Ignore me')
    print('endoptions')
    r, g, b = 100, 255, 150
    r, g, b = 0.1, 0.5, 0.7
    dr = 0
    dg = 0
    db = 0
    print('colour[{} {} {}]'.format(r, g, b))
    while True:
        print('ellipse[', end='')
        for _ in range(4):
            x = random.random() * 10
            print('{:.2f}'.format(x), end=' ')
            # print(x)
        print(']')

        print('point[', end='')
        for _ in range(2):
            x = random.random() * 10 - 10
            print('{:.2f}'.format(x), end=' ')
            # print(x)
        print(']')

        print('line[', end='')
        for _ in range(3):
            x = random.random() * 10 - 10
            y = random.random() * 10
            print('{:.2f} {:.2f}'.format(x, y), end=' ')
        print(']')

        print('lineclosed[', end='')
        for _ in range(3):
            x = random.random() * 10 - 10
            y = random.random() * 10 + 10
            print('{:.2f} {:.2f}'.format(x, y), end=' ')
        print(']')

        print('rect[', end='')
        for _ in range(2):
            x = random.random() * 5
            y = random.random() * 5 - 5
            print('{:.2f} {:.2f}'.format(x, y), end=' ')
            # print(x)
        print(']')

        if i % 5 == 0:
            print('approve')
            print('colour[{} {} {}]'.format(r, g, b))
            r += dr
            g += dg
            b += db
            if r > 255 or r < 0:
                dr = - dr
                r += 2 * dr
            if g > 255 or g < 0:
                dg = - dg
                g += 2 * dg
            if b > 255 or b < 0:
                db = - db
                b += 2 * db

        sys.stdout.flush()
        time.sleep(0.001)
        i += 1

        # print('# Garbage rhubarb rhubarb')
        # time.sleep(0.5)
        # sys.stdout.flush()
except Exception:
    print('Oh, an exception')
