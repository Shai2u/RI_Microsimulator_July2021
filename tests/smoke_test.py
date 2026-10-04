"""Smoke test: exercises every dashboard callback path without a browser.

    python tests/smoke_test.py          # quick  (~1-2 min)
    python tests/smoke_test.py --full   # every year 1976-2080 (~5 min)

Exits non-zero if any callback raises.
"""
import itertools
import os
import resource
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

started = time.time()
import app as A  # noqa: E402

print(f'startup {time.time() - started:.1f}s')
# keep the test from overwriting the shared state of a running dashboard
A.STATE_DIR = Path(tempfile.mkdtemp())
A.DASH_STATE_FILE = A.STATE_DIR / 'dashboard.json'
A.MAP_STATE_FILE = A.STATE_DIR / 'map.json'

errors = []
cases = 0


def call(fn, *args):
    global cases
    cases += 1
    try:
        return getattr(fn, '__wrapped__', fn)(*args)
    except A.PreventUpdate:
        return 'prevented'
    except Exception as exc:  # noqa: BLE001 - report every failure
        errors.append((fn.__name__, args, f'{type(exc).__name__}: {exc}'))


def click(building):
    return None if building == 'None' else {'points': [{'customdata': [building, 'x']}]}


full = '--full' in sys.argv
years = range(A.YEAR_MIN, A.YEAR_MAX + 1) if full else [1976, 2000, 2045, 2080]

# every menu combination for one year
for building, res, ctx, tf in itertools.product(['None', 'Rivercross'], A.RESOLUTIONS, A.CONTEXTS, A.TIME_CATEGORIES):
    call(A.update_graph_ri, click(building), 2000, res, ctx, tf)
for cat, zoom, menu in itertools.product(A.MAP_CATEGORIES, sorted(A.ZOOM_TARGETS), A.MENU_3D):
    call(A.update_map2, 2000, cat, f'{zoom}: 2000', menu)

# every scope across the years
for year in years:
    for res, building in [('ri', 'None'), ('NotWire', 'None'), ('wire', 'None'), ('wireb', 'None'),
                          ('ind', 'Rivercross'), ('ind', 'Riverwalk Point')]:
        call(A.update_graph_ri, click(building), year, res, 'aib', 'leave')
    call(A.update_map2, year, 'aib', 'All of The Island: 0', 'No3D')

# hostile input must be neutralised, never raise
evil = '"]) or __import__("os").system("echo pwned") #'
call(A.update_graph_ri, {'points': [{'customdata': [evil]}]}, '2000 or 1', 'ind', '__class__', 'x')
call(A.update_graph_ri, 'junk', None, None, None, None)
call(A.update_map2, '1; drop', '__class__', evil, 'Yes3D')

# projection pages: render once, then skip while the state is unchanged
for fn in (A.updateProjDash, A.updateProj3D, A.updateOnly3D_1):
    first = call(fn, 1, None)
    if not isinstance(first, list) or call(fn, 2, first[-1]) != 'prevented':
        errors.append((fn.__name__, (), 'did not render once and then skip'))

peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1e6 if sys.platform == 'darwin' else 1e3)
print(f'{cases} cases, {len(errors)} errors, {time.time() - started:.0f}s, peak memory {peak_mb:.0f} MB')
for err in errors[:20]:
    print('ERROR', err)
sys.exit(1 if errors else 0)
