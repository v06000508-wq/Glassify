GLASSIFY_EXTENSION = {
    "id": "touch_glass",
    "name": "Touch Glass",
    "version": "0.1",
    "api": 3,
}

_API = None
_View = None
_GradientDrawable = None

_TRACKED = {}
_EFFECTS = {}
_GENERATION = 0

_DEFAULTS = {
    "depth": "balanced",
    "radius": "normal",
    "wave": "soft",
    "return": "balanced",
}

_DEPTH = {
    "soft": 0.72,
    "balanced": 1.00,
    "deep": 1.30,
}

_RADIUS = {
    "compact": 36,
    "normal": 52,
    "wide": 68,
}

_WAVE = {
    "off": 0.0,
    "soft": 0.72,
    "strong": 1.00,
}

_RETURN_FRAMES = {
    "fast": 8,
    "balanced": 12,
    "smooth": 16,
}

_SETTINGS = [
    {
        "type": "choice",
        "key": "depth",
        "text": "Глубина касания",
        "icon": "msg_customize",
        "default": "balanced",
        "options": [
            {"value": "soft", "text": "Мягкая", "subtext": "Лёгкая жидкая вмятина"},
            {"value": "balanced", "text": "Обычная", "subtext": "Заметная реакция без перегруза"},
            {"value": "deep", "text": "Глубокая", "subtext": "Сильнее тень, блик и продавливание"},
        ],
    },
    {
        "type": "choice",
        "key": "radius",
        "text": "Размер вмятины",
        "icon": "msg_settings",
        "default": "normal",
        "options": [
            {"value": "compact", "text": "Компактный"},
            {"value": "normal", "text": "Обычный"},
            {"value": "wide", "text": "Широкий"},
        ],
    },
    {
        "type": "choice",
        "key": "wave",
        "text": "Жидкая волна",
        "icon": "msg_blur",
        "default": "soft",
        "options": [
            {"value": "off", "text": "Выключена"},
            {"value": "soft", "text": "Мягкая"},
            {"value": "strong", "text": "Выразительная"},
        ],
    },
    {
        "type": "choice",
        "key": "return",
        "text": "Возврат стекла",
        "icon": "msg_settings",
        "default": "balanced",
        "options": [
            {"value": "fast", "text": "Быстрый"},
            {"value": "balanced", "text": "Естественный"},
            {"value": "smooth", "text": "Плавный"},
        ],
    },
    {
        "type": "divider",
        "text": (
            "Touch Glass реагирует только на поверхности Blur3, созданные "
            "Glassify. Эффект не заменяет обычные действия Telegram и не "
            "изменяет материал LiquidGlass+."
        ),
    },
]


def _value(key):
    default = _DEFAULTS[key]
    value = str(_API.get_setting(key, default))
    tables = {
        "depth": _DEPTH,
        "radius": _RADIUS,
        "wave": _WAVE,
        "return": _RETURN_FRAMES,
    }
    return value if value in tables[key] else default


def _depth():
    return float(_DEPTH[_value("depth")])


def _radius_px():
    return int(_API.dp(int(_RADIUS[_value("radius")])) )


def _wave_strength():
    return float(_WAVE[_value("wave")])


def _return_frames():
    return int(_RETURN_FRAMES[_value("return")])


def _identity(view):
    if view is None or _API is None:
        return 0
    try:
        return int(_API.identity(view))
    except Exception:
        return 0


def _track(view):
    if view is None:
        return
    key = _identity(view)
    if not key:
        return

    _TRACKED[key] = view

    if len(_TRACKED) > 160:
        remove_count = len(_TRACKED) - 128
        for stale_key in list(_TRACKED.keys()):
            if stale_key == key:
                continue
            _drop_effect(stale_key)
            _TRACKED.pop(stale_key, None)
            remove_count -= 1
            if remove_count <= 0:
                break


