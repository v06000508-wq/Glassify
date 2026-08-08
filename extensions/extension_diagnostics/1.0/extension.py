"""Glassify extension loader diagnostics.

This extension intentionally makes no UI changes. It is used to verify that
Glassify can download, validate, load, unload, and update remote extensions.
"""

GLASSIFY_EXTENSION = {
    "id": "extension_diagnostics",
    "name": "Extension Diagnostics",
    "version": "1.0",
    "api": 1,
}


def on_load(api):
    api.log("Extension Diagnostics 1.0 loaded successfully")


def on_unload(api):
    api.log("Extension Diagnostics 1.0 unloaded")
