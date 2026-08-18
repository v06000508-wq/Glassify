GLASSIFY_EXTENSION = {
    "id": "ios_input",
    "name": "iOS Input",
    "version": "1.1",
    "api": 4,
}

_DEX_SHA256 = "4637973df7bd0b114ddc1d2dcc056554d58c2a9f3e9a00a4b6b50119928a9155"
_DEX_SIZE = 211492
_MAIN_CLASS_NAME = "com.swagaplugins.plugin.modulartweaks.module.ios_input_panel.ios_input_panel"
_DEX_CHUNKS = [
    "https://raw.githubusercontent.com/v06000508-wq/Glassify/main/extensions/ios_input/1.1/payload/all.b64",
]

_API = None
_DEX_HANDLE = None

_SETTINGS = [
    {
        "type": "choice",
        "key": "timer_ring",
        "text": "Полоска таймера",
        "icon": "msg_settings",
        "default": "on",
        "options": [
  {"value": "on", "text": "Включено"},
  {"value": "off", "text": "Выключено"},
        ],
    },
    {
        "type": "divider",
        "text": "Оригинальный DEX-модуль iOS Input с проверкой SHA-256 и оптимизированной загрузкой.",
    },
]


def _log(text):
    if _API is not None:
        _API.log("iOS Input: " + str(text))


def _timer_ring_get():
    if _API is None or _DEX_HANDLE is None:
        return True
    try:
        return bool(_API.call_embedded_dex(_DEX_HANDLE, "timerRingEnabled", []))
    except Exception:
        return True


def _timer_ring_set(enabled):
    if _API is None or _DEX_HANDLE is None:
        return
    _API.call_embedded_dex(_DEX_HANDLE, "setTimerRingEnabled", [bool(enabled)])


def _settings_changed(key, value):
    if key == "timer_ring":
        _timer_ring_set(str(value) != "off")


def on_load(api):
    global _API, _DEX_HANDLE
    _API = api
    _DEX_HANDLE = api.load_remote_dex(
        _DEX_CHUNKS,
        _DEX_SHA256,
        _DEX_SIZE,
        _MAIN_CLASS_NAME,
    )
    api.activate_embedded_dex(_DEX_HANDLE)
    _timer_ring_set(str(api.get_setting("timer_ring", "on")) != "off")
    api.register_settings(_SETTINGS, _settings_changed)
    _log("loaded; optimized single payload; timer ring=" + ("on" if _timer_ring_get() else "off"))


def on_unload(api):
    global _API, _DEX_HANDLE
    if _DEX_HANDLE is not None:
        try:
  api.unload_embedded_dex(_DEX_HANDLE)
        finally:
  _DEX_HANDLE = None
    _API = None
