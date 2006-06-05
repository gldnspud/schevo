"""Entity class.

For copyright, license, and warranty, see bottom of file.
"""

import sys
from schevo.lib import optimize

from schevo import base
from schevo.constant import UNASSIGNED
from schevo.error import (
    EntityDoesNotExist, ExtentDoesNotExist, FieldDoesNotExist)
from schevo.fieldspec import field_spec_from_class
from schevo.fieldspec import FieldSpecMap
from schevo.label import (
    LabelMixin, label_from_name, plural_from_name, with_label)
import schevo.namespace
from schevo.namespace import NamespaceExtension
from schevo import query
from schevo import transaction
from schevo import view


# extentmethod provides support for decorating methods of entity
# classes as belonging to the extent, not the entity.
def extentmethod(fn):
    def outer_fn(cls, *args, **kw):
        return fn(cls._extent, *args, **kw)
    if hasattr(fn, '_label'):
        _plural = getattr(fn, '_plural', None)
        decorator = with_label(fn._label, _plural)
        outer_fn = decorator(outer_fn)
    outer_fn = classmethod(outer_fn)
    return outer_fn


class EntityMeta(type):
    """Convert field definitions to a field specification ordered
    dictionary."""

    def __new__(cls, class_name, bases, class_dict):
        # Only do something if creating an Entity subclass.
        if class_name == 'Entity':
            return type.__new__(cls, class_name, bases, class_dict)
        class_dict['__slots__'] = bases[0].__slots__
        return type.__new__(cls, class_name, bases, class_dict)

    def __init__(cls, class_name, bases, class_dict):
        # Only do something if creating an Entity subclass.
        type.__init__(cls, class_name, bases, class_dict)
        if class_name == 'Entity':
            return
        # If the class has an actual name, use that instead.
        if '_actual_name' in class_dict:
            class_name = cls._actual_name
            cls.__name__ = class_name
        # Create the field spec odict.
        spec = cls._field_spec = field_spec_from_class(cls, class_dict)
        q_spec = spec.copy()
        tx_spec = spec.copy()
        v_spec = spec.copy()
        # Keep track of fields that have fget methods.
        fget_fields = []
        for field_name, FieldClass in spec.iteritems():
            fget = FieldClass.fget
            if fget is not None:
                fget_fields.append(field_name)
                def get_field(self, fget=fget[0]):
                    return fget(self)
                # Transactions and the default query don't need
                # calculated fields.
                del q_spec[field_name]
                del tx_spec[field_name]
            else:
                def get_field(self, field_name=field_name,
                              FieldClass=FieldClass):
                    """Get the field value from the database or cache."""
                    db = self._db
                    cache = self._cache
                    extent_name = self._extent.name
                    oid = self._oid
                    if not db._extent_contains_oid(extent_name, oid):
                        raise schevo.error.EntityDoesNotExist
                    if field_name in cache:
                        value, rev = cache[field_name]
                    else:
                        value, rev = None, None
                    if (value is None or
                        rev != db._entity_rev(extent_name, oid)):
                        try:
                            value, rev = db._entity_field_rev(
                                extent_name, oid, field_name)
                        except KeyError:
                            value = UNASSIGNED
                        except schevo.error.EntityDoesNotExist:
                            raise
                        else:
                            field = FieldClass(None, None)
                            field._value = value
                            value = field.get()
                            cache[field_name] = (value, rev)
                    return value
            setattr(cls, field_name, property(fget=get_field))
        cls._fget_fields = tuple(fget_fields)
        #
        # Create standard transaction classes.  Transaction fields
        # included in a transaction class defined in the schema appear
        # below the fields that come from the entity field spec.
        #
        # Create
        if not hasattr(cls, '_Create'):
            class _Create(transaction.Create):
                pass
            _Create._field_spec = tx_spec.copy()
            cls._Create = _Create
        else:
            # Always create a transaction subclass, in case the entity class
            # inherits from something other than E.Entity
            class _Create(cls._Create):
                pass
            subclass_spec = cls._Create._field_spec
            _Create._field_spec = tx_spec.copy()
            _Create._field_spec.update(subclass_spec, reorder=True)
            if hasattr(_Create, '_init_class'):
                _Create._init_class()
            cls._Create = _Create
        cls._Create._fget_fields = cls._fget_fields
        # Delete
        if not hasattr(cls, '_Delete'):
            class _Delete(transaction.Delete):
                pass
            cls._Delete = _Delete
        else:
            # Always create a transaction subclass, in case the entity class
            # inherits from something other than E.Entity
            class _Delete(cls._Delete):
                pass
            subclass_spec = cls._Delete._field_spec
            _Delete._field_spec = tx_spec.copy()
            _Delete._field_spec.update(subclass_spec, reorder=True)
            if hasattr(_Delete, '_init_class'):
                _Delete._init_class()
            cls._Delete = _Delete
        cls._Delete._fget_fields = cls._fget_fields
        # Generic Update (for use by cascading delete)
        class _GenericUpdate(transaction.Update):
            pass
        cls._GenericUpdate = _GenericUpdate
        cls._GenericUpdate._fget_fields = cls._fget_fields
        # Update
        if not hasattr(cls, '_Update'):
            class _Update(transaction.Update):
                pass
            cls._Update = _Update
        else:
            # Always create a transaction subclass, in case the entity class
            # inherits from something other than E.Entity
            class _Update(cls._Update):
                pass
            subclass_spec = cls._Update._field_spec
            _Update._field_spec = tx_spec.copy()
            _Update._field_spec.update(subclass_spec, reorder=True)
            if hasattr(_Update, '_init_class'):
                _Update._init_class()
            cls._Update = _Update
        cls._Update._fget_fields = cls._fget_fields
        #
        # Create standard view classes.  View fields included in a
        # view class defined in the schema appear below the fields
        # that come from the entity field spec.
        #
        # Default
        if not hasattr(cls, '_DefaultView'):
            class _DefaultView(view.View):
                _label = u'View'
            _DefaultView._field_spec = v_spec.copy()
            cls._DefaultView = _DefaultView
        else:
            # Always create a view subclass, in case the entity class
            # inherits from something other than E.Entity
            class _DefaultView(cls._DefaultView):
                pass
            subclass_spec = cls._DefaultView._field_spec
            _DefaultView._field_spec = v_spec.copy()
            _DefaultView._field_spec.update(subclass_spec, reorder=True)
            if hasattr(_DefaultView, '_init_class'):
                _DefaultView._init_class()
            cls._DefaultView = _DefaultView
        cls._DefaultView._fget_fields = cls._fget_fields
        # Set the entity class and extent name on all of them.
        cls._Create._extent_name = class_name
        cls._DefaultView._extent_name = class_name
        cls._Delete._extent_name = class_name
        cls._GenericUpdate._extent_name = class_name
        cls._Update._extent_name = class_name
        cls._Create._EntityClass = cls
        cls._DefaultView._EntityClass = cls
        cls._Delete._EntityClass = cls
        cls._GenericUpdate._EntityClass = cls
        cls._Update._EntityClass = cls
        # Create the hide spec.
        cls._hidden_actions = set(cls._hidden_actions)
        cls._hidden_queries = set(cls._hidden_queries)
        cls._hidden_views = set(cls._hidden_views)
        # Create the key spec.
        key_set = set(cls._key_spec)
        for s in cls._key_spec_additions:
            # Get just the names from field definitions.
            names = tuple(getattr(field_def, 'name', field_def)
                          for field_def in s)
            key_set.add(names)
            # The first key becomes the default key.
            if cls._default_key is None:
                cls._default_key = names
        cls._key_spec = tuple(key_set)
        cls._key_spec_additions = ()
        # Create the index spec.
        index_set = set(cls._index_spec)
        for s in cls._index_spec_additions:
            # Get just the names from field definitions.
            names = tuple(getattr(field_def, 'name', field_def)
                          for field_def in s)
            index_set.add(names)
        cls._index_spec = tuple(index_set)
        cls._index_spec_additions = ()
        # Assign labels for the class/extent.
        if '_label' not in class_dict and not hasattr(cls, '_label'):
            cls._label = label_from_name(class_name)
        if '_plural' not in class_dict and not hasattr(cls, '_plural'):
            cls._plural = plural_from_name(class_name)
        # Assign labels for query, transaction, and view methods.
        for key in class_dict:
            if key[:2] in ('q_', 't_', 'v_'):
                m_name = key
                func = getattr(cls, m_name)
                # Drop the prefix.
                method_name = m_name[2:]
                # Assign a label if none exists.
                new_label = None
                if getattr(func, '_label', None) is None:
                    # Make a label after dropping prefix.
                    new_label = label_from_name(method_name)
                if func.im_self == cls:
                    # Classmethod.
                    if new_label is not None:
                        func.im_func._label = new_label
                else:
                    # Instancemethod.
                    if new_label is not None:
                        class_dict[m_name]._label = new_label
        # Remember queries for the EntityQueries namespace.
        q_names = []
        for attr in dir(cls):
            if attr.startswith('q_'):
                q_name = attr
                func = getattr(cls, q_name)
                if func.im_self is None:
                    q_names.append(q_name)
        cls._q_names = q_names
        # Remember transactions for the EntityTransactions namespace.
        t_names = []
        for attr in dir(cls):
            if attr.startswith('t_'):
                t_name = attr
                func = getattr(cls, t_name)
                if func.im_self is None:
                    t_names.append(t_name)
        cls._t_names = t_names
        # Remember views for the EntityViews namespace.
        v_names = []
        for attr in dir(cls):
            if attr.startswith('v_'):
                v_name = attr
                func = getattr(cls, v_name)
                if func.im_self is None:
                    v_names.append(v_name)
        cls._v_names = v_names
        # Remember x_methods for the EntityExtenders namespace.
        x_names = []
        for attr in dir(cls):
            if attr.startswith('x_'):
                x_name = attr
                func = getattr(cls, x_name)
                if func.im_self is None:
                    x_names.append(x_name)
        cls._x_names = x_names
        # Only if this global schema definition variable exists.
        if schevo.namespace.SCHEMADEF is not None:
            # Add this subclass to the entity classes namespace.
            schevo.namespace.SCHEMADEF.E._set(class_name, cls)
            # Keep track of relationship metadata.
            relationships = schevo.namespace.SCHEMADEF.relationships
            for field_name, FieldClass in cls._field_spec.iteritems():
                if (hasattr(FieldClass, 'allow') and
                    field_name not in cls._fget_fields):
                    for entity_name in FieldClass.allow:
                        spec = relationships.setdefault(entity_name, [])
                        spec.append((class_name, field_name))


