GLASSIFY_EXTENSION = {
    "id": "glass_date_chips",
    "name": "Glass Date Chips",
    "description": "Стеклянные floating-плашки дат в чате и разделителя непрочитанных сообщений.",
    "version": "1.0",
    "api": 3,
    "min_glassify": "0.3.0",
    "min_exteragram": "12.9.0",
}

_api = None
_patched_dates = {}
_patched_unread = {}
_classes = {}


def _class(name):
    value = _classes.get(name)
    if value is None:
        value = _api.find_class(name)
        _classes[name] = value
    return value


def _theme():
    return _class("org.telegram.ui.ActionBar.Theme")


def _theme_key(name, fallback=0):
    try:
        return int(getattr(_theme(), name))
    except Exception:
        return int(fallback)


def _theme_color(name, fallback=-1):
    try:
        key = _theme_key(name, 0)
        return int(_theme().getColor(key))
    except Exception:
        return int(fallback)


def _make_exact_spec(size):
    try:
        return _class("android.view.View$MeasureSpec").makeMeasureSpec(
            int(size), 1073741824
        )
    except Exception:
        return int(size)


def _measure_and_layout(view, left, top, right, bottom):
    if view is None:
        return
    width = max(1, int(right) - int(left))
    height = max(1, int(bottom) - int(top))
    try:
        view.measure(_make_exact_spec(width), _make_exact_spec(height))
    except Exception:
        pass
    try:
        view.layout(int(left), int(top), int(right), int(bottom))
    except Exception:
        pass


def _date_entry(cell):
    try:
        return _patched_dates.get(_api.identity(cell))
    except Exception:
        return None


def _ensure_date_surface(cell):
    entry = _date_entry(cell)
    if not entry or entry.get("surface") is not None:
        return
    overlay = entry.get("overlay")
    if overlay is None:
        return
    try:
        fragment = _api.get_last_fragment()
        if fragment is None:
            return
        surface = _api.create_glass_surface(
            fragment,
            overlay,
            _theme_key("key_chat_serviceBackground", 0),
            0.62,
            _api.dp(13),
            True,
        )
        if surface is not None:
            entry["surface"] = surface
    except Exception as exc:
        _api.log("date surface failed: " + str(exc))


def _layout_date(cell):
    entry = _date_entry(cell)
    if not entry:
        return

    try:
        custom_date = int(_api.get_field(cell, "customDate") or 0)
    except Exception:
        custom_date = 0
    if custom_date <= 0:
        return

    overlay = entry.get("overlay")
    label = entry.get("label")
    if overlay is None or label is None:
        return

    try:
        width = int(cell.getWidth())
    except Exception:
        width = 0
    if width <= 0:
        return

    try:
        text_width = int(_api.get_field(cell, "textWidth") or 0)
    except Exception:
        text_width = 0
    try:
        text_height = int(_api.get_field(cell, "textHeight") or 0)
    except Exception:
        text_height = 0

    if text_width <= 0:
        text_width = _api.dp(64)
    if text_height <= 0:
        text_height = _api.dp(17)

    horizontal_padding = _api.dp(12)
    chip_width = min(width - _api.dp(24), text_width + horizontal_padding * 2)
    chip_height = max(_api.dp(25), text_height + _api.dp(8))
    left = int((width - chip_width) / 2)
    top = _api.dp(4)
    right = left + chip_width
    bottom = top + chip_height

    try:
        text = _api.get_field(cell, "customText")
        if text is not None:
            label.setText(text)
    except Exception:
        pass

    _measure_and_layout(overlay, left, top, right, bottom)
    _measure_and_layout(label, left, top, right, bottom)

    try:
        cell.invalidate()
    except Exception:
        pass

    _ensure_date_surface(cell)


