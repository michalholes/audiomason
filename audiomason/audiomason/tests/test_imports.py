"""
tests.test_imports
-------------------
Ensures all Audiomason v2 scaffold modules import correctly and expose functions.
"""

import importlib
import pkgutil
import inspect
import audiomason

def discover_modules(package):
    """Recursively discover all modules in a package."""
    for _, name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        if not is_pkg:
            yield name

def test_all_modules_import():
    """Import all modules under `audiomason` and ensure no ImportErrors."""
    failed = []
    for module_name in discover_modules(audiomason):
        try:
            importlib.import_module(module_name)
        except Exception as e:
            failed.append((module_name, str(e)))
    assert not failed, f"Modules failed to import: {failed}"

def test_functions_are_callable():
    """Ensure all functions defined in modules are callable."""
    for module_name in discover_modules(audiomason):
        module = importlib.import_module(module_name)
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            assert callable(obj), f"{module_name}.{name} is not callable"
