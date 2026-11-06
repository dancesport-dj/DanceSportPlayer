"""Which folders of the library ⚡ Generate draws from.

No Qt. A folder is chosen for the titles directly in it, not for everything
below it: "the main folder, not vlt" and "only vlt/vlt" are both a plain pick,
where a recursive choice could not say the first. Folders are named relative
to the library root, with "/" and in lower case, "" being the root itself.
"""

from pathlib import Path


def _rel_folder(path, root) -> str | None:
    """The folder of `path` below `root` ("" for the root), or None when the
    file lies outside it."""
    parent = Path(str(path)).parent
    try:
        rel = parent.relative_to(Path(str(root)))
    except ValueError:
        # Windows paths compare by case: retry on the lower-cased form.
        try:
            rel = Path(str(parent).lower()).relative_to(Path(str(root).lower()))
        except ValueError:
            return None
    return rel.as_posix().lower().strip(".")


def library_folders(entries, root) -> list[tuple[str, int]]:
    """Every folder that holds titles of its own, with how many, in name order."""
    counts: dict[str, int] = {}
    for e in entries:
        rel = _rel_folder(e.path, root)
        if rel is not None:
            counts[rel] = counts.get(rel, 0) + 1
    return sorted(counts.items())


def entries_in_folders(entries, root, folders) -> list:
    """The entries lying directly in one of `folders` (names as `library_folders`
    gives them)."""
    wanted = {str(f).lower().strip("/\\") for f in folders}
    return [e for e in entries if _rel_folder(e.path, root) in wanted]
