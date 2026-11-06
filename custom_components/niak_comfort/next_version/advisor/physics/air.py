"""The air: CO₂ breathed into the room, carried out by the outdoor air coming in.

    V · dC/dt = Q·(Ce − C) + 10⁶ · S

C in ppm, S the CO₂ the people breathe out (m³/h; about 0.018 for an adult at rest), Q the outdoor air coming in
(advisor/physics/vents.py). The CO₂ is the one measure that sees the air renewed: how fast it falls while a window is
open gives that window's real flow. Between two steps the equation is solved exactly (first order, linear).
"""
from dataclasses import dataclass
import math

STEP = 300.0
OUTDOOR = 420.0          # ppm
BREATH = 0.018           # m³/h of CO₂ breathed out by an adult at rest


@dataclass(frozen=True)
class AirParams:
    volume: float           # m³
    sources: float          # m³/h of CO₂, steady (people at home)
    rhythm_cos: float = 0.0
    rhythm_sin: float = 0.0


def breathed(p: AirParams, hour: float | None) -> float:
    if hour is None:
        return p.sources
    angle = 2 * math.pi * hour / 24
    return max(0.0, p.sources + p.rhythm_cos * math.cos(angle) + p.rhythm_sin * math.sin(angle))


@dataclass(frozen=True)
class ParticleParams:
    """Fine particles (PM2.5): brought by the outdoor air, made indoors (cooking, the stove), and settling on surfaces."""
    volume: float           # m³
    settling: float         # h⁻¹: what surfaces take out by themselves
    outdoor: float          # µg/m³, the outdoor level as the room sees it
    sources: float          # µg/h made indoors, steady
    rhythm_cos: float = 0.0
    rhythm_sin: float = 0.0


def particles_step(p: ParticleParams, level: float, flow: float, hour: float | None, dt: float = STEP,
                   purifier: float = 0.0) -> float:
    """The PM2.5 `dt` seconds later; `flow` in m³/h, `purifier` its clean air in m³/h while it runs."""
    angle = 2 * math.pi * (hour or 0.0) / 24
    made = max(0.0, p.sources + (p.rhythm_cos * math.cos(angle) + p.rhythm_sin * math.sin(angle) if hour is not None else 0.0))
    loss = (flow + purifier) / p.volume + p.settling
    settled = (flow / p.volume * p.outdoor + made / p.volume) / loss
    return settled + (level - settled) * math.exp(-loss * dt / 3600)


def air_step(p: AirParams, co2: float, flow: float, hour: float | None, dt: float = STEP, outdoor: float = OUTDOOR) -> float:
    """The CO₂ `dt` seconds later; `flow` in m³/h."""
    source = breathed(p, hour) * 1e6
    if flow <= 0:
        return co2 + source / p.volume * dt / 3600
    settled = outdoor + source / flow
    return settled + (co2 - settled) * math.exp(-flow / p.volume * dt / 3600)