def _find_target(source, x=None, y=None):
    current = source
    px = float(x) if x is not None else None
    py = float(y) if y is not None else None

    steps = 0
    while current is not None and steps < 10:
        key = _identity(current)
        if key in _TRACKED:
            return key, current, px, py

        parent = None
        try:
            parent = current.getParent()
        except Exception:
            parent = None
        if parent is None:
            break

        if px is not None and py is not None:
            try:
                px += float(current.getLeft())
                py += float(current.getTop())
            except Exception:
                pass
            try:
                px += float(current.getTranslationX())
                py += float(current.getTranslationY())
            except Exception:
                pass
            try:
                px -= float(parent.getScrollX())
                py -= float(parent.getScrollY())
            except Exception:
                pass

        current = parent
        steps += 1

    return 0, None, None, None


def _new_oval(color, stroke_width=0, stroke_color=0):
    drawable = _GradientDrawable()
    try:
        drawable.setShape(int(_GradientDrawable.OVAL))
    except Exception:
        drawable.setShape(1)
    drawable.setColor(int(color))
    if int(stroke_width) > 0:
        drawable.setStroke(int(stroke_width), int(stroke_color))
    return drawable


def _effect_for(key, view):
    state = _EFFECTS.get(key)
    if state is not None:
        return state

    overlay = None
    try:
        overlay = view.getOverlay()
    except Exception:
        return None
    if overlay is None:
        return None

    shadow = _new_oval(0x24000000)
    inner = _new_oval(0x10FFFFFF)
    highlight = _new_oval(
        0x00000000,
        max(1, int(_API.dp(1.0))),
        0x42FFFFFF,
    )
    wave = _new_oval(
        0x00000000,
        max(1, int(_API.dp(1.2))),
        0x48FFFFFF,
    )

    for drawable in (shadow, inner, highlight, wave):
        try:
            overlay.add(drawable)
        except Exception:
            try:
                for added in (shadow, inner, highlight, wave):
                    overlay.remove(added)
            except Exception:
                pass
            return None

    state = {
        "view": view,
        "overlay": overlay,
        "shadow": shadow,
        "inner": inner,
        "highlight": highlight,
        "wave": wave,
        "x": 0.0,
        "y": 0.0,
        "pressed": False,
        "token": 0,
    }
    _EFFECTS[key] = state
    return state


def _bounds(drawable, cx, cy, radius):
    r = max(1.0, float(radius))
    left = int(float(cx) - r)
    top = int(float(cy) - r)
    right = int(float(cx) + r)
    bottom = int(float(cy) + r)
    try:
        drawable.setBounds(left, top, right, bottom)
    except Exception:
        pass


def _alpha(drawable, value):
    try:
        drawable.setAlpha(max(0, min(255, int(value))))
    except Exception:
        pass


def _invalidate(state):
    view = state.get("view")
    if view is not None:
        try:
            view.invalidate()
        except Exception:
            pass


def _render_pressed(state, progress=1.0, wave_progress=0.0):
    depth = _depth()
    radius = float(_radius_px())
    cx = float(state.get("x", 0.0))
    cy = float(state.get("y", 0.0))
    p = max(0.0, min(1.0, float(progress)))

    dent_radius = radius * (0.62 + 0.38 * p)
    inner_radius = dent_radius * 0.66
    highlight_radius = dent_radius * 0.90

    _bounds(state["shadow"], cx, cy + radius * 0.045, dent_radius)
    _bounds(state["inner"], cx, cy - radius * 0.025, inner_radius)
    _bounds(state["highlight"], cx, cy, highlight_radius)

    _alpha(state["shadow"], int(132.0 * depth * p))
    _alpha(state["inner"], int(108.0 * depth * p))
    _alpha(state["highlight"], int(150.0 * depth * p))

    wave_strength = _wave_strength()
    if wave_strength <= 0.0:
        _alpha(state["wave"], 0)
    else:
        wp = max(0.0, min(1.0, float(wave_progress)))
        wave_radius = radius * (0.35 + 0.95 * wp)
        _bounds(state["wave"], cx, cy, wave_radius)
        _alpha(
            state["wave"],
            int(150.0 * wave_strength * (1.0 - wp) * p),
        )

    _invalidate(state)


