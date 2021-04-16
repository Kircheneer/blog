#!/usr/bin/env python
# -*- coding: utf-8 -*- #

AUTHOR = "Leo Kirchner"
SITENAME = "Kirchnered Networking"
SITEURL = ""
PATH = "content"
STATIC_PATHS = ["images"]
TIMEZONE = "Europe/Berlin"
DEFAULT_LANG = "en"
FEED_ALL_ATOM = "feeds/all.atom.xml"
CATEGORY_FEED_ATOM = "feeds/{slug}.atom.xml"
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None
THEME = "Flex"
LINKS = ()
SOCIAL = (
    ("github", "https://github.com/Kircheneer"),
    ("rss", "/blog/feeds/all.atom.xml"),
)
DEFAULT_PAGINATION = 10
FAVICON = "/blog/images/favicon.ico"
SITELOGO = SITEURL + "/blog/images/profile.png"
MAIN_MENU = True
HOME_HIDE_TAGS = True
MENUITEMS = (
    ("Archives", "/blog/archives.html"),
    ("Categories", "/blog/categories.html"),
    ("Tags", "/blog/tags.html"),
)
BROWSER_COLOR = "#333"
RELATIVE_URLS = False
