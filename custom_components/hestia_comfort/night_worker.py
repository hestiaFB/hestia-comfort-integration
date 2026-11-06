"""One room's nightly learning in a process of its own (PLAN-OPTIMISATION.md, point 10).

Started by advisor_home.py as `python -I night_worker.py`: it reads the arguments of `advisor.nightly.learn_room`
pickled on its input and writes what it returns pickled on its output. It loads only the advisor, never Home Assistant,
and runs at a low priority: the minute or more of pure calculation no longer slows Home Assistant down (in one of its
threads, Python let it move only between two steps of the calculation).
"""
import os
from pathlib import Path
import pickle
import sys
import types


def main():
    # The advisor's own package path, without running the integration's __init__ (which imports Home Assistant): the
    # arguments were pickled under these names.
    here = Path(__file__).resolve().parent
    for name, path in (("custom_components", here.parent), ("custom_components.hestia_comfort", here)):
        if name not in sys.modules:
            module = types.ModuleType(name)
            module.__path__ = [str(path)]
            sys.modules[name] = module
    try:
        os.nice(10)
    except OSError:
        pass
    from custom_components.hestia_comfort.advisor.nightly import learn_room

    arguments = pickle.load(sys.stdin.buffer)
    result = learn_room(*arguments)
    sys.stdout.buffer.write(pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL))
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
