
metastring
----------

This module composes and parses strings to write and extract metadata, respectively. Generally, this is so metadata can be stored and extracted to/from file paths and file names. With well defined separation and equivalence characters, the file name/path can be a convienent way to store metadata. The advantage of storing metadata in the file name/path is that it makes organizing and finding data easier. The disadvantage is that file names/paths can get long and difficult to read for a human. For cases with a lot of metadata, `dmanage.metafile` should be used. In the end, a combination of both `metastring` and `metafile` can be useful.

