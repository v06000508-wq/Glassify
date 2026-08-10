GLASSIFY_EXTENSION = {
    "id": "liquidglass_plus",
    "name": "LiquidGlass+",
    "version": "1.0",
    "api": 3,
}

_API = None

_DEFAULTS = {
    "surface": "frosted",
    "glow": "soft",
    "depth": "soft",
}

_SURFACES = {
    "clear": {
        "intensity_scale": 0.68,
        "thickness_scale": 0.72,
    },
    "frosted": {
        "intensity_scale": 0.96,
        "thickness_scale": 0.80,
    },
    "crystal": {
        "intensity_scale": 1.18,
        "thickness_scale": 1.28,
    },
    "satin": {
        "intensity_scale": 0.82,
        "thickness_scale": 0.90,
    },
    "deep": {
        "intensity_scale": 1.08,
        "thickness_scale": 1.06,
    },
}

_GLOWS = {
    "off": (0.0, 0.0),
    "soft": (0.35, 0.12),
    "balanced": (0.75, 0.28),
    "bright": (1.30, 0.48),
}

_DEPTHS = {
    "flat": 0.0,
    "soft": 0.06,
    "floating": 0.14,
}

_SETTINGS = [
    {
        "type": "choice",
        "key": "surface",
        "text": "Поверхность",
        "icon": "msg_customize",
        "default": "frosted",
        "options": [
            {
                "value": "clear",
                "text": "Clear",
                "subtext": "Чистое лёгкое стекло",
            },
            {
                "value": "frosted",
                "text": "Frosted",
                "subtext": "Мягкое матовое размытие",
            },
            {
                "value": "crystal",
                "text": "Crystal",
                "subtext": "Плотная линза с яркими гранями",
            },
            {
                "value": "satin",
                "text": "Satin",
                "subtext": "Спокойная бархатистая поверхность",
            },
            {
                "value": "deep",
                "text": "Deep Glass",
                "subtext": "Выразительное стекло с глубиной",
            },
        ],
    },
    {
        "type": "choice",
        "key": "glow",
        "text": "Внутреннее свечение",
        "icon": "msg_settings",
        "default": "soft",
        "options": [
            {"value": "off", "text": "Выключено"},
            {"value": "soft", "text": "Мягкое"},
            {"value": "balanced", "text": "Выразительное"},
            {"value": "bright", "text": "Яркое"},
        ],
    },
    {
        "type": "choice",
        "key": "depth",
        "text": "Глубина",
        "icon": "msg_customize",
        "default": "soft",
        "options": [
            {"value": "flat", "text": "Плоское"},
            {"value": "soft", "text": "Мягкая тень"},
            {"value": "floating", "text": "Парящее"},
        ],
    },
    {
        "type": "divider",
        "text": (
            "Изменения применяются сразу ко всем поверхностям Blur3. "
            "Анимации не используются, поэтому режим остаётся лёгким."
        ),
    },
    {
        "type": "action",
        "key": "reset",
        "text": "Вернуть рекомендуемый стиль",
        "subtext": "Frosted · мягкое свечение · мягкая тень",
        "icon": "msg_info",
    },
]


def _value(key: str) -> str:
    default = _DEFAULTS[key]
    value = str(_API.get_setting(key, default))
    allowed = {
        "surface": _SURFACES,
        "glow": _GLOWS,
        "depth": _DEPTHS,
    }[key]
    return value if value in allowed else default


def _apply_profile():
    surface = _SURFACES[_value("surface")]
    glow = _GLOWS[_value("glow")]
    depth = _DEPTHS[_value("depth")]
    _API.set_material_profile({
        "intensity_scale": surface["intensity_scale"],
        "thickness_scale": surface["thickness_scale"],
        "stroke_inner_dp": glow[0],
        "stroke_outer_dp": glow[1],
        "shadow_alpha": depth,
    })


def _settings_changed(key: str, value: Any):
    if key == "reset":
        for setting_key, default in _DEFAULTS.items():
            _API.set_setting(setting_key, default)
        _API.request_settings_reload()
    _apply_profile()


def on_load(api):
    global _API
    _API = api
    api.register_settings(_SETTINGS, _settings_changed)
    _apply_profile()
    api.log("LiquidGlass+ 1.0 loaded")


def on_unload(api):
    global _API
    api.set_material_profile(None)
    _API = None
    api.log("LiquidGlass+ unloaded; Blur3 material restored")
