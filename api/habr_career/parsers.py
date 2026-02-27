"""
Module-level parser overrides for Habr Career.
"""

from ..core.parsers import ParserFactory
from ..core.parsers.html_parsers import HabrCareerHTMLParser


class HabrCareerModuleHTMLParser(HabrCareerHTMLParser):
    """
    Adapter for the generic parsing pipeline.

    The core worker calls `parse_item(...)`, while the base HTML parser
    in the shared layer focuses on `fetch_item(...)`. This override bridges
    both contracts for the Habr Career module.
    """

    def parse_item(self, item_id: str, url: str):
        normalized_item_id = str(item_id).strip() if item_id is not None else ""
        if not normalized_item_id and url:
            normalized_item_id = url.rstrip("/").split("/")[-1]

        if not normalized_item_id:
            raise ValueError("Empty item_id for Habr Career parse_item call")

        return self.fetch_item(normalized_item_id, {})


# Override shared parser mapping with module-specific adapter.
ParserFactory.register("habr_career", "html", HabrCareerModuleHTMLParser)
