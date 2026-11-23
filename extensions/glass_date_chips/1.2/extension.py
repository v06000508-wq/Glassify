GLASSIFY_EXTENSION = {
    "id": "glass_date_chips",
    "name": "Glass Date Chips",
    "description": "Стеклянные плашки дат и непрочитанных сообщений с адаптивным контрастом и плавной сменой даты.",
    "version": "1.2",
    "api": 3,
    "min_glassify": "0.5.0",
    "min_exteragram": "12.10.6",
}

_api = None
_patched_dates = {}
_patched_unread = {}
_classes = {}
_enabled = {"date": True, "unread": True}
_wallpaper_cache = {}
_SETTINGS = [
    {
        "type": "choice",
        "key": key,
        "text": text,
        "default": "on",
        "options": [
            {"value": "on", "text": "Стекло"},
            {"value": "off", "text": "Штатное оформление"},
        ],
    }
    for key, text in (("date", "Плашки дат"), ("unread", "Разделитель непрочитанных"))
]


def _class(name):
    value = _classes.get(name)
    if value is None:
        value = _api.find_class(name)
        _classes[name] = value
    return value


def _hook_class(name):
    target = _class(name)
    if target is None:
        raise RuntimeError(f"Класс Telegram недоступен: {name}")
    # Chaquopy's class proxy exposes Java's Foo.class via Foo.getClass().
    # Some SDK builds already return a java.lang.Class from find_class.
    if not hasattr(target, "getDeclaredMethods"):
        target = target.getClass()
    if str(target.getName()) != name:
        raise RuntimeError(f"Не удалось получить Java-класс для хука: {name}")
    return target


def _theme():
    return _class("org.telegram.ui.ActionBar.Theme")


def _theme_key(name, fallback=0):
    try:
        return int(getattr(_theme(), name))
    except Exception:
        return int(fallback)


def _theme_color(name, fallback=-1, fragment=None):
    try:
        key = _theme_key(name, 0)
        if fragment is not None:
            provider = _api.get_field(fragment, "themeDelegate") or _api.get_field(fragment, "resourceProvider")
            if provider is not None:
                getter = getattr(provider, "getColor", None)
                color = getter(key) if getter is not None else None
                if color is not None:
                    return int(color)
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


def _measure_and_layout(view, left, top, right, bottom, force=False):
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
    if changed or force:
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


def _now():
    return int(_class("android.os.SystemClock").uptimeMillis())


def _luminance(color):
    channels = []
    for shift in (16, 8, 0):
        channel = ((int(color) >> shift) & 255) / 255.0
        channels.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
    return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722