def _press_frame(key, token, frame):
    if _API is None:
        return
    state = _EFFECTS.get(key)
    if state is None or int(state.get("token", 0)) != int(token):
        return
    if not bool(state.get("pressed", False)):
        return

    total = 6
    p = min(1.0, float(frame) / float(total))
    _render_pressed(state, p, p)

    if frame < total:
        _API.schedule(
            lambda key=key, token=token, frame=frame + 1:
                _press_frame(key, token, frame),
            16,
        )


def _press(key, view, x=None, y=None):
    global _GENERATION

    state = _effect_for(key, view)
    if state is None:
        return

    width = 0
    height = 0
    try:
        width = int(view.getWidth())
        height = int(view.getHeight())
    except Exception:
        pass

    if x is None or y is None:
        x = float(width) * 0.5
        y = float(height) * 0.5

    if width > 0:
        x = max(0.0, min(float(width), float(x)))
    if height > 0:
        y = max(0.0, min(float(height), float(y)))

    state["x"] = float(x)
    state["y"] = float(y)

    if bool(state.get("pressed", False)):
        _render_pressed(state, 1.0, 0.62)
        return

    _GENERATION += 1
    token = int(_GENERATION)
    state["token"] = token
    state["pressed"] = True
    _render_pressed(state, 0.35, 0.0)
    _API.schedule(
        lambda key=key, token=token: _press_frame(key, token, 1),
        16,
    )


def _move(key, view, x, y):
    state = _EFFECTS.get(key)
    if state is None or not bool(state.get("pressed", False)):
        _press(key, view, x, y)
        return

    width = 0
    height = 0
    try:
        width = int(view.getWidth())
        height = int(view.getHeight())
    except Exception:
        pass

    if width > 0:
        x = max(0.0, min(float(width), float(x)))
    if height > 0:
        y = max(0.0, min(float(height), float(y)))

    state["x"] = float(x)
    state["y"] = float(y)
    _render_pressed(state, 1.0, 0.72)


def _release_frame(key, token, frame, total):
    if _API is None:
        return
    state = _EFFECTS.get(key)
    if state is None or int(state.get("token", 0)) != int(token):
        return
    if bool(state.get("pressed", False)):
        return

    p = min(1.0, float(frame) / float(max(1, int(total))))
    remain = 1.0 - p
    eased = remain * remain

    radius = float(_radius_px())
    cx = float(state.get("x", 0.0))
    cy = float(state.get("y", 0.0))

    _bounds(
        state["shadow"],
        cx,
        cy + radius * 0.04,
        radius * (1.0 + 0.14 * p),
    )
    _bounds(
        state["inner"],
        cx,
        cy,
        radius * (0.66 + 0.18 * p),
    )
    _bounds(
        state["highlight"],
        cx,
        cy,
        radius * (0.90 + 0.22 * p),
    )

    _alpha(state["shadow"], int(132.0 * _depth() * eased))
    _alpha(state["inner"], int(108.0 * _depth() * eased))
    _alpha(state["highlight"], int(150.0 * _depth() * eased))

    wave_strength = _wave_strength()
    if wave_strength > 0.0:
        _bounds(
            state["wave"],
            cx,
            cy,
            radius * (0.78 + 1.10 * p),
        )
        _alpha(
            state["wave"],
            int(170.0 * wave_strength * remain),
        )
    else:
        _alpha(state["wave"], 0)

    _invalidate(state)

    if frame < total:
        _API.schedule(
            lambda key=key, token=token, frame=frame + 1, total=total:
                _release_frame(key, token, frame, total),
            16,
        )
    else:
        _alpha(state["shadow"], 0)
        _alpha(state["inner"], 0)
        _alpha(state["highlight"], 0)
        _alpha(state["wave"], 0)
        _invalidate(state)


