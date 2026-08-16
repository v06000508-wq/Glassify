GLASSIFY_EXTENSION = {
    "id": "glass_date_chips",
    "name": "Glass Date Chips",
    "description": "Стеклянные floating-плашки дат в чате и разделителя непрочитанных сообщений.",
    "version": "1.1",
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
        return False
    left = int(left)
    top = int(top)
    right = int(right)
    bottom = int(bottom)
    width = max(1, right - left)
    height = max(1, bottom - top)
    changed = False
    try:
        changed = (
            int(view.getLeft()) != left
            or int(view.getTop()) != top
            or int(view.getRight()) != right
            or int(view.getBottom()) != bottom
        )
    except Exception:
        changed = True
    if changed:
        try:
            view.measure(_make_exact_spec(width), _make_exact_spec(height))
        except Exception:
            pass
        try:
            view.layout(left, top, right, bottom)
        except Exception:
            pass
    return changed


def _entry_cell(entry):
    if not entry:
        return None
    return entry.get("cell")


def _date_entry(cell):
    try:
        return _patched_dates.get(_api.identity(cell))
    except Exception:
        return None


def _schedule_once(entry, key, delay_ms, callback):
    if not entry:
        return
    try:
        tokens = entry.setdefault("tokens", {})
        token = int(tokens.get(key, 0)) + 1
        tokens[key] = token
    except Exception:
        token = 1
        entry["tokens"] = {key: token}

    def _runner(token=token, entry=entry, key=key, callback=callback):
        try:
            current = (entry.get("tokens") or {}).get(key)
            if current != token:
                return
            callback()
        except Exception:
            pass

    try:
        _api.schedule(_runner, int(delay_ms))
    except Exception:
        pass


def _ensure_date_surface(cell):
    entry = _date_entry(cell)
    if not entry or entry.get("surface") is not None:
        return
    overlay = entry.get("overlay")
    if overlay is None:
        return
    try:
        if int(overlay.getWidth()) <= 0 or int(overlay.getHeight()) <= 0:
            return
    except Exception:
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


def _layout_date(cell, force=False):
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
    chip_width = max(1, min(max(_api.dp(48), text_width + horizontal_padding * 2), max(1, width - _api.dp(24))))
    chip_height = max(_api.dp(25), text_height + _api.dp(8))
    left = int((width - chip_width) / 2)
    top = _api.dp(4)
    right = left + chip_width
    bottom = top + chip_height

    try:
        text = _api.get_field(cell, "customText")
    except Exception:
        text = None
    text_value = "" if text is None else str(text)

    signature = (width, text_width, text_height, left, top, right, bottom, text_value)
    if not force and entry.get("layout_signature") == signature:
        return
    entry["layout_signature"] = signature

    try:
        if str(label.getText()) != text_value:
            label.setText(text_value)
    except Exception:
        try:
            label.setText(text_value)
        except Exception:
            pass

    changed = False
    changed = _measure_and_layout(overlay, left, top, right, bottom) or changed
    changed = _measure_and_layout(label, left, top, right, bottom) or changed

    if changed or force:
        try:
            cell.invalidate()
        except Exception:
            pass

    if entry.get("surface") is None:
        _ensure_date_surface(cell)
        if entry.get("surface") is None:
            _schedule_once(entry, "ensure_date_surface", 120, lambda cell=cell: _ensure_date_surface(cell))


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
            "layout_signature": None,
            "tokens": {},
        }
        _patched_dates[key] = entry

        _layout_date(cell, True)
        _schedule_once(entry, "layout_date", 32, lambda cell=cell: _layout_date(cell, True))
        _schedule_once(entry, "ensure_date_surface", 120, lambda cell=cell: _ensure_date_surface(cell))
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
        if int(background.getWidth()) <= 0 or int(background.getHeight()) <= 0:
            return
    except Exception:
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


def _patch_unread(cell, force=False):
    if cell is None:
        return
    key = _api.identity(cell)
    entry = _patched_unread.get(key)
    if entry is not None and not force:
        if entry.get("surface") is None:
            _ensure_unread_surface(cell)
        return

    try:
        background = cell.getBackgroundLayout()
        if background is None:
            return
        params = background.getLayoutParams()
        if entry is None:
            original = {
                "background_drawable": background.getBackground(),
                "width": getattr(params, "width", None),
                "height": getattr(params, "height", None),
                "leftMargin": getattr(params, "leftMargin", None),
                "topMargin": getattr(params, "topMargin", None),
                "rightMargin": getattr(params, "rightMargin", None),
                "bottomMargin": getattr(params, "bottomMargin", None),
                "gravity": getattr(params, "gravity", None),
                "text_color": None,
                "image_alpha": None,
            }
            try:
                text = cell.getTextView()
                if text is not None:
                    original["text_color"] = text.getCurrentTextColor()
            except Exception:
                pass
            try:
                image = cell.getImageView()
                if image is not None:
                    original["image_alpha"] = image.getAlpha()
            except Exception:
                pass
        else:
            original = entry.get("original") or {}

        signature = (
            _api.dp(28),
            _api.dp(22),
            _api.dp(22),
            _api.dp(6),
            0,
        )
        if entry is None or entry.get("layout_signature") != signature:
            try:
                params.width = -1
                params.height = signature[0]
                params.leftMargin = signature[1]
                params.rightMargin = signature[2]
                params.topMargin = signature[3]
                params.bottomMargin = signature[4]
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

        if entry is None:
            entry = {
                "cell": cell,
                "background": background,
                "surface": None,
                "original": original,
                "layout_signature": signature,
                "tokens": {},
            }
            _patched_unread[key] = entry
        else:
            entry["background"] = background
            entry["layout_signature"] = signature

        _ensure_unread_surface(cell)
        if entry.get("surface") is None:
            _schedule_once(entry, "ensure_unread_surface", 120, lambda cell=cell: _ensure_unread_surface(cell))
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
        text = cell.getTextView()
        if text is not None and original.get("text_color") is not None:
            text.setTextColor(int(original.get("text_color")))
    except Exception:
        pass
    try:
        image = cell.getImageView()
        if image is not None and original.get("image_alpha") is not None:
            image.setAlpha(float(original.get("image_alpha")))
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
            cell = param.thisObject
            try:
                custom_date = int(_api.get_field(cell, "customDate") or 0)
            except Exception:
                custom_date = 0
            if custom_date > 0:
                _patch_date(cell)
            else:
                _unpatch_date(cell)
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

    api.log("Glass Date Chips 1.1 loaded")


def on_unload(api):
    for entry in list(_patched_dates.values()):
        try:
            _unpatch_date(_entry_cell(entry))
        except Exception:
            pass
    for entry in list(_patched_unread.values()):
        try:
            _unpatch_unread(_entry_cell(entry))
        except Exception:
            pass
    _patched_dates.clear()
    _patched_unread.clear()
    _classes.clear()
    api.log("Glass Date Chips unloaded")
