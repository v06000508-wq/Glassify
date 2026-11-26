# Glassify local extension. The AndroidLiquidGlass rendering code is Apache-2.0.
# Core verifies the native payload before loading it.
GLASSIFY_EXTENSION = {
    "id": "kyant_liquid_buttons",
    "name": "Kyant Liquid Buttons",
    "description": "Liquid Glass для профиля, подарков, диалогов и кнопок с пружинной анимацией Telegram iOS.",
    "version": "1.0",
    "api": 4,
    "min_glassify": "0.6.0-beta.7",
    "min_exteragram": "13.2.2"
}

_DEX_PATH = "https://raw.githubusercontent.com/v06000508-wq/Glassify/main/extensions/local.kyant_liquid_buttons/1.0/payload/ios-panels.module.b64"
_DEX_SHA256 = "4dafbfef76a02c43323f1c5e18ffb55e090127cbed8f28e3d56b3d0e16a2dd4b"
_DEX_SIZE = 111900
_DEX_CLASS = "glassify.kyant.LiquidButtonsEntry"
_handle = None


def _sync_strength(api, strength):
    if _handle is not None:
        api.call_embedded_dex(_handle, "setStrength", [str(strength)])


def on_load(api):
    global _handle
    _handle = api.load_remote_dex([_DEX_PATH], _DEX_SHA256, _DEX_SIZE, _DEX_CLASS)
    _sync_strength(api, api.current_strength())
    api.activate_embedded_dex(_handle)
    api.register_strength_listener(lambda strength: _sync_strength(api, strength))


def on_unload(api):
    global _handle
    if _handle is not None:
        try:
            api.unload_embedded_dex(_handle)
        finally:
            _handle = None