def _release(key, view):
    global _GENERATION

    state = _EFFECTS.get(key)
    if state is None:
        return
    if not bool(state.get("pressed", False)):
        return

    _GENERATION += 1
    token = int(_GENERATION)
    state["token"] = token
    state["pressed"] = False

    total = _return_frames()
    _API.schedule(
        lambda key=key, token=token, total=total:
            _release_frame(key, token, 1, total),
        16,
    )


def _drop_effect(key):
    state = _EFFECTS.pop(key, None)
    if state is None:
        return

    overlay = state.get("overlay")
    if overlay is None:
        return
    for name in ("shadow", "inner", "highlight", "wave"):
        drawable = state.get(name)
        if drawable is not None:
            try:
                overlay.remove(drawable)
            except Exception:
                pass


def _cleanup_effects():
    for key in list(_EFFECTS.keys()):
        _drop_effect(key)
    _TRACKED.clear()


class _FactoryHook(MethodHook):
    def after_hooked_method(self, param):
        try:
            if len(param.args) <= 0:
                return
            view = param.args[0]
            if view is not None:
                _track(view)
        except Exception as exc:
            if _API is not None:
                _API.log("factory tracking failed: " + str(exc))


class _HotspotHook(MethodHook):
    def after_hooked_method(self, param):
        if _API is None:
            return
        try:
            if len(param.args) < 2:
                return
            source = param.thisObject
            key, target, x, y = _find_target(
                source,
                float(param.args[0]),
                float(param.args[1]),
            )
            if not key or target is None:
                return

            state = _EFFECTS.get(key)
            if state is not None and bool(state.get("pressed", False)):
                _move(key, target, x, y)
            else:
                try:
                    if bool(target.isPressed()) or bool(source.isPressed()):
                        _press(key, target, x, y)
                except Exception:
                    pass
        except Exception:
            return


class _PressedHook(MethodHook):
    def after_hooked_method(self, param):
        if _API is None:
            return
        try:
            if len(param.args) <= 0:
                return

            pressed = bool(param.args[0])
            source = param.thisObject
            key, target, _x, _y = _find_target(source)
            if not key or target is None:
                return

            state = _EFFECTS.get(key)
            if pressed:
                if state is None or not bool(state.get("pressed", False)):
                    _press(key, target)
            else:
                if state is not None and bool(state.get("pressed", False)):
                    _release(key, target)
        except Exception:
            return


def _settings_changed(key, value):
    if _API is None:
        return

    for state in list(_EFFECTS.values()):
        if bool(state.get("pressed", False)):
            _render_pressed(state, 1.0, 0.72)

    _API.log(
        "Touch Glass settings: "
        + _value("depth") + "/"
        + _value("radius") + "/"
        + _value("wave") + "/"
        + _value("return")
    )


def on_load(api):
    global _API, _View, _GradientDrawable

    _API = api
    _View = api.find_class("android.view.View")
    _GradientDrawable = api.find_class(
        "android.graphics.drawable.GradientDrawable"
    )
    factory = api.find_class(
        "org.telegram.ui.Components.blur3.drawable."
        "BlurredBackgroundDrawableViewFactory"
    )

    api.register_settings(_SETTINGS, _settings_changed)
    api.hook_all_methods(factory, "create", _FactoryHook())
    api.hook_all_methods(_View, "drawableHotspotChanged", _HotspotHook())
    api.hook_all_methods(_View, "setPressed", _PressedHook())
    api.rebuild_current_fragment_views()
    api.log("Touch Glass 0.1 loaded")


def on_unload(api):
    global _API, _View, _GradientDrawable, _GENERATION

    _GENERATION += 1
    _cleanup_effects()

    _API = None
    _View = None
    _GradientDrawable = None
    api.log("Touch Glass unloaded")
