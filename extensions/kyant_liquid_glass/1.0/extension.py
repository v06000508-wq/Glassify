GLASSIFY_EXTENSION = {
    "id": "kyant_liquid_glass",
    "name": "Kyant Liquid Glass",
    "version": "1.0",
    "api": 4,
}

_DEX_SHA256 = "40545eabd7d3681c2af7ccef5b03d65d28ea430c9f0f6f412d5e672fc591a1d0"
_DEX_SIZE = 34108
_DEX_PATH = (
    "https://raw.githubusercontent.com/v06000508-wq/Glassify/main/"
    "extensions/kyant_liquid_glass/1.0/payload/module.b64"
)
_handle = None


def on_load(api):
    global _handle
    _handle = api.load_remote_dex(
        [_DEX_PATH], _DEX_SHA256, _DEX_SIZE, "glassify.kyant.LiquidGlass"
    )
    api.activate_embedded_dex(_handle)


def on_unload(api):
    global _handle
    if _handle is not None:
        try:
            api.unload_embedded_dex(_handle)
        finally:
            _handle = None
