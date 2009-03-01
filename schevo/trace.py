"""Efficient tracing of internal Schevo events.

Usage for logging::

    from schevo.trace import log
    assert log(level, message)

The assert is necessary to completely remove calls to the tracer
in production code.

Programmatic usage for viewing messages as they occur::

    import schevo.trace
    schevo.trace.monitor_level = 0      # Turn off viewing.
    schevo.trace.monitor_level = 1      # Turn on level 1 messages only.
    schevo.trace.monitor_level = 2      # Turn on level 1 and level 2 messages.
    schevo.trace.monitor_level = 3      # Turn on all messages.

Usage examples for viewing messages as they occur when using the
`schevo` command line::

    $ schevo db create --app=myapp --trace=3 example.db
    $ schevo db evolve -T2 example.db latest

For copyright, license, and warranty, see bottom of file.
"""

import inspect
import sys

from schevo.lib.optimize import do_not_optimize


TRACE_TO = sys.stderr


## if __debug__:
##     print >>TRACE_TO, """\
## Schevo tracing is ON."""


# History of trace messages.  Set to None to prevent appending.
_history = [
    # (level, modulename, message),
    ]


# By default, don't copy anything to stderr.
monitor_level = 0
monitor_prefix = '#'


def history(max_level):
    """Return a generator for items from `_history` up to and including
    those at `max_level`."""
    assert isinstance(max_level, int)
    return ((level, where, messages)
            for level, where, messages in _history
            if level <= max_level)


def print_history(max_level):
    """Print a pretty version of the results of `history(max_level)`."""
    for level, where, messages in history(max_level):
        print >>TRACE_TO, monitor_prefix, where,
        if level > 1:
            print >>TRACE_TO, ('--' * (level - 1)),
        for m in messages:
            print >>TRACE_TO, m,
        print >>TRACE_TO


@do_not_optimize
def log(level, *messages):
    """Append `message` at `level` to `_history`, outputting to stderr
    if desired."""
    if not monitor_level:
        # Short-circuit for speed, if not monitoring.
        pass
    assert isinstance(level, int)
    frame = sys._getframe(1)
    finfo = inspect.getframeinfo(frame)
    filename = finfo[0]
    funcname = finfo[2]
    modulename = inspect.getmodulename(filename)
    where = '%s.%s:' % (modulename, funcname)
    if _history is not None:
        _history.append((level, where, messages))
    if level <= monitor_level:
        print >>TRACE_TO, monitor_prefix, where,
        if level > 1:
            print >>TRACE_TO, ('--' * (level - 1)),
        for m in messages:
            print >>TRACE_TO, m,
        print >>TRACE_TO
    return True


# Copyright (C) 2001-2009 ElevenCraft Inc.
#
# Schevo
# http://schevo.org/
#
# ElevenCraft Inc.
# Bellingham, WA
# http://11craft.com/
#
# This toolkit is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This toolkit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
