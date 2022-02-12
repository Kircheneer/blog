#!/usr/bin/env python
# -*- coding: utf-8 -*- #

AUTHOR = "Leo Kirchner"
SITENAME = "Kirchnered Networking"
SITEURL = ""
SITETITLE = SITENAME
SITESUBTITLE = "Network Automation Engineer"
PATH = "content"
STATIC_PATHS = ["images", "extra/CNAME"]
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
    ("rss", "/feeds/all.atom.xml"),
)
DEFAULT_PAGINATION = 10
FAVICON = "/images/favicon.ico"
SITELOGO = SITEURL + "/images/profile.png"
MAIN_MENU = True
HOME_HIDE_TAGS = True
MENUITEMS = (
    ("Archives", "/archives.html"),
    ("Categories", "/categories.html"),
    ("Tags", "/tags.html"),
)
BROWSER_COLOR = "#333"
RELATIVE_URLS = False
EXTRA_PATH_METADATA = {
    "extra/CNAME": {"path": "CNAME"},
    ".nojekyll": {"path": ".nojekyll"},
}
GOOGLE_ANALYTICS = "UA-183762699-1"
COPYRIGHT_YEAR = 2022
