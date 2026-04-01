"""Type definitions for configuration dictionaries."""

from typing import TypedDict


class EntityDict(TypedDict):
    """Type definition for entity configuration."""

    slug: str
    name: str


class StateDict(TypedDict):
    """Type definition for state configuration."""

    slug: str
    name: str


class TransitionDict(TypedDict):
    """Type definition for transition configuration."""

    from_state: str
    to_state: str


class OptionsDict(TypedDict, total=False):
    """Type definition for system options."""

    lock_entities: bool
    display_prefix: str


class ConfigDict(TypedDict):
    """Type definition for full system configuration."""

    db_path: str
    entities: list[EntityDict]
    states: list[StateDict]
    transitions: list[TransitionDict]
    options: OptionsDict


EntityList = list[EntityDict]
"""List of entity configurations."""

StateList = list[StateDict]
"""List of state configurations."""

TransitionList = list[TransitionDict]
"""List of transition configurations."""
