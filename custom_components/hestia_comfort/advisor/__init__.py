"""Hestia Comfort 3.0 advisor: one engine that compares simulated gestures (docs/CAHIER-MOTEUR.md).

Nothing here imports Home Assistant: the time is an input, and the same inputs always give the same decision, so that
any decision can be replayed on the bench.
"""

# The engine's own version, apart from the integration's (docs/dev/MOTEUR-VERSIONS.md): written in every snapshot, in the
# journal and in each night's report, so that advice before and after a change can be told apart and replayed.
# Major: a new generation of the engine, its twins relearned; minor: a gesture, a rule or a decision that changes;
# fix: a correction that changes no advice but the wrong one.
VERSION = "3.15.0"
# Shown as a beta in « À propos » until the 3.0 generation has been through its betas in real houses; the number itself
# (snapshots, journal) stays bare.
BETA = True
