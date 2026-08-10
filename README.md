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
      preview.webp
```

## Version format

Glassify extensions use a two-part version format such as `1.0`, `1.1`, `2.0`.

## Extension contract

Each extension exports metadata and optional lifecycle callbacks. Extensions
declare the Glassify API version they require; API 2 adds tracked UI helpers
for modular visual features without exposing the core object:

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
Optional store previews are declared as a `preview_v2` object with `file` and
`sha256` fields. Glassify 0.1.6+ downloads them only when the extension detail
page opens, verifies the hash, and keeps a local cache. Older cores safely ignore
the field.

## Available extensions

- `ios_header` 1.0 — moves the experimental centered iOS chat header out of
  Glassify Core. It owns its hooks and view snapshots, follows the core glass
  strength, and fully restores the stock header when disabled or unloaded.

## Security model

- The catalog may refresh automatically.
- Extensions are never installed automatically.
- Every downloaded extension must match the SHA-256 declared in the catalog.
- Installed extensions can be disabled or removed independently of Glassify Core.
