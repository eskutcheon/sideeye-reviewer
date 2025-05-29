
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Iterable, Dict, Tuple, Set, Optional
from collections import defaultdict



class DataSource(ABC):
    """ Abstract source of image identifiers & bytes (disk, database, zip, API, etc). """

    @abstractmethod
    def enumerate(self) -> Iterable[str]:
        """ Yield *identifiers* (not bytes) in deterministic order """

    @abstractmethod
    def load(self, item_id: str) -> bytes:
        """ Return raw bytes for the item.  Decoding is deferred to transforms """

    # legacy helper function kept for compatibility with existing code
    def get_image_paths(self, item_id: str) -> List[str]:
        """ Optional helper kept only for code that still wants absolute paths. """
        raise NotImplementedError


class FolderSource(DataSource):
    """ Concrete DataSource for a flat or nested folder on local disk """
    def __init__(self, root: str | Path, patterns: Tuple[str, ...] = ("*.png", "*.jpg", "*.jpeg")):
        self.root = Path(root)
        self.patterns = patterns
        self._cache: Dict[str, bytes] = {}

    def enumerate(self) -> Iterable[str]:
        """ Yield identifiers (relative paths) for all items matching the patterns in the root folder """
        for pattern in self.patterns:
            yield from sorted([str(p.relative_to(self.root)) for p in self.root.rglob(pattern)])

    def load(self, item_id: str) -> bytes:
        """ load raw bytes for a single item identifier from the folder after adding to self._cache if not already cached """
        if item_id not in self._cache:
            self._cache[item_id] = (self.root / item_id).read_bytes()
        return self._cache[item_id]

    # legacy helper function kept for compatibility with existing code
    def get_image_paths(self, item_id: str) -> List[str]:
        """ Return full disk path(s) for a single identifier (kept for downstream code that still builds its own `plt.imread`) """
        return [str(self.root / item_id)]



class MultiFolderSource(DataSource):
    """ Concrete DataSource for multiple folders, yielding IDs present in ALL root directories """
    def __init__(self, roots: List[str | Path], patterns: Tuple[str, ...] = ("*.png", "*.jpg", "*.jpeg")):
        self.roots = [Path(r) for r in roots]
        self.patterns = patterns
        self._cache: Dict[str, List[bytes]] = defaultdict(list)
        self._common_ids: List[str] = self._compute_common_ids()

    def _collect_names(self, root: Path) -> set[str]:
        """ collect all item names matching the patterns in a single root folder """
        names = set()
        for pat in self.patterns:
            names.update({str(p.relative_to(root)) for p in root.rglob(pat)})
        return names

    def _compute_common_ids(self) -> List[str]:
        common_ids: Optional[Set[str]] = None
        for root in self.roots:
            names = self._collect_names(root)
            # TODO: add a mechanism that will collect all names with common prefixes rather than exact matches
                # this includes within the same root folder
            common_ids = names if common_ids is None else common_ids.intersection(names)
            if not common_ids:
                break
        return sorted(common_ids or [])

    def enumerate(self) -> Iterable[str]:
        """ Yield identifiers (relative paths) for items present in ALL root folders """
        yield from self._common_ids

    def load(self, item_id: str) -> bytes:
        """ Load raw bytes for a single item identifier from the first root where it exists, caching it """
        if item_id not in self._cache:
            for root in self.roots:
                path = root / item_id
                if not path.exists():
                    #! FIXCHANGE: may not want to raise an error in the future - just debugging for now
                    raise FileNotFoundError(f"{item_id} missing in {root}")
                self._cache[item_id].append(path.read_bytes())
        return self._cache[item_id]

    # legacy helper function kept for compatibility with existing code
    def get_image_paths(self, item_id: str) -> List[str]:
        """ Return full disk path(s) for a single identifier across all roots """
        return [str(r / item_id) for r in self.roots if (r / item_id).exists()]



class RemoteSource(DataSource):
    """ Concrete DataSource for a remote API or database (not implemented here) """
    def __init__(self, api_url: str):
        self.api_url = api_url

    def enumerate(self) -> Iterable[str]:
        """ Should return identifiers from the remote API. Not implemented here. """
        raise NotImplementedError("RemoteSource.enumerate() not yet implemented.")

    def load(self, item_id: str) -> bytes:
        """ Should fetch raw bytes from the remote API. Not implemented here. """
        raise NotImplementedError("RemoteSource.load() not yet implemented.")



# TODO: add abstract DataSource wrapper classes that can
# 1. combine multiple sources (e.g., local + remote)
# 2. create a streaming source that yields items on demand, possibly from an alternative source (e.g., a live feed)