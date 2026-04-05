"""Type definitions for configuration dictionaries."""

from typing import TypedDict


TransitionDict = TypedDict(
    "TransitionDict",
    {"from": str, "to": str},
)
"""Type definition for transition configuration."""


class SchemaDict(TypedDict, total=False):
    """Type definition for schema data."""

    entities: list[str]
    states: list[str]
    priorities: list[str]
    transitions: list[TransitionDict]


class OptionsDict(TypedDict, total=False):
    """Type definition for system options."""

    lock_entities: bool
    display_prefix: str
    default_priority: str


class ConfigDict(TypedDict, total=False):
    """Type definition for full system configuration."""

    schema: SchemaDict
    options: OptionsDict