class Entity(base.Entity, LabelMixin):

    __metaclass__ = EntityMeta

    __slots__ = LabelMixin.__slots__ + ['_oid', '_cache', 'sys',
                                        'f', 'q', 't', 'v', 'x']

    # The first _key() specification defined.
    _default_key = None

    # Field specification for this type of Entity.
    _field_spec = FieldSpecMap()

    # True if typically hidden from a top-level view of the database
    # in a UI.
    _hidden = False

    # Sets of hidden transaction, query, and view methods.
    #
    # XXX: _hidden_* defaults in schevo.schema.hide function are used
    # XXX: if _hide is called during Entity subclass creation.
    _hidden_actions = set(['create_if_necessary', 'create_or_update',
                           'generic_update'])
    _hidden_queries = set([])
    _hidden_views = set()

    # Index specifications for the related extent.
    _index_spec = ()
    _index_spec_additions = ()          # Used during subclassing.

    # Key specifications for the related extent.
    _key_spec = ()
    _key_spec_additions = ()            # Used during subclassing.

    # Relationships between this Entity type and other Entity types.
    _relationships = []

    # Initial entity instances to create in a new database.
    _initial = []

    # The priority in which these initial values should be created.  A
    # higher priority indicates earlier execution.
    _initial_priority = 0

    # Sample entity instances to optionally create in a new database.
    _sample = []

    # The database instance associated with this Entity type.
    _db = None

    # The extent associated with this Entity type.
    _extent = None

    # The actual class/extent name to use for this Entity type.
    _actual_name = None
    
    # Names of query, transaction, view, and extender methods
    # applicable to entity instances.
    _q_names = []
    _t_names = []
    _v_names = []
    _x_names = []

    def __init__(self, oid):
        self._oid = oid
        self._cache = {}  # Cache of field values.
        self.sys = EntitySys(self)
        self.f = EntityFields(self)
        self.q = EntityQueries(self)
        self.t = EntityTransactions(self)
        self.v = EntityViews(self)
        self.x = EntityExtenders(self)

    def __cmp__(self, other):
        if other.__class__ is self.__class__:
            return cmp(self._oid, other._oid)
        else:
            return cmp(hash(self), hash(other))

    def __eq__(self, other):
        try:
            return (self._extent is other._extent and self._oid == other._oid)
        except AttributeError:
            return False

    def __ne__(self, other):
        return not (self == other)

    def __getattr__(self, name):
        msg = 'Field %r does not exist on %r.' % (name, self._extent.name)
        raise AttributeError(msg)

    def __hash__(self):
        return hash((self._extent, self._oid))

    def __repr__(self):
        oid = self._oid
        extent = self._extent
        if oid not in extent:
            return '<%s entity oid:%i rev:DELETED>' % (extent.name, oid)
        else:
            rev = self.sys.rev
            return '<%s entity oid:%i rev:%i>' % (extent.name, oid, rev)

    def __str__(self):
        return str(unicode(self))

    def __unicode__(self):
        if 'name' in self._field_spec:
            return unicode(self.name)
        else:
            return repr(self)

    @extentmethod
    @with_label(u'Exact Matches')
    def q_exact(extent, **kw):
        """Return a simple parameterized query for finding instances
        using the extent's ``find`` method."""
        return query.Exact(extent, **kw)

    @extentmethod
    @with_label(u'By Example')
    def q_by_example(extent, **kw):
        """Return an extensible query for finding instances, built
        upon Match and Intersection queries."""
        q = query.ByExample(extent, **kw)
        return q

    @classmethod
    @with_label(u'Create')
    def t_create(cls, **kw):
        """Return a Create transaction."""
        tx = cls._Create(**kw)
        return tx

    @classmethod
    @with_label(u'Create If Necessary')
    def t_create_if_necessary(cls, **kw):
        """Return a Create transaction that creates if necessary."""
        tx = cls._Create(**kw)
        tx._style = transaction._Create_If_Necessary
        return tx

    @classmethod
    @with_label(u'Create Or Update')
    def t_create_or_update(cls, **kw):
        """Return a Create transaction that creates or updates."""
        tx = cls._Create(**kw)
        tx._style = transaction._Create_Or_Update
        return tx

    @with_label(u'Delete')
    def t_delete(self):
        """Return a Delete transaction."""
        tx = self._Delete(self)
        return tx

    @with_label(u'Generic Update')
    def t_generic_update(self, **kw):
        """Return a Generic Update transaction."""
        tx = self._GenericUpdate(self, **kw)
        return tx

    @with_label(u'Update')
    def t_update(self, **kw):
        """Return an Update transaction."""
        tx = self._Update(self, **kw)
        return tx

    @with_label(u'View')
    def v_default(self):
        """Return the Default view."""
        return self._DefaultView(self)


