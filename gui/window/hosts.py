"""The host classes the mixins are type-checked against live in hosts.pyi.

They are for the type checker only (the mixins import them under
`if TYPE_CHECKING:`), so this module is empty at run time. It is here so that
the import resolves to a source file next to its stub.
"""
