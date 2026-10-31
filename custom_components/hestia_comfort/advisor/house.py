"""Layer 3: the house as declared, with ordinary values for whatever was not declared.

Every value that stands for a missing declaration is known as such (`declared`): the twin starts from it with a wider
uncertainty and learns the room's own.
"""
from dataclasses import dataclass, field

# Area (m²) and height (m) of an ordinary opening of each kind, when its size is not declared.
KINDS = {"window": (1.2, 1.2), "french": (1.8, 2.1), "skylight": (0.4, 0.5), "door": (1.8, 2.0)}
# The part of an opening that is glass: an entrance door lets in air when open, little sun when shut.
GLAZED = {"window": 1.0, "french": 1.0, "skylight": 1.0, "door": 0.2}
ORDINARY_VOLUME = 40.0
CEILING = 2.5


@dataclass(frozen=True)
class Opening:
    entity_id: str
    kind: str = "window"
    exposure: float | None = None   # bearing of the facade, degrees
    area: float | None = None       # m², declared
    height: float | None = None     # m, declared
    sheltered: bool = False

    @property
    def size(self) -> tuple[float, float]:
        """Area and height, declared or ordinary for its kind."""
        area, height = KINDS.get(self.kind, KINDS["window"])
        return (self.area or area, self.height or height)

    @property
    def glazing(self) -> float:
        return self.size[0] * GLAZED.get(self.kind, 1.0)


@dataclass(frozen=True)
class Room:
    id: str
    name: str
    volume: float | None = None         # m³, declared
    floor: int | None = None
    walls: str | None = None            # « heavy » (stone, concrete), « light » (plaster, wood), or not declared
    openings: tuple[Opening, ...] = ()
    heating_power: float | None = None  # W at full power, declared
    sleepers: int | None = None
    uses: frozenset[str] = field(default_factory=frozenset)

    @property
    def air(self) -> float:
        return self.volume or ORDINARY_VOLUME

    @property
    def surface(self) -> float:
        """Floor area (m²) from the volume and an ordinary ceiling height."""
        return self.air / CEILING

    @property
    def declared(self) -> set[str]:
        return {k for k in ("volume", "walls", "heating_power") if getattr(self, k) is not None}
