"""Backend management and selection.

For copyright, license, and warranty, see bottom of file.
"""

import sys
from schevo.lib import optimize

import pkg_resources


backends = dict(
    # backend-name = backend-class,
    (p.name, p.load())
    for p in pkg_resources.iter_entry_points('schevo.backend')
    )


def test_backends_dict():
    """Durus and schevo.store backends are always present after Schevo
    is installed."""
    assert 'durus' in backends
    assert 'schevo.store' in backends


optimize.bind_all(sys.modules[__name__])  # Last line of module.


# Copyright (C) 2001-2007 Orbtech, L.L.C.
#
# Schevo
# http://schevo.org/
#
# Orbtech
# Saint Louis, MO
# http://orbtech.com/
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