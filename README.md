# Glassify Extensions

Remote extension catalog for Glassify.

This repository stores optional Glassify extensions separately from the main exteraGram plugin. Glassify downloads only the catalog automatically. Extension code is downloaded only after the user explicitly installs an extension.

## Repository layout

```text
catalog.json
extensions/
  <extension_id>/
    <version>/
      extension.py
```

## Version format

Glassify extensions use a two-part version format such as `1.0`, `1.1`, `2.0`.

## Extension contract

Each extension exports metadata and optional lifecycle callbacks:

```python
GLASSIFY_EXTENSION = {
    "id": "example",
    "name": "Example",
    "version": "1.0",
    "api": 1,
}


def on_load(api):
    api.log("Example loaded")


def on_unload(api):
    api.log("Example unloaded")
```

Glassify verifies the SHA-256 hash from `catalog.json` before loading downloaded code.

## Security model

- The catalog may refresh automatically.
- Extensions are never installed automatically.
- Every downloaded extension must match the SHA-256 declared in the catalog.
- Installed extensions can be disabled or removed independently of Glassify Core.
