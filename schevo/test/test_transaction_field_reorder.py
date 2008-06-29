"""Transaction field reordering tests.

For copyright, license, and warranty, see bottom of file.
"""

from schevo.test import CreatesSchema


class BaseTransactionFieldReorder(CreatesSchema):

    body = '''

    class Something(E.Entity):

        field1 = f.string()
        field2 = f.integer()

        class _Create(T.Create):

            field3 = f.bytes()
            field2 = f.integer()

        class _Update(T.Update):

            field3 = f.bytes(place_before='field2')


    class SomethingElse(E.Entity):

        field0 = f.string()
        field1 = f.string()
        field2 = f.string(place_before='field1')

        class _Create(T.Create):

            field3 = f.string(place_after='field0')
            field4 = f.string(place_after='field1')
    '''

    def test_reorder_by_reassignment(self):
        # The Create transaction for a Something entity first should
        # have ``field1``, since that is implied by
        # create/delete/update. Then, ``field3`` should be next,
        # because ``field2`` was recreated afterwards, thus overriding
        # the original position of ``field2``.
        tx = db.Something.t.create()
        assert list(tx.f) == ['field1', 'field3', 'field2']

    def test_reorder_by_odict_reorder_method(self):
        tx = db.Something.t.create()
        tx.sys.current_field_map.reorder(0, 'field3')
        tx.sys.current_field_map.reorder(1, 'field2')
        tx.sys.current_field_map.reorder(2, 'field1')
        assert list(tx.f) == ['field3', 'field2', 'field1']

    def test_reorder_entity_field_by_place_before_or_place_after(self):
        tx = db.SomethingElse.t.create()
        assert list(tx.f) == ['field0', 'field3', 'field2', 'field1', 'field4']
        tx.field0 = '000'
        tx.field1 = 'abc'
        tx.field2 = 'def'
        tx.field3 = '333'
        tx.field4 = 'zzz'
        something_else = db.execute(tx)
        assert list(something_else.f) == ['field0', 'field2', 'field1']

    def test_reorder_tx_field_by_place_before_argument(self):
        tx = db.Something.t.create(field1='a', field2=1, field3='abc')
        something = db.execute(tx)
        tx = something.t.update()
        assert list(tx.f) == ['field1', 'field3', 'field2']


class TestTransactionFieldReorder1(BaseTransactionFieldReorder):

    include = True

    format = 1


class TestTransactionFieldReorder2(BaseTransactionFieldReorder):

    include = True

    format = 2


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
