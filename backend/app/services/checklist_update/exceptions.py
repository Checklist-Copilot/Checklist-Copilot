class ChecklistOperationError(Exception):
    """Base class for checklist operation errors."""


class UnsupportedOperationError(ChecklistOperationError):
    pass


class UnsupportedComponentTypeError(ChecklistOperationError):
    pass


class ComponentNotFoundError(ChecklistOperationError):
    pass


class InvalidTargetContainerError(ChecklistOperationError):
    pass


class CannotDeleteRootError(ChecklistOperationError):
    pass


class InvalidComponentPayloadError(ChecklistOperationError):
    """Raised when a component payload (add) or patch (update) fails validation."""
    pass
