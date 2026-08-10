# Glassify Extensions

Remote extension catalog for Glassify 0.2.0+.

This repository stores optional Glassify extensions separately from the main exteraGram plugin. The extension system is disabled by default in Glassify 0.2.0. The catalog is refreshed only after the user explicitly enables extensions, and extension code is downloaded only after the user presses Install. Newly installed extensions remain disabled until the user enables them manually.

## Repository layout

```text
catalog.json
extensions/
  <extension_id>/
    <version>/
      extension.py
      preview.webp
```

## Version format

Glassify extensions use a two-part version format such as `1.0`, `1.1`, `2.0`.

## Extension contract

Each extension exports metadata and optional lifecycle callbacks. Extensions declare the Glassify API version they require. API 2 adds tracked UI helpers; API 3 adds declarative native settings and validated Blur3 material profiles without exposing the core object:

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

Glassify verifies each downloaded extension against the SHA-256 hash declared in `catalog.json`. Installed code is also tied to the declared Git blob. Optional previews are declared with `file` and `sha256`, verified before display, and cached locally.

## Available extensions

- `ios_header` 1.0 — compact iOS-style chat header with native Liquid Glass, centered title/subtitle handling, avatar-aware layout and full stock-state restoration when disabled. Requires Glassify 0.2.0+.
- `liquidglass_plus` 1.3 — five Blur3 surface materials (`Clear`, `Frosted`, `Crystal`, `Satin`, `Deep Glass`) with adjustable inner glow and depth. The top chat-header blur remains Frosted and is not changed by the selected surface type. Requires Glassify 0.2.0+.

## Security model

- The extension system is disabled by default in Glassify 0.2.0.
- No catalog network request is started before the user enables extensions.
- Extensions are never installed or enabled automatically.
- Every downloaded extension must match the SHA-256 declared in the catalog.
- Installed extension code is checked against its pinned Git blob before loading.
- Installed extensions can be disabled or removed independently of Glassify Core.
- CI validates catalog structure, extension syntax and local hashes before changes are merged.
