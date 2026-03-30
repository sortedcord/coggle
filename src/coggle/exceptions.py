class ParserValidationError(Exception):
    """ Base exception class for parser """
    pass

class MissingPrimaryPathsError(ParserValidationError):
    """ Raised when a unary or a binary operation has an empty primary path collection """
    pass

class MissingDestinationPathError(ParserValidationError):
    """ Raised when a binary operation does not have a secondary path """
    pass

class UnexpectedDestinationPathError(ParserValidationError):
    """ Raised when a unary operation like LIST accidentally captures a secondary path """
    pass
# custom exception class for filter errors.
class FilterValdationError(ParserValidationError):
    """ Raised when there is a validation error for one of the filters """
    pass

class NegativeValueError(FilterValdationError):
    """ Raised when one of the active filter values is negative """
    pass
class UnexpectedValueError(FilterValdationError):
    """ Raised when a filter value is greater than another filter value when it shouldn't be """
    pass
class EmptyValueError(FilterValdationError):
    """ Raised when a filter value is an empty string """
    pass
# custom exception class for resolver errors.
class ResolverError(Exception):
    """ Base exception class for resolver """
    pass
class PathNotFoundError(ResolverError):
    """ Raised when a path was not found in the filesystem but there are suggestions """
    pass
class UnresolvablePathError(ResolverError):
    """ Raised when a path was not found in the filesystem and there are NO suggestions """
    pass
class InvalidPathError(ResolverError):
    """ A catch all for path structures that are invalid """
    pass
