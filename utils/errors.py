"""Typed exceptions for Docksmith.

Define common error classes so modules can raise and catch specific errors
instead of using generic Exception or printing directly.
"""

class ParseError(Exception):
	"""Raised when Docksmithfile parsing fails (includes line info)."""
	pass

class ImageNotFound(Exception):
	"""Raised when a requested image manifest or file cannot be found."""
	pass

class ValidationError(Exception):
	"""Raised when a validation rule is violated (instruction or manifest)."""
	pass