class EntityExtenders(NamespaceExtension):
    """A namespace of entity-level methods."""

    __slots__ = NamespaceExtension.__slots__

    def __init__(self, entity):
        NamespaceExtension.__init__(self)
        d = self._d
        for x_name in entity._x_names:
            func = getattr(entity, x_name)
            name = x_name[2:]
            d[name] = func


class EntityFields(object):

    def __init__(self, entity):
        d = self.__dict__
        d['_entity'] = entity

    def __getattr__(self, name):
        e = self._entity
        FieldClass = e._field_spec[name]
        field = FieldClass(e, name, getattr(e, name))
        return field

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __iter__(self):
        return iter(self._entity._field_spec)

    def __setattr__(self, name, value):
        raise AttributeError('EntityFields attributes are readonly.')


class EntityQueries(NamespaceExtension):
    """A namespace of entity-level queries."""

    __slots__ = NamespaceExtension.__slots__ + ['_e']

    def __init__(self, entity):
        NamespaceExtension.__init__(self)
        d = self._d
        self._e = entity
        for q_name in entity._q_names:
            func = getattr(entity, q_name)
            name = q_name[2:]
            d[name] = func

    def __iter__(self):
        return (k for k in self._d.iterkeys()
                if k not in self._e._hidden_queries)


class EntitySys(NamespaceExtension):

    __slots__ = NamespaceExtension.__slots__ + ['_entity']

    def __init__(self, entity):
        """Create a sys namespace for the `entity`."""
        NamespaceExtension.__init__(self)
        self._entity = entity

    def as_data(self):
        """Return tuple of entity values in a form suitable for
        initial or sample data in a schema."""
        def resolve(entity, fieldname):
            field = entity.f[fieldname]
            value = getattr(entity, fieldname)
            if isinstance(value, Entity):
                entity = value
                values = []
                for fieldname in entity.sys.extent.default_key:
                    value = resolve(entity, fieldname)
                    values.append(value)
                if len(field.allow) > 1:
                    values = (entity.sys.extent.name, tuple(values))
                return tuple(values)
            else:
                return value
        values = []
        e = self._entity
        for f_name in e.f:
            f = e.f[f_name]
            if f.readonly or f.hidden:
                pass
            else:
                value = resolve(e, f_name)
                values.append(value)
        return tuple(values)

    def count(self, other_extent_name=None, other_field_name=None):
        """Return count of all links, or specific links if
        `other_extent_name` and `other_field_name` are supplied."""
        e = self._entity
        return e._db._entity_links(e._extent.name, e._oid, other_extent_name,
                                   other_field_name, return_count=True)

    @property
    def db(self):
        """Return the database to which this entity belongs."""
        return self._entity._db

    @property
    def exists(self):
        """Return True if the entity exists; False if it was deleted."""
        entity = self._entity
        oid = entity._oid
        extent = entity._extent
        return oid in extent

    @property
    def extent(self):
        """Return the extent to which this entity belongs."""
        return self._entity._extent

    @property
    def extent_name(self):
        """Return the name of the extent to which this entity belongs."""
        return self._entity._extent.name

    def fields(self, include_expensive=True, include_hidden=False,
               include_readonly_fget=True):
        """Return fields for the entity.

        - `include_expensive`: Set to `True` to include fields with
          `expensive` attribute set to `True`.
          
        - `include_hidden`: Set to `True` to include fields with
          `hidden` attribute set to `True`.

        - `include_readonly_fget`: Set to `True` to include fields
          with `fget` attribute set to something other than `None`.
        """
        e = self._entity
        stored_values = e._db._entity_fields(e._extent.name, e._oid)
        entity_fields = e._field_spec.field_map(e, stored_values)
        # Remove fields that should not be included.
        to_remove = []
        for name, field in entity_fields.iteritems():
            if field.hidden and not include_hidden:
                to_remove.append(name)
            elif field.expensive and not include_expensive:
                to_remove.append(name)
            elif field.fget is not None and not include_readonly_fget:
                to_remove.append(name)
        for name in to_remove:
            del entity_fields[name]
        # Update fields that have fget callables.
        for field in entity_fields.itervalues():
            if field.fget is not None:
                value = field.fget[0](e)
            else:
                value = field._value
            field._value = field.convert(value)
        return entity_fields

    def links(self, other_extent_name=None, other_field_name=None):
        """Return dictionary of (extent_name, field_name): entity_list
        pairs, or list of linking entities if `other_extent_name` and
        `other_field_name` are supplied."""
        e = self._entity
        return e._db._entity_links(e._extent.name, e._oid,
                                   other_extent_name, other_field_name)

    def links_filter(self, other_extent_name, other_field_name):
        """Return a callable that returns the current list of linking
        entities whenever called."""
        db = self._entity._db
        try:
            extent = db.extent(other_extent_name)
        except KeyError:
            raise ExtentDoesNotExist('%r does not exist.' % other_extent_name)
        if other_field_name not in extent.field_spec:
            raise FieldDoesNotExist('%r does not exist in %r' % (
                other_field_name, other_extent_name))
        def _filter():
            return self.links(other_extent_name, other_field_name)
        return _filter

    @property
    def oid(self):
        """Return the OID of the entity."""
        return self._entity._oid

    @property
    def rev(self):
        """Return the revision number of the entity."""
        e = self._entity
        return e._db._entity_rev(e._extent.name, e._oid)


