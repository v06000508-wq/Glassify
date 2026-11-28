GLASSIFY_EXTENSION = {
    "id": "liquidglass_plus",
    "name": "LiquidGlass+",
    "version": "1.3",
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
        "intensity_scale": 0.20,
        "thickness_scale": 0.25,
        "overlay_alpha_scale": 0.35,
        "glow_scale": 0.55,
        "depth_scale": 0.50,
    },
    "frosted": {
        "intensity_scale": 0.42,
        "thickness_scale": 0.55,
        "overlay_alpha_scale": 1.35,
        "glow_scale": 0.80,
        "depth_scale": 0.72,
    },
    "crystal": {
        "intensity_scale": 1.80,
        "thickness_scale": 1.45,
        "overlay_alpha_scale": 0.52,
        "glow_scale": 1.00,
        "depth_scale": 0.86,
    },
    "satin": {
        "intensity_scale": 0.68,
        "thickness_scale": 0.82,
        "overlay_alpha_scale": 0.88,
        "glow_scale": 0.68,
        "depth_scale": 0.62,
    },
    "deep": {
        "intensity_scale": 1.32,
        "thickness_scale": 2.00,
        "overlay_alpha_scale": 1.35,
        "glow_scale": 1.00,
        "depth_scale": 1.00,
    },
}

_GLOWS = {
    "off": (0.0, 0.0),
    "soft": (0.70, 0.24),
    "balanced": (1.55, 0.72),
    "bright": (2.50, 1.50),
}

_DEPTHS = {
    "flat": 0.0,
    "soft": 0.12,
    "floating": 0.22,
}

_SETTINGS = [
    {
        "type": "choice",
        "key": "surface",
        "text": "Поверхность",
        "icon": "msg_customize",
        "default": "frosted",
        "options": [
            {"value": "clear", "text": "Clear", "subtext": "Почти прозрачное стекло с тонкой линзой"},
            {"value": "frosted", "text": "Frosted", "subtext": "Плотная матовая поверхность без сильного преломления"},
            {"value": "crystal", "text": "Crystal", "subtext": "Прозрачная оптическая линза с сильным преломлением"},
            {"value": "satin", "text": "Satin", "subtext": "Молочное полуматовое стекло с мягкими краями"},
            {"value": "deep", "text": "Deep Glass", "subtext": "Тяжёлая толстая линза с плотным фоном"},
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
            "Тип поверхности меняет материал стеклянных элементов: прозрачность, "
            "матовость, преломление и толщину. Верхнее размытие шапки Glassify "
            "всегда остаётся Frosted и не зависит от выбранной поверхности."
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
    allowed = {"surface": _SURFACES, "glow": _GLOWS, "depth": _DEPTHS}[key]
    return value if value in allowed else default


def _apply_profile():
    surface = _SURFACES[_value("surface")]
    glow = _GLOWS[_value("glow")]
    depth = _DEPTHS[_value("depth")]
    _API.set_material_profile({
        "intensity_scale": surface["intensity_scale"],
        "thickness_scale": surface["thickness_scale"],
        "stroke_inner_dp": min(2.50, glow[0] * surface["glow_scale"]),
        "stroke_outer_dp": min(1.50, glow[1] * surface["glow_scale"]),
        "shadow_alpha": min(0.22, depth * surface["depth_scale"]),
        "overlay_alpha_scale": surface["overlay_alpha_scale"],
    })


def _settings_changed(key, value):
    if key == "reset":
        for setting_key, default in _DEFAULTS.items():
            _API.set_setting(setting_key, default)
        _API.request_settings_reload()
    _apply_profile()
    _API.log("material changed: " + _value("surface") + "/" + _value("glow") + "/" + _value("depth"))


def on_load(api):
    global _API
    _API = api
    api.register_settings(_SETTINGS, _settings_changed)
    _apply_profile()
    api.log("LiquidGlass+ 1.3 loaded")


def on_unload(api):
    global _API
    api.set_material_profile(None)
    _API = None
    api.log("LiquidGlass+ unloaded; Blur3 material restored")
