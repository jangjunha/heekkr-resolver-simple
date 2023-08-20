import re
import urllib.parse

from bs4 import Tag


def parse_url_base(root: Tag, base_url: str) -> str | None:
    if elem := root.select_one("a[href='#link']"):
        if m := URL_PATTERN.search(elem.attrs["onclick"]):
            parts = list(urllib.parse.urlparse(base_url))
            parts[4] = urllib.parse.urlencode(
                {
                    "recKey": m.group(1),
                    "bookKey": m.group(2),
                    "publishFormCode": m.group(3),
                }
            )
            return urllib.parse.urlunparse(parts)


URL_PATTERN = re.compile(
    r"fnSearchResultDetail\((\d+)\s*,\s*(\d+)\s*,\s*\'([\w\d]+)\'\)"
)
