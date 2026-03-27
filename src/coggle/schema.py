from dataclasses import dataclass
from intent_classifier import Intent
from exceptions import UnexpectedDestinationPathError, MissingPrimaryPathsError, MissingDestinationPathError, NegativeValueError, UnexpectedValueError, EmptyValueError

@dataclass
class FilenameFilter:
    """Filter for dealing with name values in user query"""
    starts_with: str | None = None
    ends_with: str | None = None
    contains: str | None = None

    def __post_init__(self):
        # Check for empty string values
        condition = (self.starts_with is not None and self.starts_with == '') or (self.ends_with is not None and self.ends_with == '') or ( self.contains is not None and self.contains =='')
        if condition:
            raise EmptyValueError

@dataclass
class TimeFilter:
    """Filter for time values in user query"""
    older_than_days: int | None = None
    newer_than_days: int | None = None
    
    def __post_init__(self):
        if self.older_than_days is not None:
            if not self.newer_than_days:
                self.newer_than_days = 0
        else:
            if self.newer_than_days:
                self.older_than_days = 0
            else:
                # Both are None and I shouldn't validate the response
                return
        _validate_values(self.older_than_days, self.newer_than_days)

@dataclass
class SizeFilter:
    """Filter for size values in user query"""
    # conversion to bytes but only if any one of these is not None in exec. script
    min_bytes: int | None = None
    max_bytes: int | None = None

    def __post_init__(self):
        if self.max_bytes is not None:
            if not self.min_bytes:
                self.min_bytes= 0
        else:
            if self.min_bytes:
                self.max_bytes= 0
            else:
                # Both are None and I shouldn't validate the response
                return
        _validate_values(self.min_bytes, self.max_bytes)

@dataclass
class Filter:
    extension: str | None = None      # ".pdf", ".jpg"
    filetype: str | None = None       # "images", "documents"  
    filename: FilenameFilter | None = None
    time: TimeFilter | None = None
    size: SizeFilter | None = None

@dataclass
class ParsedResponse:
    intent: Intent # Always present
    confirmation_required: bool = False # false by default
    primary_path: list[str] | None = None # main subject of operation; list because of multi-path operations like create, delete
    secondary_path: str | None = None # only used for binary operations (destination, new_name, target, etc.)
    filters: Filter | None = None

    def __post_init__(self):
        UNARY_OPERATIONS = [
            Intent.LIST,
            Intent.DELETE,
            Intent.CREATE,
            Intent.TRUNCATE,
        ]
        # just to be explicit, we also show binary operations
        # BINARY_OPERATIONS = [
        #     Intent.MOVE,
        #     Intent.COPY,
        #     Intent.RENAME,
        #     Intent.SYMLINK,
        #     Intent.HARDLINK
        # ]
        if self.intent in UNARY_OPERATIONS:
            validate_secondary_absence(self)
            # additionally with delete create truncate we also verify that primary exists; for list we will assert that through exec script.
            if self.intent != Intent.LIST:
                validate_primary_presence(self) 
        else:
            validate_primary_presence(self)
            validate_secondary_presence(self)

def validate_primary_presence(self):
    """ The primary path must be present for all unary operations except LIST and for all binary operations """
    if not self.primary_path: # checks for truthiness
        raise MissingPrimaryPathsError

def validate_secondary_presence(self):
    """ The secondary path must be present for binary operations """
    if not self.secondary_path:
        raise MissingDestinationPathError

def validate_secondary_absence(self):
    """ The secondary path must not be present for unary operations """
    if self.secondary_path:
        raise UnexpectedDestinationPathError

def _validate_values(bigger_value: int, smaller_value: int):
    if (bigger_value < 0) or (smaller_value < 0):
        raise NegativeValueError
    elif smaller_value > bigger_value:
        raise UnexpectedValueError