def _patch_date(cell):
    if cell is None:
        return
    key = _api.identity(cell)
    entry = _patched_dates.get(key)
    if entry is not None:
        _layout_date(cell)
        return

    try:
        custom_date = int(_api.get_field(cell, "customDate") or 0)
    except Exception:
        custom_date = 0
    if custom_date <= 0:
        return

    try:
        View = _class("android.view.View")
        TextView = _class("android.widget.TextView")
        Paint = _class("android.graphics.Paint")
        AndroidUtilities = _class("org.telegram.messenger.AndroidUtilities")

        context = cell.getContext()
        overlay = View(context)
        label = TextView(context)

        try:
            overlay.setClickable(False)
            overlay.setFocusable(False)
        except Exception:
            pass
        try:
            label.setClickable(False)
            label.setFocusable(False)
            label.setSingleLine(True)
            label.setIncludeFontPadding(False)
            label.setGravity(17)
            label.setTextSize(13.0)
            label.setTextColor(_theme_color("key_chat_serviceText", -1))
            label.setTypeface(AndroidUtilities.bold())
        except Exception:
            pass

        original = {
            "overrideBackground": _api.get_field(cell, "overrideBackground"),
            "overrideText": _api.get_field(cell, "overrideText"),
            "overrideBackgroundPaint": _api.get_field(cell, "overrideBackgroundPaint"),
            "overrideTextPaint": _api.get_field(cell, "overrideTextPaint"),
        }

        transparent = Paint()
        transparent.setColor(0)
        transparent.setAlpha(0)

        original_text_paint = _api.get_field(cell, "textPaint")
        if original_text_paint is None:
            try:
                paint_key = getattr(_theme(), "key_paint_chatActionText")
                original_text_paint = _theme().getThemePaint(paint_key)
            except Exception:
                original_text_paint = None

        _api.set_field(cell, "overrideBackground", 0)
        _api.set_field(cell, "overrideText", _theme_key("key_chat_serviceText", 0))
        _api.set_field(cell, "overrideBackgroundPaint", transparent)
        if original_text_paint is not None:
            _api.set_field(cell, "overrideTextPaint", original_text_paint)

        try:
            cell.addView(overlay, 0)
        except Exception:
            cell.addView(overlay)
        cell.addView(label)

        entry = {
            "cell": cell,
            "overlay": overlay,
            "label": label,
            "surface": None,
            "original": original,
        }
        _patched_dates[key] = entry

        _layout_date(cell)
        _api.schedule(lambda cell=cell: _layout_date(cell), 32)
        _api.schedule(lambda cell=cell: _ensure_date_surface(cell), 120)
    except Exception as exc:
        _api.log("date patch failed: " + str(exc))


def _unpatch_date(cell):
    if cell is None:
        return
    key = _api.identity(cell)
    entry = _patched_dates.pop(key, None)
    if not entry:
        return

    try:
        overlay = entry.get("overlay")
        if overlay is not None:
            cell.removeView(overlay)
    except Exception:
        pass
    try:
        label = entry.get("label")
        if label is not None:
            cell.removeView(label)
    except Exception:
        pass

    original = entry.get("original") or {}
    for name in (
        "overrideBackground",
        "overrideText",
        "overrideBackgroundPaint",
        "overrideTextPaint",
    ):
        try:
            _api.set_field(cell, name, original.get(name))
        except Exception:
            pass
    try:
        cell.invalidate()
    except Exception:
        pass


def _ensure_unread_surface(cell):
    if cell is None:
        return
    key = _api.identity(cell)
    entry = _patched_unread.get(key)
    if not entry or entry.get("surface") is not None:
        return
    background = entry.get("background")
    if background is None:
        return
    try:
        fragment = _api.get_last_fragment()
        if fragment is None:
            return
        surface = _api.create_glass_surface(
            fragment,
            background,
            _theme_key("key_chat_unreadMessagesStartBackground", 0),
            0.68,
            _api.dp(14),
            True,
        )
        if surface is not None:
            entry["surface"] = surface
    except Exception as exc:
        _api.log("unread surface failed: " + str(exc))