class EntityTransactions(NamespaceExtension):
    """A namespace of entity-level transactions."""

    __slots__ = NamespaceExtension.__slots__ + ['_e']

    def __init__(self, entity):
        NamespaceExtension.__init__(self)
        d = self._d
        self._e = entity
        for t_name in entity._t_names:
            func = getattr(entity, t_name)
            name = t_name[2:]
            d[name] = func

    def __iter__(self):
        return (k for k in self._d.iterkeys()
                if k not in self._e._hidden_actions)


class EntityViews(NamespaceExtension):
    """A namespace of entity-level views."""

    __slots__ = NamespaceExtension.__slots__ + ['_e']

    def __init__(self, entity):
        NamespaceExtension.__init__(self)
        d = self._d
        self._e = entity
        for v_name in entity._v_names:
            func = getattr(entity, v_name)
            name = v_name[2:]
            d[name] = func

    def __iter__(self):
        return (k for k in self._d.iterkeys()
                if k not in self._e._hidden_views)


class EntityRef(object):
    """Reference to an Entity via its extent name and OID."""

    def __init__(self, extent_name, oid):
        """Create an EntityRef instance.

        - `extent_name`: The name of the extent.
        - `oid`: The OID of the entity.
        """
        self.extent_name = extent_name
        self.oid = oid


optimize.bind_all(sys.modules[__name__])  # Last line of module.


# Copyright (C) 2001-2006 Orbtech, L.L.C. and contributors
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
