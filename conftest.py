import sys, os

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

# Remove any other workspace shadowing
for p in list(sys.path):
    if "antigravity\\BIONEMO" in p.replace("/", "\\"):
        try:
            sys.path.remove(p)
        except ValueError:
            pass

if ROOT_DIR in sys.path:
    try:
        sys.path.remove(ROOT_DIR)
    except ValueError:
        pass
sys.path.insert(0, ROOT_DIR)

# Purge any cached 'src' module to avoid cross-project shadowing
for mod in list(sys.modules.keys()):
    if mod == "src" or mod.startswith("src."):
        del sys.modules[mod]
