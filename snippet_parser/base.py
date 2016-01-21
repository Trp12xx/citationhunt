#!/usr/bin/env python

from __future__ import unicode_literals
import os
import sys

_upper_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
if _upper_dir not in sys.path:
    sys.path.append(_upper_dir)

import config

import mwparserfromhell

REF_MARKER = 'ec5b89dc49c433a9521a13928c032129'
CITATION_NEEDED_MARKER = '7b94863f3091b449e6ab04d44cb372a0'

def get_localized_snippet_parser():
    import snippet_parser # requires CH_LANG
    return snippet_parser

class SnippetParserBase(object):
    '''A base class for snippet parsers in various languages.'''

    def __init__(self):
        # Monkey-patch mwparserfromhell to use our own methods.
        monkey_patched_classes = {
            mwparserfromhell.nodes.Template: self.strip_template,
            mwparserfromhell.nodes.Tag: self.strip_tag,
            mwparserfromhell.nodes.Wikilink: self.strip_wikilink,
        }

        # Always strip headings entirely
        mwparserfromhell.nodes.Heading.__strip__ = \
        mwparserfromhell.nodes.Node.__strip__

        self._original_strip_methods = {}
        for klass, method in monkey_patched_classes.items():
            self._original_strip_methods[klass] = klass.__strip__
            def unbind(self, *args):
                return monkey_patched_classes[type(self)](self, *args)
            klass.__strip__ = unbind

    def delegate_strip(self, obj, normalize, collapse):
        strip = self._original_strip_methods[type(obj)]
        strip = strip.__get__(obj, type(obj)) # bind the method
        return strip(normalize, collapse)

    def handle_common_templates(self, template, normalize, collapse):
        '''Handle a few common, non-localized templates. You usually want
        to call this from strip_template. This will either return a string
        (the replacement for the template), or None if the template was not
        handled.
        '''

        if template.name == 'lang':
            return template.params[1].value.strip_code()
        return None

    def strip_template(self, template, normalize, collapse):
        '''Override to control how templates are stripped in the wikicode.

        The return value will be the template's replacement. The default
        implementation replaces the citation needed template with
        CITATION_NEEDED_MARKER, which you must take care to do when overriding.
        '''

        if self.is_citation_needed(template):
            return CITATION_NEEDED_MARKER
        return ''

    def strip_tag(self, tag, normalize, collapse):
        '''Override to control how tags are stripped in the wikicode.

        The return value will be the tag's replacement. The default
        implementation replaces <ref> tags with REF_MARKER, which you probably
        want to do when overriding, and delegates other tags to mwparserfromhell.
        '''

        if tag.tag == 'ref':
            return REF_MARKER
        return self.delegate_strip(tag, normalize, collapse)

    def strip_wikilink(self, wikilink, normalize, collapse):
        '''Override to control how wikilinks are stripped in the wikicode.

        The return value will be the link's replacement. The default value
        will strip the wikilink entirely if its title has a prefix-match in
        config.wikilink_prefix_blacklist; otherwise, it will delegate to
        mwparserfromhell.
        '''

        cfg = config.get_localized_config()
        for prefix in cfg.wikilink_prefix_blacklist:
            if wikilink.title.startswith(prefix):
                return ''
        return self.delegate_strip(wikilink, normalize, collapse)

    def is_citation_needed(self, template):
        '''Override to control which templates are considered Citation needed.

        The default implementation matches against
        config.citation_needed_templates.
        '''

        cfg = config.get_localized_config()
        return any(
            template.name.matches(tpl)
            for tpl in cfg.citation_needed_templates)
