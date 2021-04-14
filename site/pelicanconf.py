#!/usr/bin/env python
# -*- coding: utf-8 -*- #

AUTHOR = 'Leo Kirchner'
SITENAME = 'Kirchnered Networking'
SITEURL = ''

PATH = 'content'

TIMEZONE = 'Europe/Berlin'

DEFAULT_LANG = 'English'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = 'feeds/all.atom.xml'
CATEGORY_FEED_ATOM = 'feeds/{slug}.atom.xml'
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

THEME = "Flex"

# Blogroll
LINKS = (('Home', SITEURL),)

# Social widget
SOCIAL = (('Github', 'https://github.com/Kircheneer'),
          ('Another social link', '#'),)

DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True