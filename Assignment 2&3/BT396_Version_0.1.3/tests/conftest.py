# tests/conftest.py
import sys, pathlib
# add the project root (the folder that contains main.py and /framework) to sys.path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
