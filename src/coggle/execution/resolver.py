import os
import difflib
from dataclasses import dataclass
from pathlib import Path
from coggle.exceptions import PathNotFoundError, InvalidPathError, UnresolvablePathError, ResolverError

"""
This resolver should receive a ParsedResponse object and would "resolve" that to send it to the executor
"""
@dataclass
class ResolvedCommand:
    """
    What the executor would need:
    - adapter ("ls", "mv", "cp", "ffmpeg")
    - path
    - flags
    - filters
    ...
    """
    pass

# The exact structure for the schema is still unknown. I will thus try to pass a normal string and see what it resolves to here. 
test_strings = [
    "downloads",
    "/downloads",
    "~/Downloads/",
    "downloads/",
    "./downloads",
    "../downloads",
    ".../downloads",
    "../Downloads/"
]

HOME_DIRECTORY = Path.home()
CURRENT_WORKING_DIRECTORY = os.getcwd()
# print(HOME_DIRECTORY)
# results = []

"""
The flow for the testing shoud be:
1. Just path resolution - home (~), relative (/ or ./) or bare word?
2. Expansion of the resolved path -> ~ to $HOME/ relative and bare word via cwd then home.
3. Verify existence via os.path.exists() or isdir() AT THE END. If nothing gets resolved? Fail loudly. 
"""
def resolve_path(path: str):
    """ Resolves path for a given a path string """
    path = os.path.normpath(path)
    if path.startswith("~"):
        path = os.path.expanduser(path)
        return (os.path.normpath(path))
    else:
        if path.startswith("/"):
            path = path.replace("/", "") 
            return (os.path.join(HOME_DIRECTORY, path)) # leading / gets resolved to HOME/..
        else:
            return (os.path.normpath(os.path.join(CURRENT_WORKING_DIRECTORY, path)))

def check_resolved_path(resolved_path: str):
    """ Checks resolved paths for a path """
    if (os.path.isdir(resolved_path)):
        print("This path exists: ", resolved_path)
        return resolved_path
    else:
        base = (os.path.basename(resolved_path)).lower() # ex.: downloads
        # you go to the parent and then listdir for all directories for close matches

        try:
            directory_list: list[str] = os.listdir(os.path.dirname(resolved_path))
        except FileNotFoundError:
            raise InvalidPathError(f"It appears that {resolved_path} is not a valid path..")

        fuzzy_matches = difflib.get_close_matches(base, directory_list)
        print(f"Fuzzy matches: {fuzzy_matches} with resolved_path being {resolved_path}")
        if fuzzy_matches != []:
            matches = [os.path.join(os.path.dirname(resolved_path), match) for match in fuzzy_matches]
            for match in matches:
                raise PathNotFoundError(f"Did you mean: {match}?")
        else:
            raise UnresolvablePathError

def check_path(example_path: str):
    resolved = resolve_path(example_path)
    try:
        return check_resolved_path(resolved)
    except ResolverError as error:
        raise error
