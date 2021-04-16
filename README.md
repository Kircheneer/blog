# Blog

Personal blog.

Publish using

```bash
$ cd site
$ pelican content -o output -s publishconf.py
$ ghp-import output && git push origin gh-pages
```

A post-commit hook is configured.