# Blog

Personal blog at https://blog.kirchne.red.

Built using [Pelican](https://github.com/getpelican/pelican/) and the [Flex](https://github.com/alexandrevicenzi/Flex) theme.

## Updating

```bash
$ cd site
$ pelican content -o output -s publishconf.py
$ ghp-import output && git push origin gh-pages
```
