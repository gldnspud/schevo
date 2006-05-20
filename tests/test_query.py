"""Query unit tests.

For copyright, license, and warranty, see bottom of file.
"""

from schevo.constant import UNASSIGNED
from schevo import error
from schevo import field
from schevo.label import label
from schevo.test import CreatesSchema, raises


class TestQuery(CreatesSchema):

    # XXX: tests for schevo.query.Links

    body = '''

    class DeltaAlpha(E.Entity):
        """A plain extent that has a default query like any other."""

        string = f.string(required=False)
        integer = f.integer(required=False)
        float = f.float(required=False)
        entity = f.entity('DeltaAlpha', required=False)


    class DeltaBravo(E.Entity):
        """An extent that has its default query hidden."""

        string = f.string(required=False)

        _hide('q_by_example')


    class DeltaCharlie(E.Entity):
        """An extent that has a custom query."""

        hashed_value = f.hashedValue()

        @extentmethod
        def q_hashes(extent, **kw):
            return E.DeltaCharlie._Hashes(extent, **kw)

        class _Hashes(Q.Param):

            compare_with = f.string()

            def __call__(self):
                # If a positional argument is given to __init__, it is
                # stored in self._on; in this case it is the extent.
                extent = self._on
                compare_with = self.compare_with
                return schevo.query.results(
                    dc for dc in extent
                    if dc.f.hashed_value.compare(compare_with)
                    )
    '''

    def test_q_namespace(self):
        # All extents have some standard queries
        assert list(db.DeltaAlpha.q) == ['by_example', 'exact']
        # An extent may have hidden a query.
        assert list(db.DeltaBravo.q) == ['exact']
        # An extent may have specified additional queries.
        assert list(sorted(db.DeltaCharlie.q)) == [
            'by_example', 'exact', 'hashes']

    def test_q_labels(self):
        assert label(db.DeltaAlpha.q.by_example) == u'By Example'
        assert label(db.DeltaAlpha.q.exact) == u'Exact Matches'

    def test_by_example_query(self):
        qmethod = db.DeltaAlpha.q.by_example
        new_da = lambda **kw: db.execute(db.DeltaAlpha.t.create(**kw))
        # Create some entities to query for.
        da1 = new_da(string='foo')
        da2 = new_da(string='bar', integer=5)
        da3 = new_da(integer=12, float=2.34)
        da4 = new_da(float=3.45, entity=da1)
        da5 = new_da(integer=12, entity=da2)
        da6 = new_da(string='foo', entity=da1)
        # Query for string 'foo'.
        q = qmethod(string='foo')
        results = list(sorted(q()))
        assert len(results) == 2
        assert results[0] == da1
        assert results[1] == da6
        # Query for string 'bar'.
        q = qmethod(string='bar')
        results = list(sorted(q()))
        assert len(results) == 1
        assert results[0] == da2
        # Query for unassigned string.
        q = qmethod(string=UNASSIGNED)
        results = list(sorted(q()))
        assert len(results) == 3
        assert results[0] == da3
        assert results[1] == da4
        assert results[2] == da5
        # Query for integer 12.
        q = qmethod(integer=12)
        results = list(sorted(q()))
        assert len(results) == 2
        assert results[0] == da3
        assert results[1] == da5
        # Query for integer 12 and entity da2.
        q = qmethod(integer=12, entity=da2)
        results = list(sorted(q()))
        assert len(results) == 1
        assert results[0] == da5
        # Query for integer 12 and string 'foo'.
        q = qmethod(integer=12, string='foo')
        results = list(sorted(q()))
        assert len(results) == 0
    
    def test_exact_query(self):
        # This is based on test_by_example_query, but uses the find query
        # instead, which is more specific than the by_example query.
        qmethod = db.DeltaAlpha.q.exact
        new_da = lambda **kw: db.execute(db.DeltaAlpha.t.create(**kw))
        # Create some entities to query for.
        da1 = new_da(string='foo')
        da2 = new_da(string='bar', integer=5)
        da3 = new_da(integer=12, float=2.34)
        da4 = new_da(float=3.45, entity=da1)
        da5 = new_da(integer=12, entity=da2)
        da6 = new_da(string='foo', entity=da1)
        # Query for string 'foo'.
        q = qmethod()
        q.string = 'foo'
        results = list(sorted(q()))
        assert len(results) == 2
        assert results[0] == da1
        assert results[1] == da6
        # Query for string 'bar'.
        q = qmethod()
        q.string = 'bar'
        results = list(sorted(q()))
        assert len(results) == 1
        assert results[0] == da2
        # Query for unassigned string.
        q = qmethod()
        q.string = UNASSIGNED
        results = list(sorted(q()))
        assert len(results) == 3
        assert results[0] == da3
        assert results[1] == da4
        assert results[2] == da5
        # Query for integer 12.
        q = qmethod()
        q.integer = 12
        results = list(sorted(q()))
        assert len(results) == 2
        assert results[0] == da3
        assert results[1] == da5
        # Query for integer 12 and entity da2.
        q = qmethod()
        q.integer = 12
        q.entity = da2
        results = list(sorted(q()))
        assert len(results) == 1
        assert results[0] == da5
        # Query for integer 12 and string 'foo'.
        q = qmethod()
        q.integer = 12
        q.string = 'foo'
        results = list(sorted(q()))
        assert len(results) == 0

    def test_parameterized_query(self):
        hashes = db.DeltaCharlie.q.hashes
        new_dc = lambda **kw: db.execute(db.DeltaCharlie.t.create(**kw))
        # Create some entities to query for.
        dc1 = new_dc(hashed_value='foo')
        dc2 = new_dc(hashed_value='bar')
        dc3 = new_dc(hashed_value='foo')
        # Query for string 'foo'; assignment by attribute.
        q = hashes()
        q.compare_with = 'foo'
        results = list(sorted(q()))
        assert len(results) == 2
        assert results[0] == dc1
        assert results[1] == dc3
        # Query for string 'bar'; assignment using kwargs.
        q = hashes(compare_with='bar')
        results = list(sorted(q()))
        assert len(results) == 1
        assert results[0] == dc2
        # Query for string 'baz'; zero results.
        q = hashes(compare_with='baz')
        results = list(sorted(q()))
        assert len(results) == 0
        # Make sure fields are accessible.
        q = hashes()
        assert isinstance(q.f.compare_with, field.String)
        assert list(q.f) == ['compare_with']

    def test_remove_match_from_intersection(self):
        q = db.DeltaAlpha.q.by_example()
        assert q.match_names == ['string', 'integer', 'float', 'entity']
        assert len(q.queries) == 4
        q.remove_match('integer')
        assert q.match_names == ['string', 'float', 'entity']
        assert len(q.queries) == 3
        raises(error.FieldDoesNotExist, q.remove_match, 'integer')
        

# Copyright (C) 2001-2006 Orbtech, L.L.C.
#
# Schevo
# http://schevo.org/
#
# Orbtech
# 709 East Jackson Road
# Saint Louis, MO  63119-4241
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
