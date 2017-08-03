"""Exceptions explicitly raised by this package.

Following best practice, all raised exceptions are derived from a single
package-specific base class so that 'all exceptions raised by nchelpers`
can be caught if desired.
"""

class CFException(Exception):
    pass


class CFAttributeError(CFException):
    pass


class CFValueError(CFException):
    pass
