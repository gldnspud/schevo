"""Functions to help with inspecting internal Schevo data structures.

For copyright, license, and warranty, see bottom of file.
"""

from schevo.label import label


def print_entity_information(db, entity):
    if db.format != 2:
        raise RuntimeError('Unsupported DB format')
    print '=' * 70
    print 'Entity information for %r' % entity
    print 'Label: %r' % label(entity)
    extent = entity.sys.extent
    print 'Extent: %r (id %r)' % (
        extent.name,
        db._extent_name_id[extent.name],
        )
    print 'Fields:'
    extent_map = db._extent_map(extent.name)
    field_id_name = extent_map['field_id_name']
    entity_map = db._entity_map(extent.name, entity.sys.oid)
    for field_id, stored_value in sorted(entity_map['fields'].iteritems()):
        print '    %r (name %r): %r' % (
            field_id,
            field_id_name[field_id],
            stored_value,
            )
    print 'Related Entities:'
    related_entities = sorted(entity_map['related_entities'].iteritems())
    for field_id, related_entity_set in related_entities:
        print '    %r (name %r): %r' % (
            field_id,
            field_id_name[field_id],
            related_entity_set,
            )
    print 'Link Count: %r' % entity_map['link_count']
    print 'Links:'
    links = sorted(entity_map['links'].iteritems())
    for (ref_extent_id, ref_field_id), links_tree in links:
        ref_extent_name = db._extent_id_name.get(ref_extent_id, '<Not Found>')
        if ref_extent_id in db._extent_id_name:
            ref_extent_map = db._extent_map(ref_extent_name)
            ref_field_name = ref_extent_map['field_id_name'][ref_field_id]
        else:
            ref_field_name = '<Unknown>'
        oids = ' '.join(str(oid) for oid in sorted(links_tree))
        print '    From extent %r (name %r) field %r (name %r): %r' % (
            ref_extent_id,
            ref_extent_name,
            ref_field_id,
            ref_field_name,
            oids,
            )


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
