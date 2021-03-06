"""Schevo templates for Python Paste."""

# Copyright (c) 2001-2009 ElevenCraft Inc.
# See LICENSE for details.

import pkg_resources

from paste.script import templates


class SchevoTemplate(templates.Template):

    egg_plugins = ['Schevo']
    _template_dir = pkg_resources.resource_filename(
        pkg_resources.Requirement.parse('Schevo'),
        'schevo/templates/schevo')
    summary = 'Schevo application template.'