def _patch_unread(cell):
    if cell is None:
        return
    key = _api.identity(cell)
    if key in _patched_unread:
        return

    try:
        background = cell.getBackgroundLayout()
        if background is None:
            return
        params = background.getLayoutParams()
        original = {
            "background_drawable": background.getBackground(),
            "width": getattr(params, "width", None),
            "height": getattr(params, "height", None),
            "leftMargin": getattr(params, "leftMargin", None),
            "topMargin": getattr(params, "topMargin", None),
            "rightMargin": getattr(params, "rightMargin", None),
            "bottomMargin": getattr(params, "bottomMargin", None),
            "gravity": getattr(params, "gravity", None),
        }

        try:
            params.width = -1
            params.height = _api.dp(28)
            params.leftMargin = _api.dp(22)
            params.rightMargin = _api.dp(22)
            params.topMargin = _api.dp(6)
            params.bottomMargin = 0
            background.setLayoutParams(params)
        except Exception:
            pass

        try:
            background.setBackground(None)
        except Exception:
            pass

        try:
            text = cell.getTextView()
            if text is not None:
                text.setTextColor(_theme_color("key_chat_unreadMessagesStartText", -1))
        except Exception:
            pass
        try:
            image = cell.getImageView()
            if image is not None:
                image.setAlpha(0.88)
        except Exception:
            pass

        _patched_unread[key] = {
            "cell": cell,
            "background": background,
            "surface": None,
            "original": original,
        }
        _ensure_unread_surface(cell)
        _api.schedule(lambda cell=cell: _ensure_unread_surface(cell), 120)
        try:
            cell.requestLayout()
            cell.invalidate()
        except Exception:
            pass
    except Exception as exc:
        _api.log("unread patch failed: " + str(exc))


def _unpatch_unread(cell):
    if cell is None:
        return
    key = _api.identity(cell)
    entry = _patched_unread.pop(key, None)
    if not entry:
        return
    background = entry.get("background")
    original = entry.get("original") or {}
    if background is None:
        return
    try:
        background.setBackground(original.get("background_drawable"))
    except Exception:
        pass
    try:
        params = background.getLayoutParams()
        for name in (
            "width",
            "height",
            "leftMargin",
            "topMargin",
            "rightMargin",
            "bottomMargin",
            "gravity",
        ):
            value = original.get(name)
            if value is not None:
                setattr(params, name, value)
        background.setLayoutParams(params)
    except Exception:
        pass
    try:
        cell.requestLayout()
        cell.invalidate()
    except Exception:
        pass


class _DateSetHook(MethodHook):
    def after_hooked_method(self, param):
        try:
            _patch_date(param.thisObject)
        except Exception as exc:
            _api.log("setCustomDate hook failed: " + str(exc))


class _DateLayoutHook(MethodHook):
    def after_hooked_method(self, param):
        try:
            _layout_date(param.thisObject)
        except Exception:
            pass


class _DateMessageHook(MethodHook):
    def before_hooked_method(self, param):
        try:
            _unpatch_date(param.thisObject)
        except Exception:
            pass


class _UnreadCtorHook(MethodHook):
    def after_hooked_method(self, param):
        try:
            _patch_unread(param.thisObject)
        except Exception as exc:
            _api.log("ChatUnreadCell constructor hook failed: " + str(exc))


class _UnreadTextHook(MethodHook):
    def after_hooked_method(self, param):
        try:
            _patch_unread(param.thisObject)
            _ensure_unread_surface(param.thisObject)
        except Exception:
            pass


def on_load(api):
    global _api
    _api = api

    ChatActionCell = api.find_class("org.telegram.ui.Cells.ChatActionCell")
    ChatUnreadCell = api.find_class("org.telegram.ui.Cells.ChatUnreadCell")

    api.hook_all_methods(ChatActionCell, "setCustomDate", _DateSetHook())
    api.hook_all_methods(ChatActionCell, "onLayout", _DateLayoutHook())
    api.hook_all_methods(ChatActionCell, "setMessageObject", _DateMessageHook())

    api.hook_all_constructors(ChatUnreadCell, _UnreadCtorHook())
    api.hook_all_methods(ChatUnreadCell, "setText", _UnreadTextHook())

    api.log("Glass Date Chips 1.0 loaded")


def on_unload(api):
    for entry in list(_patched_dates.values()):
        try:
            _unpatch_date(entry.get("cell"))
        except Exception:
            pass
    for entry in list(_patched_unread.values()):
        try:
            _unpatch_unread(entry.get("cell"))
        except Exception:
            pass
    _patched_dates.clear()
    _patched_unread.clear()
    _classes.clear()
    api.log("Glass Date Chips unloaded")
