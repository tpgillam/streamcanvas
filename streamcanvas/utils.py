''' Useful utility functions '''

import sys

from itertools import tee

from streamcanvas.constants import PLOTTER_ARGUMENT


def pairs(iterable, skip=1, distinct=False):
    ''' Generate pairs of variables from a 1D iterator:

        s -> (s0,s[skip]), (s1,s[1+skip]), (s2, s[2+skip]), ...

        If distinct is True, then:

        s -> (s0,s[skip]), (s[skip+1],s[(skip + 1) + skip]), ...
    '''
    if not distinct:
        a, b = tee(iterable)
        for _ in range(skip):
            next(b, None)
        return zip(a, b)

    else:
        def _distinct_generator(iter_):
            # Ensure that we have an iterator object
            while True:
                iter_ = iter(iter_)
                item_0 = next(iter_)
                for _ in range(skip):
                    item_1 = next(iter_)
                yield item_0, item_1

        return _distinct_generator(iterable)


def sc_print(*args):
    ''' Stream canvas print -- logs to standard error, since stdout is taken! '''
    is_plotter = PLOTTER_ARGUMENT in sys.argv
    process_string = 'plotter' if is_plotter else 'gobbler'
    print('[{}]'.format(process_string), *args, file=sys.stderr)