def _sample_bitmap(bitmap):
    width, height = int(bitmap.getWidth()), int(bitmap.getHeight())
    if width <= 0 or height <= 0:
        return ()
    return tuple(
        _luminance(bitmap.getPixel((x + 1) * width // 10, (y + 1) * height // 10))
        for y in range(8) for x in range(8)
    )


def _sample_wallpaper(wallpaper):
    if wallpaper is None:
        return ()
    try:
        if hasattr(wallpaper, "getColor"):
            return (_luminance(wallpaper.getColor()),)
        if hasattr(wallpaper, "getBitmap"):
            bitmap = wallpaper.getBitmap()
            if bitmap is not None:
                try:
                    return _sample_bitmap(bitmap)
                except Exception:
                    try:
                        Bitmap = _class("android.graphics.Bitmap")
                        Config = _class("android.graphics.Bitmap$Config")
                        small = Bitmap.createScaledBitmap(bitmap, 32, 32, True)
                        software = small.copy(Config.ARGB_8888, False)
                        try:
                            return _sample_bitmap(software)
                        finally:
                            software.recycle()
                    except Exception:
                        pass
        state = wallpaper.getConstantState()
        if state is None:
            return ()
        clone = state.newDrawable().mutate()
        Bitmap = _class("android.graphics.Bitmap")
        Config = _class("android.graphics.Bitmap$Config")
        sampled = Bitmap.createBitmap(32, 32, Config.ARGB_8888)
        try:
            canvas = _class("android.graphics.Canvas")(sampled)
            clone.setBounds(0, 0, 32, 32)
            clone.draw(canvas)
            return _sample_bitmap(sampled)
        finally:
            sampled.recycle()
    except Exception:
        return ()


def _wallpaper_profile(fragment):
    fragment_id = _api.identity(fragment)
    now = _now()
    if _wallpaper_cache.get("fragment") == fragment_id and now < _wallpaper_cache["next_check"]:
        return _wallpaper_cache["profile"]

    wallpaper = None
    try:
        delegate = _api.get_field(fragment, "themeDelegate")
        if delegate is not None and hasattr(delegate, "getWallpaperDrawable"):
            wallpaper = delegate.getWallpaperDrawable()
    except Exception:
        pass
    if wallpaper is None:
        try:
            wallpaper = _theme().getCachedWallpaperNonBlocking()
        except Exception:
            pass
    wallpaper_id = _api.identity(wallpaper) if wallpaper is not None else 0
    if _wallpaper_cache.get("wallpaper") == wallpaper_id:
        profile = _wallpaper_cache["profile"]
    else:
        samples = _sample_wallpaper(wallpaper)
        values = sorted(samples)
        if not values:
            profile = ((), 0.0)
        else:
            spread = values[len(values) * 9 // 10] - values[len(values) // 10]
            if len(samples) == 64:
                # Adjacent changes distinguish textured photos from a gentle gradient.
                variation = sum(
                    abs(samples[y * 8 + x] - samples[y * 8 + x + 1])
                    + abs(samples[y * 8 + x] - samples[(y + 1) * 8 + x])
                    for y in range(7) for x in range(7)
                ) / 98.0
            else:
                variation = 0.0
            profile = (values, min(1.0, spread * 1.2 + variation * 2.0))

    _wallpaper_cache.update(
        fragment=fragment_id,
        wallpaper=wallpaper_id,
        next_check=now + 1200,
        profile=profile,
    )
    return profile


def _contrast_opacity(profile, foreground, base):
    values, busyness = profile
    if not values:
        return base
    text = _luminance(foreground)
    ratios = sorted((max(text, value) + 0.05) / (min(text, value) + 0.05) for value in values)
    low_contrast = max(0.0, min(1.0, (4.5 - ratios[len(ratios) // 4]) / 3.5))
    # Keep the normal glass on quiet backgrounds and make busy or low-contrast
    # backgrounds visibly denser. Quantization avoids tiny changes in tint.
    correction = max(busyness, low_contrast * 0.8)
    return min(0.96, round(base + (0.96 - base) * correction, 2))


def _update_surface(entry, kind):
    view = entry["overlay"] if kind == "date" else entry["background"]
    now = _now()
    if int(view.getWidth()) <= 0 or int(view.getHeight()) <= 0:
        return
    if now < entry.get("next_surface_check", 0):
        return
    surface = entry.get("surface")
    entry["next_surface_check"] = now + (1200 if surface is not None else 200)

    fragment = _api.get_last_fragment()
    if fragment is None:
        return
    if kind == "date":
        background_key, text_key, base, radius = "key_chat_serviceBackground", "key_chat_serviceText", 0.62, 13
    else:
        background_key, text_key, base, radius = "key_chat_unreadMessagesStartBackground", "key_chat_unreadMessagesStartText", 0.68, 14
    text_color = _theme_color(text_key, -1, fragment)
    profile = _wallpaper_profile(fragment)
    signature = (profile, text_color)
    if entry.get("contrast_signature") != signature:
        entry["contrast_signature"] = signature
        entry["target_opacity"] = _contrast_opacity(profile, text_color, base)
        if kind == "date":
            entry["label"].setTextColor(text_color)
            entry["previous_label"].setTextColor(text_color)
        else:
            label = entry["cell"].getTextView()
            if label is not None:
                label.setTextColor(text_color)
    opacity = entry["target_opacity"]
    if surface is None:
        entry["fragment_id"] = _api.identity(fragment)
        surface = _api.create_glass_surface(
            fragment, view, _theme_key(background_key), opacity, _api.dp(radius), True
        )
        if surface is not None:
            cell = entry["cell"]
            if kind == "date":
                entry["label"].setAlpha(1.0)
                view.setAlpha(1.0)
            entry["surface"] = surface
            entry["opacity"] = opacity
            entry["next_surface_check"] = now + 1200
            cell.invalidate()
        return

    if entry.get("opacity") != opacity:
        provider = surface.get("provider")
        if provider is not None:
            if hasattr(provider, "setAlpha"):
                provider.setAlpha(float(opacity))
            elif _api.set_field(provider, "alpha", float(opacity)):
                provider.updateColors()
            else:
                return
            surface["drawable"].updateColors()
            view.invalidate()
            entry["opacity"] = opacity


def _request_surface(entry, kind):
    if entry.get("surface_retry_pending"):
        return
    entry["surface_retry_pending"] = True
    entries = _patched_dates if kind == "date" else _patched_unread
    cell_id = _api.identity(entry["cell"])

    def retry():
        if _api is None or entries.get(cell_id) is not entry or not _enabled[kind]:
            return
        entry["surface_retry_pending"] = False
        _update_surface(entry, kind)

    _api.schedule(retry, 220)


def _is_date(cell):
    return (
        cell is not None
        and int(_api.get_field(cell, "customDate") or 0) > 0
        and _api.get_field(cell, "currentMessageObject") is None
    )


def _animate_date(entry, left, top, right, bottom, text):
    overlay, label, old = entry["overlay"], entry["label"], entry["previous_label"]
    previous_text = entry.get("text", "")
    text_changed = previous_text != text
    geometry_changed = entry.get("bounds") != (left, top, right, bottom)
    if not text_changed and not geometry_changed:
        return

    ready = entry.get("surface") is not None
    animate = (
        ready and bool(previous_text) and bool(text) and text_changed
        and int(entry["cell"].getVisibility()) == 0 and float(entry["cell"].getAlpha()) > 0.01
    )
    if animate:
        Animator = _class("android.animation.ValueAnimator")
        animate = not hasattr(Animator, "areAnimatorsEnabled") or Animator.areAnimatorsEnabled()

    if geometry_changed:
        visible_width = int(overlay.getWidth()) * float(overlay.getScaleX())
        overlay.animate().cancel()
        _measure_and_layout(overlay, left, top, right, bottom)
        if animate and visible_width > 0:
            overlay.setScaleX(float(visible_width / max(1, right - left)))
            overlay.animate().scaleX(1.0).setDuration(150).start()
        else:
            overlay.setScaleX(1.0)

    if text_changed:
        label.animate().cancel()
        old.animate().cancel()
        if animate:
            if float(label.getAlpha()) >= float(old.getAlpha()):
                old.setText(previous_text)
                _measure_and_layout(
                    old, label.getLeft(), label.getTop(), label.getRight(), label.getBottom(), True
                )
                old.setAlpha(float(label.getAlpha()))
            old.animate().alpha(0.0).setDuration(140).start()
            label.setAlpha(0.0)
        else:
            old.setAlpha(0.0)
            label.setAlpha(1.0 if ready else 0.0)
        label.setText(text)

    _measure_and_layout(label, left, top, right, bottom, text_changed)
    if animate:
        label.animate().alpha(1.0).setDuration(140).start()

    entry["text"] = text
    entry["bounds"] = (left, top, right, bottom)


def _layout_date(cell):
    entry = _date_entry(cell)
    if entry is None:
        return
    if not _enabled["date"] or not _is_date(cell):
        _unpatch_date(cell)
        return

    width = int(cell.getWidth())
    if width <= 0:
        return
    text = str(_api.get_field(cell, "customText") or "")
    if not text:
        _unpatch_date(cell)
        return
    text_width = int(_api.get_field(cell, "textWidth") or _api.dp(64))
    text_height = int(_api.get_field(cell, "textHeight") or _api.dp(17))
    chip_width = max(1, min(max(_api.dp(48), text_width + _api.dp(24)), width - _api.dp(24)))
    chip_height = max(_api.dp(25), text_height + _api.dp(8))
    left = (width - chip_width) // 2
    top = _api.dp(4)
    _animate_date(entry, left, top, left + chip_width, top + chip_height, text)
    _update_surface(entry, "date")
    if entry.get("surface") is None:
        _request_surface(entry, "date")


def _date_label(context):
    label = _class("android.widget.TextView")(context)
    label.setClickable(False)
    label.setFocusable(False)
    label.setImportantForAccessibility(2)
    label.setSingleLine(True)
    label.setIncludeFontPadding(False)
    label.setGravity(17)
    label.setTextSize(13.0)
    label.setTextColor(_theme_color("key_chat_serviceText", -1))
    label.setTypeface(_class("org.telegram.messenger.AndroidUtilities").bold())
    label.setAlpha(0.0)
    return label


def _patch_date(cell):
    if not _enabled["date"] or not _is_date(cell):
        return
    key = _api.identity(cell)
    if key not in _patched_dates:
        context = cell.getContext()
        overlay = _class("android.view.View")(context)
        overlay.setClickable(False)
        overlay.setFocusable(False)
        overlay.setImportantForAccessibility(2)
        overlay.setAlpha(0.0)
        old = _date_label(context)
        label = _date_label(context)
        _patched_dates[key] = {"cell": cell, "overlay": overlay, "label": label, "previous_label": old}
        try:
            cell.addView(overlay, 0)
            cell.addView(old)
            cell.addView(label)
        except Exception:
            _unpatch_date(cell)
            raise
    _layout_date(cell)


def _unpatch_date(cell):
    if cell is None:
        return
    entry = _patched_dates.pop(_api.identity(cell), None)
    if entry is None:
        return
    for view in (entry["overlay"], entry["previous_label"], entry["label"]):
        try:
            view.animate().cancel()
            cell.removeView(view)
        except Exception:
            pass
    cell.invalidate()


def _patch_unread(cell, force=False):
    if not _enabled["unread"] or cell is None:
        return
    key = _api.identity(cell)
    entry = _patched_unread.get(key)
    if entry is not None and not force:
        _update_surface(entry, "unread")
        if entry.get("surface") is None:
            _request_surface(entry, "unread")
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

        _update_surface(entry, "unread")
        if entry.get("surface") is None:
            _request_surface(entry, "unread")
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
            if not _enabled["date"]:
                return
            cell = param.thisObject
            entry = _date_entry(cell)
            if entry is not None and not _is_date(cell):
                _unpatch_date(cell)
                return
            if (
                entry is not None
                and entry.get("surface") is not None
                and entry.get("text") == str(_api.get_field(cell, "customText") or "")
            ):
                _update_surface(entry, "date")
            else:
                _patch_date(cell)
        except Exception as exc:
            _api.log("setCustomDate hook failed: " + str(exc))


class _DateLayoutHook(MethodHook):
    def after_hooked_method(self, param):
        try:
            cell = param.thisObject
            if _date_entry(cell) is not None:
                _layout_date(cell)
            elif _enabled["date"] and _is_date(cell):
                _patch_date(cell)
        except Exception:
            pass


class _DateDrawHook(MethodHook):
    def before_hooked_method(self, param):
        if not _enabled["date"]:
            return
        entry = _date_entry(param.thisObject)
        if entry is not None and entry.get("surface") is not None:
            param.setResult(None)


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


class _ChatDestroyHook(MethodHook):
    def before_hooked_method(self, param):
        if _api is None:
            return
        fragment_id = _api.identity(param.thisObject)
        for entries, restore in (
            (_patched_dates, _unpatch_date), (_patched_unread, _unpatch_unread)
        ):
            for entry in list(entries.values()):
                if entry.get("fragment_id") == fragment_id:
                    restore(entry["cell"])


def _settings_changed(key, value):
    if key not in _enabled:
        return
    _enabled[key] = value == "on"
    if not _enabled[key]:
        entries, restore = (
            (_patched_dates, _unpatch_date) if key == "date" else (_patched_unread, _unpatch_unread)
        )
        for entry in list(entries.values()):
            restore(entry["cell"])


def on_load(api):
    global _api
    _api = api
    for key in _enabled:
        _enabled[key] = api.get_setting(key, "on") == "on"
    api.register_settings(_SETTINGS, _settings_changed)

    ChatActionCell = _hook_class("org.telegram.ui.Cells.ChatActionCell")
    ChatUnreadCell = _hook_class("org.telegram.ui.Cells.ChatUnreadCell")
    ChatActivity = _hook_class("org.telegram.ui.ChatActivity")

    api.hook_all_methods(ChatActionCell, "setCustomDate", _DateSetHook())
    api.hook_all_methods(ChatActionCell, "onLayout", _DateLayoutHook())
    api.hook_all_methods(ChatActionCell, "setMessageObject", _DateMessageHook())
    api.hook_all_methods(ChatActionCell, "onDraw", _DateDrawHook())
    api.hook_all_methods(ChatActionCell, "drawBackground", _DateDrawHook())

    api.hook_all_constructors(ChatUnreadCell, _UnreadCtorHook())
    api.hook_all_methods(ChatUnreadCell, "setText", _UnreadTextHook())
    api.hook_all_methods(ChatUnreadCell, "onMeasure", _UnreadTextHook())
    api.hook_all_methods(ChatActivity, "onFragmentDestroy", _ChatDestroyHook())

    api.log("Glass Date Chips " + GLASSIFY_EXTENSION["version"] + " loaded")


def on_unload(api):
    global _api
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
    _wallpaper_cache.clear()
    _api = None
    api.log("Glass Date Chips unloaded")
