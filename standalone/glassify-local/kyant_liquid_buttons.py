# Glassify local extension. The AndroidLiquidGlass rendering code is Apache-2.0.
# Core verifies the native payload before loading it.
GLASSIFY_EXTENSION = {
    "id": "kyant_liquid_buttons",
    "name": "Kyant Liquid Buttons",
    "description": "Liquid Glass и пружинная анимация кнопок exteraGram.",
    "version": "1.3",
    "api": 4,
    "min_glassify": "0.6.0-beta.7",
    "min_exteragram": "13.2.2"
}

_DEX_PATH = "https://raw.githubusercontent.com/v06000508-wq/Glassify/main/extensions/local.kyant_liquid_buttons/1.3/payload/module.b64"
_DEX_SHA256 = "ce44039147fcb3d69f6ec1e62849b38193ebcf4c789a9ba0bf8d850994502806"
_DEX_SIZE = 62512
_DEX_CLASS = "glassify.kyant.LiquidButtonsEntry"
_handle = None


def on_load(api):
    global _handle
    _handle = api.load_remote_dex([_DEX_PATH], _DEX_SHA256, _DEX_SIZE, _DEX_CLASS)
    api.activate_embedded_dex(_handle)


def on_unload(api):
    global _handle
    if _handle is not None:
        try:
            api.unload_embedded_dex(_handle)
        finally:
            _handle = None
