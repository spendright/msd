from logging import getLogger

from .db import select_url
from .norm import merge_dicts

URL_FIELDS = ['url', 'author_url']

IGNORE_FIELDS = {'last_scraped', 'url'}

log = getLogger(__name__)



def merge_with_url_data(ds):
    """Merge a list of dicts, folding in data based on URLs.

    (data will only be filled from URLs if it's not available
    in any of the original dicts)

    Can also be used on a single dict.
    """
    if isinstance(ds, dict):
        ds = [ds]
    else:
        ds = list(ds)
    url_rows = []

    # look for URLs in the rows we want to merge
    for d in ds:
        for url_field in URL_FIELDS:
            url = d.get(url_field)
            if url:
                url_row = select_url(url)
                if url_row:
                    url_rows.append(_strip_url_row(url_row))

    return merge_dicts(ds + url_rows)


def _strip_url_row(url_row):
    return dict((k, v) for k, v in url_row.iteritems()
                if k not in IGNORE_FIELDS)
