GLASSIFY_EXTENSION = {
    "id": "ios_header",
    "name": "iOS Header",
    "version": "1.5",
    "api": 5,
    "detail_layout": "sections",
    "description": "iOS-компоновка заголовка: капсула 44 dp, адаптивная ширина, статическое сокращение имени, сохранение значков, профиль и счётчик.",
    "min_glassify": "0.6.0",
    "min_exteragram": "13.1.1",
}

_API = None
_RUNTIME = None
AndroidUtilities = None
View = None
ViewGroup = None
Gravity = None
Theme = None
TextLayout = None
_IOS7_TITLE_FONT = None
_B8_CLASSES = {}
_B8_INTERPOLATORS = {}

_SETTINGS = [
    {
        "type": "choice",
        "key": "header_morph",
        "text": "Glass Header Morph",
        "icon": "msg_settings",
        "default": "on",
        "options": [
            {"value": "on", "text": "Включён", "subtext": "Капсула меняет форму при входе в чат и возврате."},
            {"value": "off", "text": "Выключен"},
        ],
    },
]


def _field(obj: Any, name: str):
    if _API is None:
        return None
    return _API.get_field(obj, name)


def _class(name: str):
    if _API is None:
        return None
    clazz = _B8_CLASSES.get(name)
    if clazz is None:
        clazz = _API.find_class(name)
        if clazz is not None:
            _B8_CLASSES[name] = clazz
    return clazz


def _b8_curve(kind, *args):
    key = (kind, args)
    value = _B8_INTERPOLATORS.get(key)
    if value is None:
        clazz = _class("android.view.animation." + kind)
        value = clazz(*args)
        _B8_INTERPOLATORS[key] = value
    return value


def _identity(obj: Any) -> int:
    if _API is None:
        return 0
    return _API.identity(obj)


def _note_suppressed(exc: Any):
    runtime = _RUNTIME
    if runtime is not None:
        runtime.log_suppressed("compatibility fallback", exc)


def _ios_header_int(value: Any, fallback: int = 0) -> int:
    try:
        return fallback if value is None else int(value)
    except Exception:
        return fallback


def _ios_header_topic_id(fragment: Any) -> int:
    if fragment is None:
        return 0
    for name in (
        "getTopicId",
        "getCurrentTopicId",
        "getThreadId",
        "topicId",
        "currentTopicId",
        "threadId",
    ):
        try:
            member = getattr(fragment, name)
            value = member() if callable(member) else member
            result = _ios_header_int(value)
            if result:
                return result
        except Exception as _suppressed_exc:
            _note_suppressed(_suppressed_exc)
    return 0


def _ios_header_fragment_state(fragment: Any) -> Tuple[bool, bool]:
    """Return (supported, saved_messages) for a real chat header."""
    if fragment is None:
        return False, False

    try:
        simple_name = str(fragment.getClass().getSimpleName())
        if "Feed" in simple_name or "Folder" in simple_name:
            return False, False
    except Exception as _suppressed_exc:
        _note_suppressed(_suppressed_exc)

    try:
        dialog_id = _ios_header_int(fragment.getDialogId())
    except Exception:
        dialog_id = 0
    if dialog_id == 0:
        return False, False

    self_id = 0
    try:
        UserConfig = _class("org.telegram.messenger.UserConfig")
        if UserConfig is not None:
            account = _ios_header_int(fragment.getCurrentAccount())
            self_id = _ios_header_int(
                UserConfig.getInstance(account).getClientUserId()
            )
    except Exception as _suppressed_exc:
        _note_suppressed(_suppressed_exc)

    saved = dialog_id == self_id and self_id != 0
    try:
        saved = saved or _ios_header_int(fragment.getChatMode()) == 4
    except Exception as _suppressed_exc:
        _note_suppressed(_suppressed_exc)

    chat = None
    for getter in ("getCurrentChat", "getChat"):
        try:
            chat = getattr(fragment, getter)()
            if chat is not None:
                break
        except Exception as _suppressed_exc:
            _note_suppressed(_suppressed_exc)

    forum = False
    if chat is not None:
        try:
            forum = bool(_field(chat, "forum"))
        except Exception as _suppressed_exc:
            _note_suppressed(_suppressed_exc)
        if not forum:
            try:
                forum = bool(chat.isForum())
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)

    # The root of Saved Messages / a forum uses a different stock header model.
    # Apply the centered variant only inside an actual topic there.
    if (saved or forum) and _ios_header_topic_id(fragment) == 0:
        return False, saved

    return True, saved


def _ios_header_subtitle_is_activity(
    view: Any,
    fragment: Any = None,
) -> bool:
    """Detect Telegram's transient chat activity without relying on locale.

    Drawable and fragment state are preferred. Text markers remain only as a
    compatibility fallback for older client builds that expose neither.
    """
    if view is None:
        return False

    for field_name in (
        "typingDrawable",
        "statusDrawable",
        "leftDrawable",
        "replaceDrawable",
    ):
        try:
            if _field(view, field_name) is not None:
                return True
        except Exception as _suppressed_exc:
            _note_suppressed(_suppressed_exc)

    for getter_name in ("getLeftDrawable", "getStatusDrawable"):
        try:
            if getattr(view, getter_name)() is not None:
                return True
        except Exception as _suppressed_exc:
            _note_suppressed(_suppressed_exc)

    if fragment is not None:
        activity_text_present = False
        for field_name in (
            "printingString",
            "lastPrintingString",
            "typingString",
        ):
            try:
                value = _field(fragment, field_name)
                if value is not None and str(value):
                    activity_text_present = True
                    break
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)
        for field_name in (
            "printingStringType",
            "lastPrintingStringType",
            "typingAnimationType",
        ):
            try:
                value = _field(fragment, field_name)
                if activity_text_present and value is not None and int(value) >= 0:
                    return True
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)

    try:
        value = view.getText()
    except Exception:
        value = None
    if value is None:
        return False
    text = str(value).lower()
    markers = (
        "typing",
        "recording",
        "sending",
        "choosing",
        "playing",
        "печат",
        "записыв",
        "отправл",
        "выбира",
        "игра",
        "schreibt",
        "nimmt auf",
        "sendet",
        "tippt",
    )
    return any(marker in text for marker in markers)


def _ios_header_text_extent(view: Any) -> int:
    """Use the full CharSequence, including spans, before it is clipped."""
    if view is None:
        return 0
    try:
        if TextLayout is not None:
            width = float(TextLayout.getDesiredWidth(view.getText(), view.getPaint()))
            width += int(view.getSideDrawablesSize())
            width += max(0, _ios_header_int(_field(view, "minusWidth")))
            width += max(0, _ios_header_int(_field(view, "paddingRight")))
            return max(0, int(width) + int(width > int(width)))
    except Exception:
        pass
    try:
        width = float(view.getExactWidth())
        return max(0, int(width) + int(width > int(width)))
    except Exception:
        return 0


def _ios_header_pill_bounds(center, left, right, desired_width, minimum_width):
    """Keep an equal span either side of the screen's toolbar center."""
    span = max(0, right - left)
    if span <= 1:
        return left, span
    half_minimum = min(minimum_width, span) // 2
    center = max(left + half_minimum, min(center, right - half_minimum))
    width = min(desired_width, 2 * min(center - left, right - center))
    return center - width // 2, width


def _ios_header_set_text_overflow(view, scrolling, fade, fade_width=16, fade_left=None):
    scroll = getattr(view, "setScrollNonFitText", None)
    gradient = getattr(view, "setEllipsizeByGradient", None)
    old_scroll = _field(view, "scrollNonFitText")
    old_fade = _field(view, "ellipsizeByGradient")
    old_width = _field(view, "ellipsizeByGradientWidthDp") if fade else None
    old_left = _field(view, "forceEllipsizeByGradientLeft") if fade else None
    fade_changed = old_fade is None or bool(old_fade) != fade
    width_changed = fade and old_width is not None and int(old_width) != fade_width
    left_changed = fade and old_left != fade_left
    try:
        if fade_changed or width_changed or left_changed:
            if gradient is not None:
                # Some SimpleTextView builds compare the gradient argument to
                # the scroll flag. Set that flag first so both modes can switch.
                if scroll is not None:
                    scroll(not fade)
                if fade:
                    try:
                        gradient(int(fade_width), fade_left)
                    except TypeError:
                        gradient(True)
                else:
                    gradient(False)
            elif hasattr(view, "setFadeWidth"):
                view.setFadeWidth(AndroidUtilities.dp(fade_width) if fade or scrolling else 0)
    except Exception as exc:
        _note_suppressed(exc)

    try:
        if scroll is not None:
            scroll(bool(scrolling))
        elif hasattr(view, "setScrolling"):
            view.setScrolling(bool(scrolling))
        if not scrolling and (old_scroll or float(_field(view, "scrollingOffset") or 0)):
            if hasattr(view, "resetScrolling"):
                view.resetScrolling()
            elif _API is not None:
                _API.set_field(view, "scrollingOffset", 0.0)
            view.invalidate()
        if fade_changed or width_changed or left_changed or old_scroll != scrolling:
            view.forceLayout()
    except Exception as exc:
        _note_suppressed(exc)


# Telegram-iOS ChatTitleComponent.swift, commit 24638bc69bd083981b178dd1e7f921eebbf7fc46:
# 14pt side inset, 150pt minimum content, 44pt height, 17pt title,
# 12pt subtitle, reserve all icon widths before truncating the name.
# This is an Android port of the layout, not a UIKit implementation.
def _ios7_pill_geometry(center, left, right, title_width, subtitle_width, inset, minimum_content, allow_shift=True, min_readable_width=None):
    room = max(0, right - left)
    if not allow_shift:
        # With the unread counter disabled, preserve the toolbar centre.
        # The avatar/back/timer still define safe edges. Fit long labels by
        # reducing the pill width symmetrically instead of shifting the pill.
        centered_room = 2 * min(center - left, right - center)
        # Keep a readable minimum when exact centering is impossible.
        # Only then allow the smallest necessary displacement.
        readable = min(room, max(2, min_readable_width if min_readable_width is not None else inset * 6))
        room = min(room, max(readable, centered_room))
    width = min(room, max(minimum_content + 2 * inset,
                          max(title_width, subtitle_width) + 2 * inset))
    x = max(left, min(center - width // 2, right - width))
    return x, width


def _ios7_try(view, method, *args):
    try:
        fn = getattr(view, method, None)
        if fn is not None:
            fn(*args)
            return True
    except Exception as exc:
        _note_suppressed(exc)
    return False


def _ios7_static(view, is_title, dp):
    # SimpleTextView's native truncation uses TextUtils.TruncateAt.END when
    # both gradient and marquee are off. The boolean gradient setter on
    # some builds compares against scrollNonFitText rather than its own flag.
    old_gradient = _field(view, "ellipsizeByGradient")
    if bool(old_gradient) or (old_gradient is None and hasattr(view, "setScrollNonFitText")):
        _ios7_try(view, "setScrollNonFitText", True)
        _ios7_try(view, "setEllipsizeByGradient", False)
    _ios7_try(view, "setScrollNonFitText", False)
    if bool(_field(view, "ellipsizeByGradient")) and _API is not None:
        _API.set_field(view, "ellipsizeByGradient", False)
    if bool(_field(view, "scrolling")):
        _ios7_try(view, "setScrolling", False)
    offset = _field(view, "scrollingOffset")
    if offset is not None and float(offset) != 0.0:
        if not _ios7_try(view, "resetScrolling") and _API is not None:
            _API.set_field(view, "scrollingOffset", 0.0)
    # For AnimatedTextView, disable its gradient and request an end ellipsis
    # where supported. Never change the actual text or remove native spans.
    if old_gradient is None:
        _ios7_try(view, "setEllipsizeByGradient", False)
        truncate = _class("android.text.TextUtils$TruncateAt")
        if truncate is not None:
            _ios7_try(view, "setEllipsize", truncate.END)
    paint = None
    try:
        paint = view.getPaint()
    except Exception:
        pass
    size = dp(17 if is_title else 12)
    if paint is None or abs(float(paint.getTextSize()) - size) > 0.5:
        if not _ios7_try(view, "setTextSizePx", size):
            # AnimatedTextView takes pixels; SimpleTextView has setTextSizePx.
            _ios7_try(view, "setTextSize", float(size))
    if is_title:
        global _IOS7_TITLE_FONT
        if _IOS7_TITLE_FONT is None:
            try:
                Typeface = _class("android.graphics.Typeface")
                _IOS7_TITLE_FONT = Typeface.create(Typeface.DEFAULT, 600, False)
            except Exception:
                try:
                    _IOS7_TITLE_FONT = AndroidUtilities.bold()
                except Exception:
                    pass
        if paint is not None and _IOS7_TITLE_FONT is not None:
            try:
                current = paint.getTypeface()
                if current is None or not current.equals(_IOS7_TITLE_FONT):
                    _ios7_try(view, "setTypeface", _IOS7_TITLE_FONT)
            except Exception:
                pass
        # Native Android glyphs are retained (including dynamic emoji and
        # credibility labels). In outside mode the platform reserves both
        # right drawable widths in onMeasure, then draws after the ellipsis.
        for field_name, method, value in (
            ("canHideRightDrawable", "setCanHideRightDrawable", False),
            ("rightDrawableInside", "setRightDrawableInside", False),
            ("rightDrawableOutside", "setRightDrawableOutside", True),
            ("leftDrawableOutside", "setLeftDrawableOutside", False),
            ("drawablePadding", "setDrawablePadding", dp(4)),
        ):
            if _field(view, field_name) != value:
                _ios7_try(view, method, value)
    # Native horizontal padding and SimpleTextView's independent clip padding
    # must not be counted a second time after the iOS 14pt insets.
    if _field(view, "paddingRight") != 0:
        _ios7_try(view, "setRightPadding", 0)
    if any(_ios_header_int(getattr(view, getter)()) for getter in
           ("getPaddingLeft", "getPaddingTop", "getPaddingRight", "getPaddingBottom")):
        view.setPadding(0, 0, 0, 0)
    gravity = Gravity.LEFT | Gravity.CENTER_VERTICAL
    try:
        current_gravity = view.getGravity()
    except Exception:
        current_gravity = None
    if current_gravity != gravity:
        view.setGravity(gravity)
    # forceLayout is important: a changed status drawable or a new name may
    # leave the exact same width as the preceding layout pass.
    view.forceLayout()


def _ios7_drawable_reserve(view):
    try:
        native = max(0, int(view.getSideDrawablesSize()))
    except Exception:
        native = 0
    # Outside mode reserves intrinsic (unscaled) sizes on Android. Prefer the
    # larger of those and the actual native width so labels never overlap.
    reserve = 0
    gap = max(0, _ios_header_int(_field(view, "drawablePadding")))
    for name in ("getLeftDrawable", "getRightDrawable", "getRightDrawable2"):
        try:
            drawable = getattr(view, name)()
            if drawable is not None:
                reserve += max(0, int(drawable.getIntrinsicWidth())) + gap
        except Exception:
            pass
    return max(native, reserve)


def _ios7_extent(view):
    if view is None or view.getVisibility() != View.VISIBLE:
        return 0
    try:
        width = float(TextLayout.getDesiredWidth(view.getText(), view.getPaint()))
        return max(0, int(width) + int(width > int(width))) + _ios7_drawable_reserve(view) + max(0, _ios_header_int(_field(view, "minusWidth")))
    except Exception:
        return _ios_header_text_extent(view)


def _ios7_measure_row(view, width, height, spec, natural=None):
    if view is None or view.getVisibility() != View.VISIBLE or width <= 0:
        return None
    if natural is None:
        natural = _ios7_extent(view)
    # AnimatedTextView does not necessarily expose the same measurement
    # methods as SimpleTextView. If unknown, use the full available row.
    target = min(width, natural) if natural > 0 else width
    target = max(1, target)
    view.measure(spec.makeMeasureSpec(target, spec.EXACTLY),
                 spec.makeMeasureSpec(height, spec.AT_MOST))
    actual = min(target, max(1, int(view.getMeasuredWidth())))
    return (actual, min(height, max(1, int(view.getMeasuredHeight()))))


class _IOSHeaderCreatedHook(MethodHook):
    def __init__(self, plugin: "GlassifyPlugin"):
        self.plugin = plugin

    def after_hooked_method(self, param):
        if not self.plugin.ios_header_enabled():
            return
        container = param.thisObject
        try:
            fragment = _field(container, "parentFragment")
            title = _field(container, "titleTextView")
            subtitle = _field(container, "subtitleTextView")
            avatar = _field(container, "avatarImageView")
            self.plugin.remember_ios_header_state(
                container,
                fragment,
                title,
                subtitle,
                avatar,
            )
        except Exception as exc:
            self.plugin.log_once_header_error(exc)


class _IOSHeaderRefreshHook(MethodHook):
    def __init__(self, plugin: "GlassifyPlugin"):
        self.plugin = plugin

    def after_hooked_method(self, param):
        if not self.plugin.ios_header_enabled():
            return
        view = param.thisObject
        try:
            if not view.isLayoutRequested():
                view.requestLayout()
            view.invalidate()
        except Exception as _suppressed_exc:
            _note_suppressed(_suppressed_exc)


class _IOSHeaderLayoutHook(MethodHook):
    def __init__(self, plugin: "GlassifyPlugin"):
        self.plugin = plugin

    def after_hooked_method(self, param):
        if not self.plugin.ios_header_enabled():
            return

        try:
            container = param.thisObject
            fragment = _field(container, "parentFragment")
            supported, saved = _ios_header_fragment_state(fragment)
            if not supported:
                self.plugin.avatar_guard.destroy(fragment)
                return

            ActionBar = _class("org.telegram.ui.ActionBar.ActionBar")
            MeasureSpec = _class("android.view.View$MeasureSpec")
            if ActionBar is None or MeasureSpec is None:
                return

            avatar = _field(container, "avatarImageView")
            title = _field(container, "titleTextView")
            subtitle = _field(container, "subtitleTextView")
            time_item = _field(container, "timeItem")
            community_item = _field(container, "communityItem")
            self.plugin.remember_ios_header_state(
                container,
                fragment,
                title,
                subtitle,
                avatar,
            )

            width = _ios_header_int(container.getWidth())
            height = _ios_header_int(container.getHeight())
            if width <= 0 or height <= 0:
                return

            left_on_screen = _ios_header_int(container.getLeft())
            parent_width = 0
            try:
                parent = container.getParent()
                if parent is not None:
                    parent_width = _ios_header_int(parent.getWidth())
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)
            right_edge = parent_width if parent_width > 0 else width + left_on_screen

            bar_height = _ios_header_int(ActionBar.getCurrentActionBarHeight())
            status_height = _ios_header_int(AndroidUtilities.statusBarHeight)
            add_status = False
            try:
                occupy = _field(container, "occupyStatusBar")
                add_status = bool(occupy) and _ios_header_int(container.getTop()) == 0
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)
            top_offset = status_height if add_status else 0

            pill_height = self.plugin.dp(44)
            pill_top = max(0, (bar_height - pill_height) // 2) + top_offset

            avatar_left = width - self.plugin.dp(48)
            if avatar is not None and avatar.getVisibility() != View.GONE:
                avatar_w = _ios_header_int(avatar.getMeasuredWidth(), self.plugin.dp(42))
                avatar_h = _ios_header_int(avatar.getMeasuredHeight(), self.plugin.dp(42))
                if avatar_w <= 0:
                    avatar_w = self.plugin.dp(42)
                if avatar_h <= 0:
                    avatar_h = self.plugin.dp(42)

                avatar_right = right_edge - left_on_screen - self.plugin.dp(6)
                avatar_left = avatar_right - avatar_w
                avatar_top = (bar_height - avatar_h) // 2 + top_offset

                show_avatar = not saved
                avatar.setVisibility(View.VISIBLE if show_avatar else View.INVISIBLE)
                avatar.layout(
                    int(avatar_left),
                    int(avatar_top),
                    int(avatar_right),
                    int(avatar_top + avatar_h),
                )
                try:
                    avatar.setTranslationX(float(-self.plugin.dp(3)))
                    avatar.setTranslationY(0.0)
                    avatar.setScaleX(1.08)
                    avatar.setScaleY(1.08)
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)

            # The ActionBar may relayout or animate its menu after this
            # container. The overlap guard also runs immediately before draw.
            self.plugin.avatar_guard.bind(fragment, container, avatar)

            if saved:
                try:
                    search_item = _field(fragment, "searchItem")
                    if search_item is not None:
                        search_item.setAlpha(0.0)
                        search_item.setVisibility(View.GONE)
                        search_item.setEnabled(False)
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)

            left_bound = self.plugin.dp(16)
            badge_enabled = _BETA is not None and _BETA.active and _BETA.badge
            if badge_enabled:
                try:
                    left_bound = max(left_bound, _BETA.left_bound(fragment, container))
                except Exception as exc:
                    _BETA.log("badge layout inset", exc)
            avatar_visible = (
                avatar is not None and avatar.getVisibility() == View.VISIBLE
            )
            if avatar_visible:
                right_bound = avatar_left - self.plugin.dp(14)
            else:
                right_bound = width - self.plugin.dp(16)
            if right_bound <= left_bound:
                left_bound = self.plugin.dp(12)
                right_bound = width - self.plugin.dp(12)

            available = max(0, right_bound - left_bound)
            if available <= 0:
                return

            # Match the iOS title component: measure with the final typography
            # before choosing the pill width. Status glyphs are included.
            for row, is_title in ((title, True), (subtitle, False)):
                if row is not None and row.getVisibility() == View.VISIBLE:
                    try:
                        _ios7_static(row, is_title, self.plugin.dp)
                    except Exception as exc:
                        self.plugin.log_suppressed("prepare iOS title row", exc)
            title_width = _ios7_extent(title)
            subtitle_width = _ios7_extent(subtitle)
            horizontal_inset = self.plugin.dp(14)

            # Telegram's auto-delete timer is a separate ImageView. Keep it
            # outside the glass and treat the timer + pill as one anchored
            # header group. The pill is sized first; the timer then follows its
            # real upper-left edge instead of using screen-relative coordinates.
            # Telegram can keep timeItem GONE during onLayout and reveal it
            # afterwards from BoolAnimator. Visibility alone misses that case,
            # so use the animator target state first.
            time_item_active = False
            time_item_width = 0
            time_item_height = 0
            time_item_gap = self.plugin.dp(2)
            timer_overlap_x = self.plugin.dp(5)
            if time_item is not None:
                try:
                    time_animator = _field(container, "animatorTimeVisible")
                    if time_animator is not None:
                        time_item_active = bool(time_animator.getValue())
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)
                if not time_item_active:
                    try:
                        time_item_active = (
                            time_item.getVisibility() == View.VISIBLE
                            and float(time_item.getAlpha()) > 0.01
                        )
                    except Exception as _suppressed_exc:
                        _note_suppressed(_suppressed_exc)

                # Always capture the native timer size even while it is hidden.
                time_item_width = _ios_header_int(
                    time_item.getMeasuredWidth(),
                    self.plugin.dp(34),
                )
                time_item_height = _ios_header_int(
                    time_item.getMeasuredHeight(),
                    self.plugin.dp(34),
                )
                if time_item_width <= 0:
                    time_item_width = self.plugin.dp(34)
                if time_item_height <= 0:
                    time_item_height = self.plugin.dp(34)

            community_item_active = False
            community_item_width = 0
            community_item_height = 0
            if community_item is not None:
                try:
                    community_item_active = (
                        community_item.getVisibility() == View.VISIBLE
                    )
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)

                community_item_width = _ios_header_int(
                    community_item.getMeasuredWidth(),
                    self.plugin.dp(14),
                )
                community_item_height = _ios_header_int(
                    community_item.getMeasuredHeight(),
                    self.plugin.dp(14),
                )
                if community_item_width <= 0:
                    community_item_width = self.plugin.dp(14)
                if community_item_height <= 0:
                    community_item_height = self.plugin.dp(14)

            min_island = min(available, self.plugin.dp(82))
            if time_item_active:
                needed_left = time_item_width - timer_overlap_x + time_item_gap
                left_bound += max(0, min(needed_left, available - min_island))
            toolbar_center = (
                parent_width // 2 - left_on_screen if parent_width > 0 else width // 2
            )
            island_left, island_width = _ios7_pill_geometry(
                toolbar_center, left_bound, right_bound, title_width, subtitle_width,
                horizontal_inset, self.plugin.dp(150), allow_shift=badge_enabled,
                min_readable_width=self.plugin.dp(82)
            )
            if island_width <= 1:
                return
            island_right = island_left + island_width

            glass = self.plugin.ensure_ios_header_glass(
                container,
                fragment,
                title,
                subtitle,
            )
            self.plugin.layout_ios_header_glass(
                glass,
                island_left,
                pill_top,
                island_width,
                pill_height,
                MeasureSpec,
            )

            self.plugin.header_morph.bind(fragment, glass)

            inset = min(horizontal_inset, max(0, (island_width - self.plugin.dp(24)) // 2))
            text_left = island_left + inset
            text_right = island_right - inset
            pill_bottom = pill_top + pill_height

            if time_item_active:
                # Final tuned timer position.
                timer_right = island_left + timer_overlap_x + self.plugin.dp(18)
                timer_left = timer_right - time_item_width
                timer_top = pill_top - self.plugin.dp(6)
                timer_bottom = timer_top + time_item_height
                try:
                    time_item.layout(
                        int(timer_left),
                        int(timer_top),
                        int(timer_right),
                        int(timer_bottom),
                    )
                    time_item.invalidate()
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)

            if community_item_active:
                # Mirror the tuned upper-left badge on the lower-left corner.
                # The 14dp arrow keeps the same horizontal visual centre as the
                # timer and protrudes 6dp below the pill, so it remains attached
                # while the pill changes width or shifts horizontally.
                badge_center_x = island_left + self.plugin.dp(6)
                community_left = badge_center_x - community_item_width // 2
                community_right = community_left + community_item_width
                community_bottom = pill_bottom + self.plugin.dp(4)
                community_top = community_bottom - community_item_height
                try:
                    community_item.layout(
                        int(community_left),
                        int(community_top),
                        int(community_right),
                        int(community_bottom),
                    )
                    community_item.invalidate()
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)

            text_width = text_right - text_left

            # iOS vertically centers the combined title and subtitle, with
            # no extra gap. Measure both rows first, then center each row.
            rows = []
            for row, natural in ((title, title_width), (subtitle, subtitle_width)):
                if row is None or row.getVisibility() != View.VISIBLE:
                    continue
                if float(row.getTranslationX()) != 0.0:
                    row.setTranslationX(0.0)
                if float(row.getTranslationY()) != 0.0:
                    row.setTranslationY(0.0)
                size = _ios7_measure_row(row, text_width, pill_height, MeasureSpec, natural)
                if size is not None:
                    rows.append((row, size[0], size[1]))
            combined_height = sum(size[2] for size in rows)
            y = pill_top + max(0, (pill_height - combined_height) // 2)
            for row, row_width, row_height in rows:
                x = island_left + (island_width - row_width) // 2
                row.layout(int(x), int(y), int(x + row_width), int(y + row_height))
                y += row_height
        except Exception as exc:
            self.plugin.log_once_header_error(exc)


class _IOSHeaderChatViewHook(MethodHook):
    def __init__(self, plugin: "GlassifyPlugin"):
        self.plugin = plugin

    def after_hooked_method(self, param):
        if not self.plugin.ios_header_enabled():
            return
        fragment = param.thisObject
        supported, _ = _ios_header_fragment_state(fragment)
        if not supported:
            return
        try:
            container = _field(fragment, "avatarContainer")
            title = (
                _field(container, "titleTextView")
                if container is not None
                else None
            )
            subtitle = (
                _field(container, "subtitleTextView")
                if container is not None
                else None
            )
            avatar = (
                _field(container, "avatarImageView")
                if container is not None
                else None
            )
            self.plugin.remember_ios_header_state(
                container,
                fragment,
                title,
                subtitle,
                avatar,
            )
            params = container.getLayoutParams() if container is not None else None
            if params is not None and hasattr(params, "rightMargin"):
                params.rightMargin = 0
                container.setLayoutParams(params)
        except Exception as exc:
            self.plugin.log_once_header_error(exc)


class _HeaderMorph:
    """Move and resize the existing glass view during chat navigation."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.transition = None

    def _screen_origin(self, view):
        rect = _class("android.graphics.Rect")()
        origin = _class("android.graphics.Point")()
        if view.getGlobalVisibleRect(rect, origin):
            return float(origin.x), float(origin.y)
        return None

    def _source_frame(self, fragment):
        layout = fragment.getParentLayout()
        if layout is None:
            return None
        stack = layout.getFragmentStack()
        size = int(stack.size())
        if size < 2 or _identity(stack.get(size - 1)) != _identity(fragment):
            return None
        source = stack.get(size - 2)
        if source is None:
            return None
        if hasattr(source, "getCurrentVisibleFragment"):
            source = source.getCurrentVisibleFragment()
        if source is None:
            return None
        source_name = str(source.getClass().getSimpleName())
        if not source_name or source_name.endswith("TabsActivity"):
            return None
        if source_name != "DialogsActivity":
            return False
        bar = _field(source, "actionBar")
        if bar is None:
            return None
        origin = self._screen_origin(bar)
        width, height = int(bar.getWidth()), int(bar.getHeight())
        if origin is None or width <= 0 or height <= 0:
            return None

        dp = self.runtime.dp
        bar_height = min(height, int(_class("org.telegram.ui.ActionBar.ActionBar").getCurrentActionBarHeight()))
        if bar_height <= 0:
            return None
        center_x = origin[0] + width * 0.5
        center_y = origin[1] + height - bar_height * 0.5
        anchor_width = min(width * 0.42, dp(144))
        title = _field(bar, "titleTextView")
        if title is not None and int(title.getVisibility()) == View.VISIBLE:
            anchor = self._screen_origin(title)
            text_width = _ios_header_text_extent(title)
            if anchor is not None and text_width > 0 and int(title.getHeight()) > 0:
                actual_width = min(float(title.getWidth()), float(text_width))
                center_x = anchor[0] + actual_width * 0.5
                center_y = anchor[1] + int(title.getHeight()) * 0.5
                anchor_width = min(width * 0.62, max(dp(72), actual_width + dp(26)))
        return center_x, center_y, anchor_width, min(dp(42), bar_height)

    def begin(self, fragment, opening, backward):
        if not self.runtime.ios_header_enabled() or not self.runtime.morph_enabled or opening == backward:
            return
        self.finish()
        try:
            if hasattr(fragment, "isInPreviewMode") and fragment.isInPreviewMode():
                return
            animator = _class("android.animation.ValueAnimator")
            if animator is not None and hasattr(animator, "areAnimatorsEnabled"):
                if not animator.areAnimatorsEnabled():
                    return
            try:
                frame = self._source_frame(fragment)
            except Exception as exc:
                self.runtime.log_suppressed("locate chat-list header", exc)
                frame = None
            if frame is False:
                return
            transition = {
                "fragment_id": _identity(fragment),
                "opening": opening,
                "frame": frame,
            }
            self.transition = transition
            container = _field(fragment, "avatarContainer")
            if container is not None:
                state = self.runtime._ios_header_runtime.get(_identity(container)) or {}
                self.bind(fragment, state.get("glass"))

            def expire():
                if self.transition is transition:
                    self.finish()

            self.runtime.schedule(expire, 750)
        except Exception as exc:
            self.finish()
            self.runtime.log_suppressed("start Glass Header Morph", exc)

    def bind(self, fragment, glass):
        transition = self.transition
        if transition is None or glass is None or transition.get("view") is not None:
            return
        if transition["fragment_id"] != _identity(fragment):
            return
        try:
            width, height = float(glass.getWidth()), float(glass.getHeight())
            if width <= 0 or height <= 0 or glass.getParent() is None:
                return
            dp = self.runtime.dp
            dx, dy, sx, sy = -dp(14), 0, 0.64, 0.80
            frame = transition["frame"]
            origin = self._screen_origin(glass) if frame is not None else None
            if origin is not None:
                center_x, center_y, anchor_width, anchor_height = frame
                dx = max(-dp(20), min(dp(20), center_x - origin[0] - width * 0.5))
                dy = max(-dp(6), min(dp(6), center_y - origin[1] - height * 0.5))
                sx = max(0.52, min(0.72, anchor_width / width))
                sy = max(0.70, min(0.84, anchor_height / height))

            base = (
                float(glass.getTranslationX()), float(glass.getTranslationY()),
                float(glass.getScaleX()), float(glass.getScaleY()), float(glass.getAlpha()),
            )
            transition["view"] = glass
            transition["base"] = base
            x, y, scale_x, scale_y, alpha = base
            anchor = (x + dx, y + dy, scale_x * sx, scale_y * sy, alpha * 0.58)
            opening = transition["opening"]
            if opening:
                self._set_transform(glass, anchor)
            target = base if opening else anchor
            animation = glass.animate()
            animation.translationX(target[0]).translationY(target[1])
            animation.scaleX(target[2]).scaleY(target[3])
            animation.alpha(target[4])
            animation.setDuration(270 if opening else 150)
            Interpolator = _class("android.view.animation.DecelerateInterpolator")
            if Interpolator is not None:
                animation.setInterpolator(_b8_curve("DecelerateInterpolator", 1.0))
            animation.start()

            if opening:
                def finish_opening():
                    if self.transition is transition:
                        self.finish()

                self.runtime.schedule(finish_opening, 320)
        except Exception as exc:
            self.finish()
            self.runtime.log_suppressed("animate Glass Header Morph", exc)

    def _set_transform(self, view, transform):
        view.setTranslationX(transform[0])
        view.setTranslationY(transform[1])
        view.setScaleX(transform[2])
        view.setScaleY(transform[3])
        view.setAlpha(transform[4])

    def finish(self, fragment=None):
        transition = self.transition
        if transition is None:
            return
        if fragment is not None and transition["fragment_id"] != _identity(fragment):
            return
        self.transition = None
        view = transition.get("view")
        if view is not None:
            try:
                view.animate().cancel()
            except Exception as exc:
                self.runtime.log_suppressed("cancel Glass Header Morph", exc)
            try:
                self._set_transform(view, transition["base"])
            except Exception as exc:
                self.runtime.log_suppressed("restore Glass Header Morph", exc)


class _IOSHeaderMorphStartHook(MethodHook):
    def __init__(self, morph):
        self.morph = morph

    def after_hooked_method(self, param):
        self.morph.begin(param.thisObject, bool(param.args[0]), bool(param.args[1]))


class _IOSHeaderMorphEndHook(MethodHook):
    def __init__(self, morph):
        self.morph = morph

    def after_hooked_method(self, param):
        if not bool(param.args[0]):
            self.morph.finish(param.thisObject)


class _IOSHeaderMorphDestroyHook(MethodHook):
    def __init__(self, morph):
        self.morph = morph

    def before_hooked_method(self, param):
        fragment = param.thisObject
        self.morph.finish(fragment)
        self.morph.runtime.release_chat(fragment)


class _AvatarOverlapGuard:
    """Suppress only the paint of stock controls overlapping the avatar.

    Never alter visibility, enabled/clickable flags, listeners or menu
    geometry: the invisible native hit targets still open their own menus.
    Prefer transition alpha to keep the native logical alpha and its
    animations intact. Older Android builds fall back to ordinary alpha.
    Recheck before draw and restore only values owned by this guard.
    """

    def __init__(self, runtime):
        self.runtime = runtime
        self.bars = {}

    def bind(self, fragment, container, avatar):
        bar = _field(fragment, "actionBar")
        if bar is None:
            return
        key = _identity(bar)
        entry = self.bars.get(key)
        if entry is not None and _identity(entry["container"]) != _identity(container):
            self.release(entry)
            entry = None
        if entry is None:
            entry = {"fragment": fragment, "container": container,
                     "avatar": avatar, "bar": bar, "hidden": {}}
            self.bars[key] = entry
        else:
            entry["avatar"] = avatar
        entry.pop("candidate_cache", None)
        self.sync(bar)

    def bounds(self, view, bar):
        # Compute layout bounds independently of rendering alpha so invisible
        # artwork retains its native touch region.
        if view is None:
            return None
        w, h = float(view.getWidth()), float(view.getHeight())
        if w <= 0 or h <= 0:
            return None
        x, y, r, b = 0.0, 0.0, w, h
        node = view
        for _ in range(12):
            if _identity(node) == _identity(bar):
                return min(x, r), min(y, b), max(x, r), max(y, b)
            parent = node.getParent()
            if parent is None:
                return None
            sx, sy = float(node.getScaleX()), float(node.getScaleY())
            px, py = float(node.getPivotX()), float(node.getPivotY())
            dx = float(node.getX()) - float(parent.getScrollX())
            dy = float(node.getY()) - float(parent.getScrollY())
            x, r = dx + px + (x - px) * sx, dx + px + (r - px) * sx
            y, b = dy + py + (y - py) * sy, dy + py + (b - py) * sy
            node = parent
        return None

    def collides(self, a, b):
        if a is None or b is None:
            return False
        minimum = self.runtime.dp(3)
        return (min(a[2], b[2]) - max(a[0], b[0]) > minimum and
                min(a[3], b[3]) - max(a[1], b[1]) > minimum)

    def normal(self, entry):
        if not self.runtime.ios_header_enabled():
            return False
        bar, avatar, fragment = entry["bar"], entry["avatar"], entry["fragment"]
        if avatar is None or avatar.getVisibility() != View.VISIBLE:
            return False
        # bind() is called only from a supported chat layout.
        for name in ("isActionModeShowed", "isSearchFieldVisible"):
            try:
                if _beta_truth(getattr(bar, name)()):
                    return False
            except Exception:
                pass
        for name in ("actionModeVisible", "isSearchFieldVisible"):
            try:
                value = _field(bar, name)
                if value is not None and not callable(value) and _beta_truth(value):
                    return False
            except Exception:
                pass
        try:
            if fragment.isInPreviewMode():
                return False
        except Exception:
            pass
        return True

    def candidates(self, entry):
        bar, fragment = entry["bar"], entry["fragment"]
        items = {}
        def add(view, force=False):
            if view is not None and hasattr(view, "getVisibility") and hasattr(view, "setAlpha"):
                key = _identity(view)
                items[key] = (view, force or (items.get(key) or (None, False))[1])
        # headerItem is the stock avatar/menu placeholder intentionally
        # suppressed by 1.4. Also cover actual ActionBarMenu child buttons
        # (including the overflow and attachment icon seen in the report).
        add(_field(fragment, "headerItem"), True)
        for name in ("attachItem", "menuItem", "searchItem", "callItem", "videoCallItem"):
            add(_field(fragment, name))
        menus = []
        menu = _field(bar, "menu")
        if menu is not None:
            menus.append(menu)
        try:
            for i in range(int(bar.getChildCount())):
                child = bar.getChildAt(i)
                name = str(child.getClass().getSimpleName())
                if name == "ActionBarMenu":
                    menus.append(child)
                elif name == "ActionBarMenuItem":
                    add(child)
        except Exception:
            pass
        for menu in menus:
            try:
                for i in range(int(menu.getChildCount())):
                    add(menu.getChildAt(i))
            except Exception:
                pass
        return items

    def _suppress_paint(self, entry, key, view):
        # Transition alpha affects the RenderNode but not View.getAlpha(),
        # so menu logic and native property animations retain their state.
        record = entry["hidden"].get(key)
        if record is not None:
            try:
                current = float(getattr(view, record["getter"])())
                if current > 0.0:
                    # The client started/restarted an animation; remember its
                    # most recent value rather than restoring a stale alpha.
                    record["alpha"] = current
                    getattr(view, record["setter"])(0.0)
                return
            except Exception as exc:
                self.runtime.log_suppressed("refresh avatar-overlap paint", exc)
                self.restore_one(entry, key)

        for getter, setter in (
            ("getTransitionAlpha", "setTransitionAlpha"),
            ("getAlpha", "setAlpha"),
        ):
            try:
                alpha = float(getattr(view, getter)())
                if alpha <= 0.0:
                    # Already hidden by native state. Do not take ownership.
                    return
                getattr(view, setter)(0.0)
                entry["hidden"][key] = {
                    "view": view, "getter": getter, "setter": setter,
                    "alpha": alpha,
                }
                return
            except Exception:
                continue

    def restore_one(self, entry, key):
        record = entry["hidden"].pop(key, None)
        if record is None:
            return
        try:
            view = record["view"]
            # If the client has already set a new alpha, its value wins.
            if float(getattr(view, record["getter"])()) == 0.0:
                getattr(view, record["setter"])(record["alpha"])
        except Exception as exc:
            self.runtime.log_suppressed("restore avatar-overlap paint", exc)

    def release(self, entry):
        for key in list(entry["hidden"]):
            self.restore_one(entry, key)

    def sync(self, bar):
        entry = self.bars.get(_identity(bar))
        if entry is None:
            return
        try:
            if not self.normal(entry):
                self.release(entry)
                return
            bounds = self.bounds(entry["avatar"], bar)
            if bounds is None:
                self.release(entry)
                return
            wanted = set()
            clock = _class("android.os.SystemClock")
            now = int(clock.uptimeMillis()) if clock is not None else 0
            cache = entry.get("candidate_cache")
            if cache is None or not now or now - cache[0] >= 100:
                cache = (now, self.candidates(entry))
                entry["candidate_cache"] = cache
            for key, pair in cache[1].items():
                view, force = pair
                if key in (_identity(entry["avatar"]), _identity(entry["container"]), _identity(bar)):
                    continue
                # Native hidden/disabled state is never changed by this guard.
                if view.getVisibility() != View.VISIBLE:
                    continue
                if not force and not self.collides(bounds, self.bounds(view, bar)):
                    continue
                wanted.add(key)
                self._suppress_paint(entry, key, view)
            for key in list(entry["hidden"]):
                if key not in wanted:
                    self.restore_one(entry, key)
        except Exception as exc:
            self.runtime.log_suppressed("guard avatar overlap", exc)

    def destroy(self, fragment=None):
        for key, entry in list(self.bars.items()):
            if fragment is None or _identity(fragment) == _identity(entry["fragment"]):
                self.release(entry)
                self.bars.pop(key, None)


class _AvatarOverlapHook(MethodHook):
    def __init__(self, guard, destroy=False):
        self.guard = guard
        self.destroy = destroy

    def before_hooked_method(self, param):
        if self.destroy:
            self.guard.destroy(param.thisObject)
        else:
            self.guard.sync(param.thisObject)


class IOSHeaderRuntime:
    def __init__(self, api):
        self.api = api
        self._active = True
        self.morph_enabled = api.get_setting("header_morph", "on") == "on"
        self.header_morph = _HeaderMorph(self)
        self.avatar_guard = _AvatarOverlapGuard(self)
        self._ios_header_runtime: Dict[int, Dict[str, Any]] = {}
        self._header_error_logged = False
        self._suppressed_errors: Dict[str, int] = {}

    def ios_header_enabled(self) -> bool:
        return bool(self._active)

    def settings_changed(self, key, value):
        if _BETA is not None:
            _BETA.settings(key, value)
        if key == "header_morph":
            self.morph_enabled = value == "on"
            if not self.morph_enabled:
                self.header_morph.finish()
        for state in list(self._ios_header_runtime.values()):
            container = state.get("container")
            if container is not None:
                container.requestLayout()

    def _snapshot_ios_header_view(self, view: Any) -> Dict[str, Any]:
        if view is None:
            return {}
        snapshot: Dict[str, Any] = {"view": view}
        getters = {
            "background": "getBackground",
            "visibility": "getVisibility",
            "alpha": "getAlpha",
            "enabled": "isEnabled",
            "translation_x": "getTranslationX",
            "translation_y": "getTranslationY",
            "scale_x": "getScaleX",
            "scale_y": "getScaleY",
            "pivot_x": "getPivotX",
            "pivot_y": "getPivotY",
            "gravity": "getGravity",
            "padding_left": "getPaddingLeft",
            "padding_top": "getPaddingTop",
            "padding_right": "getPaddingRight",
            "padding_bottom": "getPaddingBottom",
        }
        for key, getter_name in getters.items():
            try:
                snapshot[key] = getattr(view, getter_name)()
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)
        for key, field_name in (
            ("right_drawable_outside", "rightDrawableOutside"),
            ("right_drawable_inside", "rightDrawableInside"),
            ("left_drawable_outside", "leftDrawableOutside"),
            ("can_hide_right_drawable", "canHideRightDrawable"),
            ("drawable_padding", "drawablePadding"),
            ("native_right_padding", "paddingRight"),
            ("fade_width", "fadeWidth"),
            ("scroll_non_fit", "scrollNonFitText"),
            ("scrolling", "scrolling"),
            ("ellipsize_gradient", "ellipsizeByGradient"),
            ("ellipsize_width", "ellipsizeByGradientWidthDp"),
            ("ellipsize_left", "forceEllipsizeByGradientLeft"),
        ):
            try:
                snapshot[key] = _field(view, field_name)
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)
        if snapshot.get("ellipsize_gradient") is None:
            try:
                drawable = view.getDrawable()
                if drawable is not None:
                    gradient = _field(drawable, "ellipsizeByGradient")
                    right_padding = _field(drawable, "rightPadding")
                    if gradient is not None:
                        snapshot["animated_gradient"] = bool(gradient)
                    if right_padding is not None:
                        snapshot["animated_right_padding"] = float(right_padding)
            except Exception:
                pass
        try:
            snapshot["text_size_px"] = float(view.getPaint().getTextSize())
            snapshot["typeface"] = view.getPaint().getTypeface()
        except Exception:
            pass
        return snapshot

    def _restore_ios_header_view(self, snapshot: Dict[str, Any]):
        view = snapshot.get("view")
        if view is None:
            return
        setters = {
            "background": "setBackground",
            "visibility": "setVisibility",
            "alpha": "setAlpha",
            "enabled": "setEnabled",
            "translation_x": "setTranslationX",
            "translation_y": "setTranslationY",
            "scale_x": "setScaleX",
            "scale_y": "setScaleY",
            "pivot_x": "setPivotX",
            "pivot_y": "setPivotY",
            "gravity": "setGravity",
        }
        for key, setter_name in setters.items():
            if key not in snapshot:
                continue
            try:
                getattr(view, setter_name)(snapshot[key])
            except Exception as exc:
                self._log_suppressed(f"restore iOS header {key}", exc)
        if "right_drawable_outside" in snapshot:
            try:
                view.setRightDrawableOutside(
                    bool(snapshot["right_drawable_outside"])
                )
            except Exception as exc:
                self._log_suppressed("restore title drawable mode", exc)
        for key, method in (
            ("right_drawable_inside", "setRightDrawableInside"),
            ("left_drawable_outside", "setLeftDrawableOutside"),
            ("can_hide_right_drawable", "setCanHideRightDrawable"),
            ("drawable_padding", "setDrawablePadding"),
            ("native_right_padding", "setRightPadding"),
        ):
            if snapshot.get(key) is not None:
                _ios7_try(view, method, snapshot[key])
        if "text_size_px" in snapshot:
            size = snapshot["text_size_px"]
            if not _ios7_try(view, "setTextSizePx", int(size)):
                _ios7_try(view, "setTextSize", float(size))
        if "animated_gradient" in snapshot:
            _ios7_try(view, "setEllipsizeByGradient", snapshot["animated_gradient"])
        if "animated_right_padding" in snapshot:
            _ios7_try(view, "setRightPadding", snapshot["animated_right_padding"])
        if snapshot.get("typeface") is not None:
            _ios7_try(view, "setTypeface", snapshot["typeface"])
        if "fade_width" in snapshot:
            try:
                view.setFadeWidth(int(snapshot["fade_width"]))
            except Exception as exc:
                self._log_suppressed("restore title fade", exc)
        if snapshot.get("ellipsize_gradient") is not None:
            try:
                _ios_header_set_text_overflow(
                    view,
                    bool(snapshot.get("scroll_non_fit")),
                    bool(snapshot["ellipsize_gradient"]),
                    int(snapshot.get("ellipsize_width") or 16),
                    snapshot.get("ellipsize_left"),
                )
            except Exception as exc:
                self._log_suppressed("restore iOS header gradient", exc)
        elif "scroll_non_fit" in snapshot:
            try:
                view.setScrollNonFitText(bool(snapshot["scroll_non_fit"]))
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)
        if "scrolling" in snapshot:
            try:
                view.setScrolling(bool(snapshot["scrolling"]))
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)
        if any(
            key in snapshot
            for key in (
                "padding_left",
                "padding_top",
                "padding_right",
                "padding_bottom",
            )
        ):
            try:
                view.setPadding(
                    int(snapshot.get("padding_left", view.getPaddingLeft())),
                    int(snapshot.get("padding_top", view.getPaddingTop())),
                    int(snapshot.get("padding_right", view.getPaddingRight())),
                    int(snapshot.get("padding_bottom", view.getPaddingBottom())),
                )
            except Exception as exc:
                self._log_suppressed("restore iOS header padding", exc)
        try:
            view.requestLayout()
            view.invalidate()
        except Exception as _suppressed_exc:
            _note_suppressed(_suppressed_exc)

    def remember_ios_header_state(
        self,
        container: Any,
        fragment: Any,
        title: Any = None,
        subtitle: Any = None,
        avatar: Any = None,
    ) -> Optional[Dict[str, Any]]:
        if container is None:
            return None
        key = _identity(container)
        state = self._ios_header_runtime.get(key)
        if state is None:
            state = {
                "container": container,
                "fragment": fragment,
                "container_state": self._snapshot_ios_header_view(container),
                "title_state": self._snapshot_ios_header_view(title),
                "subtitle_state": self._snapshot_ios_header_view(subtitle),
                "avatar_state": self._snapshot_ios_header_view(avatar),
            }
            try:
                params = container.getLayoutParams()
                if params is not None and hasattr(params, "rightMargin"):
                    state["container_right_margin"] = int(params.rightMargin)
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)
            self._ios_header_runtime[key] = state
            self._prune_runtime_refs()
        else:
            if fragment is not None:
                state["fragment"] = fragment
            for state_key, view in (
                ("title_state", title),
                ("subtitle_state", subtitle),
                ("avatar_state", avatar),
            ):
                snapshot = state.get(state_key)
                if view is not None and (
                    not isinstance(snapshot, dict)
                    or _identity(snapshot.get("view")) != _identity(view)
                ):
                    state[state_key] = self._snapshot_ios_header_view(view)

        for state_key, field_name in (
            ("header_item_state", "headerItem"),
            ("search_item_state", "searchItem"),
        ):
            if fragment is None:
                continue
            try:
                view = _field(fragment, field_name)
            except Exception:
                view = None
            snapshot = state.get(state_key)
            if view is not None and (
                not isinstance(snapshot, dict)
                or _identity(snapshot.get("view")) != _identity(view)
            ):
                state[state_key] = self._snapshot_ios_header_view(view)
        return state

    def suppress_ios_stock_center_glass(
        self,
        fragment: Any,
        state: Dict[str, Any],
    ):
        """Disable Telegram's wide center/menu glass at the ActionBar level.

        Recent Telegram ActionBar builds expose the private `glassOnlyBack`
        switch. Unlike changing drawable alpha, this flag is consulted by the
        ActionBar drawing path itself, so the stock full-width center pill is
        never drawn while the experimental iOS header is active.
        """
        if fragment is None or state is None:
            return

        try:
            action_bar = self.field(fragment, "actionBar")
        except Exception:
            action_bar = None
        if action_bar is None:
            return

        stock_mode = self.field(action_bar, "glassOnlyBack")
        previous_bar = state.get("action_bar")
        if previous_bar is None or _identity(previous_bar) != _identity(action_bar):
            # Restore a previously tracked ActionBar before switching to a new
            # instance (for example after a theme/configuration recreation).
            if previous_bar is not None and "stock_glass_only_back" in state:
                try:
                    self.set_field_value(
                        previous_bar,
                        "glassOnlyBack",
                        bool(state.get("stock_glass_only_back", False)),
                    )
                    previous_bar.invalidate()
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)

            state["action_bar"] = action_bar
            state["stock_glass_only_back"] = bool(stock_mode)

        if stock_mode:
            return

        changed = self.set_field_value(action_bar, "glassOnlyBack", True)
        if not changed:
            # Public method exists on current Telegram builds; keep it as a
            # compatibility fallback if reflection is restricted.
            try:
                action_bar.setGlassOnlyBack()
                changed = True
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)

        if changed:
            try:
                action_bar.invalidate()
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)

    def _suppress_header_backgrounds(self, *views):
        for view in views:
            try:
                if view is not None and view.getBackground() is not None:
                    view.setBackground(None)
            except Exception as exc:
                self.log_suppressed("suppress stock header background", exc)

    def ensure_ios_header_glass(
        self,
        container: Any,
        fragment: Any,
        title: Any = None,
        subtitle: Any = None,
    ) -> Any:
        """Create one compact native blur3 island behind the header text."""
        if container is None or fragment is None:
            return None

        key = _identity(container)
        current = self._ios_header_runtime.get(key)
        if current is None:
            current = self.remember_ios_header_state(
                container,
                fragment,
                title,
                subtitle,
                self.field(container, "avatarImageView"),
            )
        if current is not None:
            glass = current.get("glass")
            try:
                if glass is not None and _identity(glass.getParent()) == key:
                    self._suppress_header_backgrounds(container, title, subtitle)
                    self.suppress_ios_stock_center_glass(fragment, current)
                    return glass
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)

            if glass is not None:
                # Restore the ActionBar drawing mode if this header instance
                # was detached/recreated between layout passes.
                old_bar = current.get("action_bar")
                if old_bar is not None and "stock_glass_only_back" in current:
                    try:
                        self.set_field_value(
                            old_bar,
                            "glassOnlyBack",
                            bool(current.get("stock_glass_only_back", False)),
                        )
                        old_bar.invalidate()
                    except Exception as exc:
                        self._log_suppressed("restore detached ActionBar", exc)
                current.pop("glass", None)
                current.pop("glass_info", None)

        glass = None
        try:
            context = container.getContext()
            glass = View(context)
            glass.setClickable(False)
            glass.setFocusable(False)
            try:
                glass.setImportantForAccessibility(
                    View.IMPORTANT_FOR_ACCESSIBILITY_NO
                )
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)

            params = ViewGroup.LayoutParams(self.dp(1), self.dp(1))
            container.addView(glass, 0, params)

            top_key = getattr(
                Theme,
                "key_actionBarDefault",
                Theme.key_actionBarDefaultSubmenuBackground,
            )
            glass_info = self.create_glass_surface(
                fragment,
                glass,
                top_key,
                0.72,
                self.dp(24),
                False,
            )
            if glass_info is None:
                try:
                    container.removeView(glass)
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)
                return None

            state = current or {
                "container": container,
                "fragment": fragment,
                "container_state": self._snapshot_ios_header_view(container),
                "title_state": self._snapshot_ios_header_view(title),
                "subtitle_state": self._snapshot_ios_header_view(subtitle),
            }
            state["glass"] = glass
            state["glass_info"] = glass_info

            self._suppress_header_backgrounds(container, title, subtitle)
            self.suppress_ios_stock_center_glass(fragment, state)
            self._ios_header_runtime[key] = state
            return glass
        except Exception as exc:
            if glass is not None:
                try:
                    parent = glass.getParent()
                    if parent is not None:
                        parent.removeView(glass)
                except Exception as cleanup_exc:
                    self.log_suppressed("remove incomplete glass", cleanup_exc)
            self.log_once_header_error(exc)
            return None

    def layout_ios_header_glass(
        self,
        glass: Any,
        left: int,
        top: int,
        width: int,
        height: int,
        measure_spec: Any,
    ):
        if glass is None or width <= 0 or height <= 0:
            return
        try:
            if glass.getVisibility() != View.VISIBLE:
                glass.setVisibility(View.VISIBLE)
            if not glass.isLayoutRequested() and (
                glass.getLeft(), glass.getTop(), glass.getWidth(), glass.getHeight()
            ) == (left, top, width, height):
                return
            if int(glass.getHeight()) != height:
                drawable = glass.getBackground()
                if drawable is not None:
                    drawable.setRadius(float(height) * 0.5)
            glass.measure(
                measure_spec.makeMeasureSpec(int(width), measure_spec.EXACTLY),
                measure_spec.makeMeasureSpec(int(height), measure_spec.EXACTLY),
            )
            glass.layout(
                int(left),
                int(top),
                int(left + width),
                int(top + height),
            )
            glass.invalidate()
        except Exception as _suppressed_exc:
            _note_suppressed(_suppressed_exc)

    def update_ios_header_strength(self, strength: int):
        for state in list(self._ios_header_runtime.values()):
            info = state.get("glass_info")
            if not info:
                continue
            self.apply_glass_drawable(
                info.get("drawable"),
                info.get("view"),
                strength,
                bool(info.get("prefer_light", False)),
            )

    def release_chat(self, fragment):
        if fragment is None:
            return
        try:
            self.avatar_guard.destroy(fragment)
        except Exception as exc:
            self.log_suppressed("release avatar guard", exc)
        try:
            if _BETA is not None:
                _BETA.release_chat(fragment)
        except Exception as exc:
            self.log_suppressed("release chat features", exc)
        self.restore_ios_header_glass(fragment)

    def restore_ios_header_glass(self, fragment=None):
        for key, state in list(self._ios_header_runtime.items()):
            if fragment is not None and _identity(state.get("fragment")) != _identity(fragment):
                continue
            self._ios_header_runtime.pop(key, None)
            container = state.get("container")
            glass = state.get("glass")
            if glass is not None:
                try:
                    parent = glass.getParent()
                    if parent is not None:
                        parent.removeView(glass)
                except Exception as exc:
                    self._log_suppressed("remove iOS header glass", exc)

            for snapshot_key in (
                "container_state",
                "title_state",
                "subtitle_state",
                "avatar_state",
                "search_item_state",
            ):
                snapshot = state.get(snapshot_key)
                if isinstance(snapshot, dict):
                    self._restore_ios_header_view(snapshot)

            if container is not None and "container_right_margin" in state:
                try:
                    params = container.getLayoutParams()
                    if params is not None and hasattr(params, "rightMargin"):
                        params.rightMargin = int(state["container_right_margin"])
                        container.setLayoutParams(params)
                except Exception as exc:
                    self._log_suppressed("restore iOS header margin", exc)

            action_bar = state.get("action_bar")
            if action_bar is not None:
                try:
                    self.set_field_value(
                        action_bar,
                        "glassOnlyBack",
                        bool(state.get("stock_glass_only_back", False)),
                    )
                    action_bar.invalidate()
                except Exception as exc:
                    self._log_suppressed("restore iOS ActionBar", exc)

    def log(self, message: Any):
        self.api.log(message)

    def log_suppressed(self, context: str, exc: Any):
        key = str(context)
        count = int(self._suppressed_errors.get(key, 0)) + 1
        self._suppressed_errors[key] = count
        if count <= 3 or count in (8, 32, 128):
            self.log(f"{key} failed ({count}): {exc}")

    def _log_suppressed(self, context: str, exc: Any):
        self.log_suppressed(context, exc)

    def field(self, obj: Any, name: str):
        return self.api.get_field(obj, name)

    def set_field_value(self, obj: Any, name: str, value: Any) -> bool:
        return self.api.set_field(obj, name, value)

    def dp(self, value: float) -> int:
        return self.api.dp(value)

    def current_strength(self) -> int:
        return self.api.current_strength()

    def schedule(self, callback, delay: int = 0):
        if self._active:
            self.api.schedule(callback, delay)

    def create_glass_surface(
        self, fragment: Any, view: Any, color_key: int,
        intensity: float, radius: int, prefer_light: bool,
    ):
        return self.api.create_glass_surface(
            fragment, view, color_key, intensity, radius, prefer_light
        )

    def apply_glass_drawable(
        self, drawable: Any, view: Any, strength: int, prefer_light: bool
    ) -> bool:
        return self.api.apply_glass_drawable(
            drawable, view, strength, prefer_light
        )

    def rebuild_current_fragment_views(self):
        return self.api.rebuild_current_fragment_views()

    def _view_is_detached(self, view: Any) -> bool:
        if view is None:
            return True
        try:
            attached = bool(view.isAttachedToWindow())
        except Exception:
            attached = None
        try:
            parent = view.getParent()
        except Exception:
            parent = None
        return attached is False and parent is None

    def _prune_runtime_refs(self):
        if len(self._ios_header_runtime) <= 256:
            return
        for key, state in list(self._ios_header_runtime.items()):
            if len(self._ios_header_runtime) <= 256:
                break
            if self._view_is_detached(state.get("container")):
                if state.get("fragment") is not None:
                    self.avatar_guard.destroy(state["fragment"])
                self._ios_header_runtime.pop(key, None)
        while len(self._ios_header_runtime) > 256:
            old = self._ios_header_runtime.pop(next(iter(self._ios_header_runtime)), None)
            if old is not None and old.get("fragment") is not None:
                self.avatar_guard.destroy(old["fragment"])

    def log_once_header_error(self, exc: Any):
        if self._header_error_logged:
            return
        self._header_error_logged = True
        self.log(f"iOS header layout fallback: {exc}")

    def _hook_optional_methods(self, clazz: Any, method_names: Any, hook: Any):
        if clazz is None:
            return
        for method_name in method_names:
            try:
                self.api.hook_all_methods(clazz, method_name, hook)
            except Exception as exc:
                self.log_suppressed(f"hook {method_name}", exc)

    def _hook_optional_constructors(self, clazz: Any, hook: Any):
        if clazz is None:
            return
        try:
            self.api.hook_all_constructors(clazz, hook)
        except Exception as exc:
            self.log_suppressed("hook constructors", exc)

    def install_hooks(self):
        chat_header_class = self.api.find_class(
            "org.telegram.ui.Components.ChatAvatarContainer"
        )
        self._hook_optional_constructors(
            chat_header_class, _IOSHeaderCreatedHook(self)
        )
        self._hook_optional_methods(
            chat_header_class,
            (
                "setTitle",
                "setTopic",
                "setSubtitle",
                "updateSubtitle",
                "showTimeItem",
                "hideTimeItem",
                "setTime",
                "setCommunityItemVisible",
            ),
            _IOSHeaderRefreshHook(self),
        )
        self._hook_optional_methods(
            chat_header_class, ("onLayout",), _IOSHeaderLayoutHook(self)
        )
        chat_activity_class = self.api.find_class("org.telegram.ui.ChatActivity")
        self._hook_optional_methods(
            chat_activity_class, ("createView",), _IOSHeaderChatViewHook(self)
        )

        self._hook_optional_methods(
            chat_activity_class,
            ("onTransitionAnimationStart",),
            _IOSHeaderMorphStartHook(self.header_morph),
        )
        self._hook_optional_methods(
            chat_activity_class,
            ("onTransitionAnimationEnd",),
            _IOSHeaderMorphEndHook(self.header_morph),
        )
        self._hook_optional_methods(
            chat_activity_class,
            ("onFragmentDestroy",),
            _IOSHeaderMorphDestroyHook(self.header_morph),
        )

        action_bar_class = self.api.find_class("org.telegram.ui.ActionBar.ActionBar")
        self._hook_optional_methods(action_bar_class, ("dispatchDraw",), _AvatarOverlapHook(self.avatar_guard))
        self._hook_optional_methods(chat_activity_class, ("onFragmentDestroy",), _AvatarOverlapHook(self.avatar_guard, True))

    def shutdown(self):
        self._active = False
        self.avatar_guard.destroy()
        self.header_morph.finish()
        self.restore_ios_header_glass()
        self.rebuild_current_fragment_views()


def on_load(api):
    global _API, _RUNTIME, AndroidUtilities, View, ViewGroup, Gravity, Theme, TextLayout
    _API = api
    AndroidUtilities = api.find_class("org.telegram.messenger.AndroidUtilities")
    View = api.find_class("android.view.View")
    ViewGroup = api.find_class("android.view.ViewGroup")
    Gravity = api.find_class("android.view.Gravity")
    Theme = api.find_class("org.telegram.ui.ActionBar.Theme")
    TextLayout = api.find_class("android.text.Layout")
    if any(item is None for item in (AndroidUtilities, View, ViewGroup, Gravity, Theme)):
        raise RuntimeError("required Android or Telegram class is unavailable")
    runtime = IOSHeaderRuntime(api)
    _RUNTIME = runtime
    runtime.install_hooks()
    api.register_settings(_SETTINGS + _BETA_SETTINGS, runtime.settings_changed)
    api.register_strength_listener(runtime.update_ios_header_strength)
    _beta_load(api)
    runtime.rebuild_current_fragment_views()
    api.log("iOS Header 1.5 loaded")


def on_unload(api):
    global _RUNTIME, _API
    _beta_unload(api)
    runtime = _RUNTIME
    if runtime is not None:
        runtime.shutdown()
    _RUNTIME = None
    _API = None
    _B8_CLASSES.clear()
    _B8_INTERPOLATORS.clear()
    api.log("iOS Header unloaded")

# Beta features: adaptation of iOS Experience (Rin / @itsRin).
_BETA_SETTINGS = [
    {"type": "choice", "key": "profile_open", "text": "Открытие профиля", "icon": "msg_settings", "default": "on", "options": [
        {"value": "on", "text": "Включено", "subtext": "Фото раскрывается из аватара"}, {"value": "off", "text": "Выключено"}]},
    {"type": "choice", "key": "unread_badge", "text": "Счётчик непрочитанных", "icon": "msg_settings", "default": "off", "options": [
        {"value": "on", "text": "Включён"}, {"value": "off", "text": "Выключен"}]},
]
_BETA = None


def _beta_label(count):
    count = max(0, int(count))
    return "999+" if count > 999 else str(count)


def _beta_truth(value):
    try:
        return bool(value.booleanValue())
    except Exception:
        return bool(value)


def _beta_geometry(count):
    # Back.chipGeometry in the reference DEX: width, height, extra offset.
    digits = len(_beta_label(max(1, count)))
    return ((18, 16, 3.5), (24, 16, 7.5), (30, 16, 13.5), (38, 16, 17.5))[min(4, digits) - 1]


class _BetaFeatures:
    def __init__(self, api):
        self.api = api
        self.active = True
        self.integrated = False
        self.profile = api.get_setting("profile_open", "on") == "on"
        self.badge = api.get_setting("unread_badge", "off") == "on"
        self.tick_generation = 0
        self.tick_running = False
        self.entries = {}
        self.pending = None
        self.motion = None
        self.paint = None
        self.profile_sources = {}
        self.errors = {}
        self.View = api.find_class("android.view.View")
        self.Theme = api.find_class("org.telegram.ui.ActionBar.Theme")
        self.G = api.find_class("android.view.Gravity")

    def log(self, key, exc):
        n = self.errors.get(key, 0) + 1
        self.errors[key] = n
        if n <= 3:
            self.api.log("iOS Header Beta / %s: %s" % (key, exc))

    def field(self, obj, name):
        return self.api.get_field(obj, name) if obj is not None else None

    def cls(self, name):
        return _class(name)

    def key(self, obj):
        return self.api.identity(obj) if obj is not None else 0

    def dp(self, value):
        return self.api.dp(value)

    def chat(self, f):
        try:
            if f is None or str(f.getClass().getSimpleName()) != "ChatActivity" or not int(f.getDialogId()):
                return False
            if hasattr(f, "isInPreviewMode") and f.isInPreviewMode():
                return False
            return True
        except Exception:
            return False

    def allowed(self, f, bar):
        if not self.active or not self.badge or not self.chat(f) or bar is None:
            return False
        for name in ("isActionModeShowed", "isSearchFieldVisible"):
            try:
                if getattr(bar, name)():
                    return False
            except Exception:
                pass
        return True

    def count(self, f):
        # Prefer the same explicit policy on all clients: non-muted unread
        # messages in folder 0, excluding the currently open dialog.
        current = int(f.getDialogId())
        try:
            try:
                mc = f.getMessagesController()
            except Exception:
                mc = self.cls("org.telegram.messenger.MessagesController").getInstance(int(f.getCurrentAccount()))
            try:
                dialogs = mc.getDialogs(0)
            except Exception:
                dialogs = None
            if dialogs is None:
                folders = self.field(mc, "dialogsByFolder")
                dialogs = folders.get(0) if folders is not None else None
            if dialogs is not None:
                total = 0
                for i in range(int(dialogs.size())):
                    d = dialogs.get(i)
                    did = int(self.field(d, "id") or 0)
                    n = max(0, int(self.field(d, "unread_count") or 0))
                    if not did or did == current or not n:
                        continue
                    try:
                        muted = _beta_truth(mc.isDialogMuted(did, 0))
                    except Exception:
                        try:
                            muted = _beta_truth(mc.isDialogMuted(did))
                        except Exception:
                            muted = False
                    if not muted:
                        total += n
                    if total > 999:
                        return 1000
                return total
        except Exception as exc:
            self.log("read unread dialogs", exc)
        # Older builds may not expose folder data. Their native total can
        # differ, but is preferable to a stale custom count.
        try:
            return min(1000, max(0, int(f.getMessagesStorage().getMainUnreadCount())))
        except Exception:
            return 0

    def back(self, bar):
        try:
            v = bar.getBackButton()
            if v is not None:
                return v
        except Exception:
            pass
        return self.field(bar, "backButtonImageView")

    def entry(self, f, bar):
        key = self.key(bar)
        if key in self.entries:
            return self.entries[key]
        v = self.cls("android.widget.TextView")(bar.getContext())
        v.setTag("glassify_ios_header_beta_unread_chip")
        v.setGravity(self.G.CENTER)
        v.setIncludeFontPadding(False)
        v.setSingleLine(True)
        v.setTextSize(1, 14.0)
        try:
            v.setTypeface(self.cls("android.graphics.Typeface").create("sans-serif-medium", 0))
        except Exception:
            pass
        v.setPadding(0, 0, 0, 0)
        v.setClickable(False)
        v.setFocusable(False)
        v.setImportantForAccessibility(self.View.IMPORTANT_FOR_ACCESSIBILITY_NO)
        # White iOS unread badge inside the existing glass back capsule.
        badge_background = self.cls("android.graphics.drawable.GradientDrawable")()
        badge_background.setColor(-1)  # opaque white
        badge_background.setCornerRadius(float(self.dp(11)))
        v.setBackground(badge_background)
        v.setTextColor(-16777216)  # black, independent of the chat theme
        v.setVisibility(self.View.GONE)
        pill = self.View(bar.getContext())
        pill.setClickable(False)
        pill.setFocusable(False)
        pill.setImportantForAccessibility(self.View.IMPORTANT_FOR_ACCESSIBILITY_NO)
        pill.setVisibility(self.View.GONE)
        params = self.cls("android.widget.FrameLayout$LayoutParams")
        try:
            bar.addView(pill, 0, params(self.dp(46), self.dp(46)))
            info = self.api.create_glass_surface(f, pill, self.Theme.key_actionBarDefault, 0.72, self.dp(23), False)
            if info is None:
                raise RuntimeError("native back glass unavailable")
            bar.addView(v, params(self.dp(24), self.dp(22)))
        except Exception:
            if v.getParent() is not None:
                v.getParent().removeView(v)
            if pill.getParent() is not None:
                pill.getParent().removeView(pill)
            raise
        e = {"fragment": f, "bar": bar, "chip": v, "pill": pill,
             "glass_info": info, "count": 0, "display_count": 1, "width": float(self.dp(46)),
             "target": float(self.dp(46)), "generation": 0, "expanding": False}
        self.entries[key] = e
        return e

    def restore_stock(self, e):
        stock = e.pop("stock", None)
        if stock is not None:
            try:
                if int(stock[0].getAlpha()) == 0:
                    stock[0].setAlpha(stock[1])
            except Exception as exc:
                self.log("restore back glass", exc)
        # No ImageView alpha or drawable replacement: invalidating the native
        # button restores its ordinary drawing after this entry is hidden.
        try:
            back = self.back(e["bar"])
            if back is not None:
                back.invalidate()
        except Exception as exc:
            self.log("restore back arrow", exc)
        e["bar"].invalidate()

    def suppress_stock(self, e):
        stock = self.field(e["bar"], "glassDrawableBack")
        saved = e.get("stock")
        if saved is not None and self.key(stock) != self.key(saved[0]):
            self.restore_stock(e)
            saved = None
        if stock is not None and saved is None:
            try:
                alpha = int(stock.getAlpha())
            except Exception:
                alpha = 255
            stock.setAlpha(0)
            e["stock"] = (stock, alpha)
        elif saved is not None:
            try:
                alpha = int(stock.getAlpha())
                if alpha != 0:
                    e["stock"] = (stock, alpha)
                    stock.setAlpha(0)
            except Exception:
                pass

    def prepare_draw(self, bar):
        if not self.active or not self.badge or not self.entries:
            return
        e = self.entries.get(self.key(bar))
        if e is None or e["pill"].getVisibility() != self.View.VISIBLE:
            return
        if not self.allowed(e["fragment"], bar):
            self.hide(e, True)
            return
        back = self.back(bar)
        if back is None:
            self.hide(e, True)
            return
        try:
            drawable = back.getDrawable()
            if drawable is not None and abs(float(drawable.getRotation())) > 0.01:
                self.hide(e, True)
                return
        except Exception:
            pass
        self.suppress_stock(e)

    def draw_native_chevron(self, param):
        """Replace only the active chat's native BackDrawable draw call.

        Drawing inside the original ImageView preserves Android's transforms,
        alpha, native touch target and the working profile animation. If this
        hook is absent or the drawable is different, no second arrow is drawn.
        """
        if not self.active or not self.badge or not self.entries or len(param.args) != 1:
            return
        drawable = param.thisObject
        for e in list(self.entries.values()):
            pill, bar = e["pill"], e["bar"]
            if pill.getVisibility() != self.View.VISIBLE or not self.allowed(e["fragment"], bar):
                continue
            back = self.back(bar)
            if back is None or back.getVisibility() != self.View.VISIBLE:
                continue
            current = back.getDrawable()
            if current is None or self.key(current) != self.key(drawable):
                continue
            try:
                if abs(float(drawable.getRotation())) > 0.01:
                    return
            except Exception:
                return
            bounds = drawable.getBounds()
            if bounds.width() <= 0 or bounds.height() <= 0:
                return
            if self.paint is None:
                self.paint = self.cls("android.graphics.Paint")(3)
                self.paint.setStyle(self.cls("android.graphics.Paint$Style").STROKE)
                self.paint.setStrokeCap(self.cls("android.graphics.Paint$Cap").ROUND)
                self.paint.setStrokeJoin(self.cls("android.graphics.Paint$Join").ROUND)
            self.paint.setStrokeWidth(float(self.dp(2.0)))
            self.paint.setColor(int(self.Theme.getColor(self.Theme.key_actionBarDefaultIcon)))
            # The native drawable is centered in the button. Offset within
            # its own canvas instead of moving the native hit target.
            center = float(back.getLeft()) + float(back.getWidth()) / 2.0
            desired = float(pill.getLeft()) + float(self.dp(18))
            x = float(bounds.exactCenterX()) + desired - center
            y = float(bounds.exactCenterY())
            dx, dy = float(self.dp(4)), float(self.dp(7))
            canvas = param.args[0]
            # BackDrawable.setAlpha() can be a no-op. Stop the original draw
            # before painting, so a rejected hook cannot create two arrows.
            param.setResult(None)
            canvas.drawLine(x + dx, y - dy, x - dx, y, self.paint)
            canvas.drawLine(x - dx, y, x + dx, y + dy, self.paint)
            return

    def strength(self, strength):
        for e in list(self.entries.values()):
            info = e["glass_info"]
            try:
                self.api.apply_glass_drawable(info.get("drawable"), e["pill"], strength, bool(info.get("prefer_light", False)))
            except Exception as exc:
                self.log("back glass strength", exc)

    def animate_width(self, e, target):
        if e["target"] == target and (e["expanding"] or e["width"] == target):
            return
        previous_reserve = int(max(e["width"], e["target"]))
        e["target"] = target
        if int(max(e["width"], target)) != previous_reserve:
            self.relayout(e)
        e["generation"] += 1
        gen = e["generation"]
        start = float(e["width"])
        e["expanding"] = True
        clock = self.cls("android.os.SystemClock")
        started = int(clock.uptimeMillis())
        interp = _b8_curve("PathInterpolator", 0.1, 1.0, 0.25, 1.0)
        def frame():
            if not self.active or e["generation"] != gen or self.entries.get(self.key(e["bar"])) is not e:
                return
            p = min(1.0, max(0.0, (int(clock.uptimeMillis()) - started) / 380.0))
            old_pixels = int(round(e["width"]))
            old_reserve = int(max(e["width"], target))
            e["width"] = start + (target - start) * float(interp.getInterpolation(p))
            new_pixels = int(round(e["width"]))
            new_reserve = int(max(e["width"], target))
            if new_pixels != old_pixels or p >= 1.0:
                self.position(e)
                e["bar"].invalidate()
            if old_reserve != new_reserve:
                self.relayout(e)
            if p < 1.0:
                self.api.schedule(frame, 16)
            else:
                e["width"] = target
                e["expanding"] = False
                if not e["count"]:
                    self.hide(e, True)
        frame()

    def relayout(self, e):
        container = self.field(e["fragment"], "avatarContainer")
        if container is not None:
            if not container.isLayoutRequested():
                container.requestLayout()

    def hide(self, e, immediate=False):
        if e is None:
            return
        v, pill = e["chip"], e["pill"]
        if not immediate and not e["count"] and e["expanding"]:
            return
        if not immediate and e["count"] and pill.getVisibility() == self.View.VISIBLE and self.allowed(e["fragment"], e["bar"]):
            e["count"] = 0
            v.animate().cancel()
            v.animate().alpha(0.0).scaleX(0.0).scaleY(0.0).setDuration(160).start()
            self.animate_width(e, float(self.dp(46)))
            return
        if pill.getVisibility() == self.View.GONE and not e.get("stock"):
            return
        e["generation"] += 1
        e["expanding"] = False
        e["count"] = 0
        e["width"] = e["target"] = float(self.dp(46))
        v.animate().cancel()
        v.setVisibility(self.View.GONE)
        v.setAlpha(1.0)
        v.setScaleX(1.0)
        v.setScaleY(1.0)
        pill.setVisibility(self.View.GONE)
        pill.setAlpha(1.0)
        self.restore_stock(e)
        self.relayout(e)

    def remove(self, key):
        e = self.entries.get(key)
        if e is None:
            return
        try:
            self.hide(e, True)
        except Exception as exc:
            self.log("hide unread", exc)
        self.entries.pop(key, None)
        e["generation"] += 1
        for v in (e["chip"], e["pill"]):
            try:
                v.animate().cancel()
                if v.getParent() is not None:
                    v.getParent().removeView(v)
            except Exception as exc:
                self.log("remove unread", exc)
        self.relayout(e)

    def clear(self, f=None):
        for key, e in list(self.entries.items()):
            if f is None or self.key(f) == self.key(e["fragment"]):
                self.remove(key)

    def glass(self, f):
        c = self.field(f, "avatarContainer")
        if c is None or _RUNTIME is None:
            return None
        state = _RUNTIME._ios_header_runtime.get(self.key(c)) or {}
        v = state.get("glass")
        if v is not None and self.key(v.getParent()) == self.key(c):
            return v
        return None

    def badge_geometry(self, e, back):
        # Use the actual back button bounds (not a fixed screen coordinate).
        # Reserve space even if the client uses the stock arrow fallback.
        v = e["chip"]
        label = _beta_label(e["display_count"])
        try:
            font_size = float(v.getPaint().getTextSize())
        except Exception:
            font_size = 0.0
        metric_key = (label, font_size, self.dp(22), self.dp(8))
        metrics = e.get("badge_metrics")
        if metrics is not None and metrics[0] == metric_key:
            w, h = metrics[1], metrics[2]
        else:
            w, _, _ = _beta_geometry(e["display_count"])
            w = self.dp(w)
            try:
                w = max(w, int(v.getPaint().measureText(str(v.getText()))) + self.dp(8))
            except Exception:
                pass
            h = self.dp(22)
            try:
                fm = v.getPaint().getFontMetrics()
                h = max(h, int(float(fm.descent) - float(fm.ascent)) + self.dp(2))
            except Exception:
                pass
            w = h if len(label) == 1 and w <= h else max(w, h)
            e["badge_metrics"] = (metric_key, w, h)
        if e.get("badge_height") != h:
            v.getBackground().setCornerRadius(float(h) / 2.0)
            e["badge_height"] = h
        bx = max(0, int(back.getLeft()) + self.dp(6))
        x = max(bx + self.dp(35), int(back.getLeft() + back.getWidth() / 2.0) + self.dp(16))
        target = max(self.dp(46), x + w + self.dp(9) - bx)
        return bx, x, w, h, target

    def position(self, e):
        v, pill, bar = e["chip"], e["pill"], e["bar"]
        if pill.getVisibility() != self.View.VISIBLE:
            return
        back = self.back(bar)
        if back is None or back.getVisibility() != self.View.VISIBLE or back.getWidth() <= 0:
            self.hide(e, True)
            return
        bx, x, w, h, target = self.badge_geometry(e, back)
        bh = self.dp(46)
        bw = max(self.dp(46), int(round(e["width"])))
        cy = int(back.getTop()) + int(back.getHeight()) // 2
        by, y = cy - bh // 2, cy - h // 2
        if bx + max(bw, target) > int(bar.getWidth()) - self.dp(100):
            self.hide(e, True)
            return
        spec = self.cls("android.view.View$MeasureSpec")
        for view, left, top, width, height in ((pill, bx, by, bw, bh), (v, x, y, w, h)):
            if (view.getLeft(), view.getTop(), view.getWidth(), view.getHeight()) != (left, top, width, height):
                view.measure(spec.makeMeasureSpec(width, spec.EXACTLY), spec.makeMeasureSpec(height, spec.EXACTLY))
                view.layout(left, top, left + width, top + height)
                view.invalidate()
        # Do not draw a digit outside the glass during the expansion.
        if self.motion is None and e["count"]:
            alpha = 1.0 if bx + bw >= x + w + self.dp(4) else 0.0
            if float(v.getAlpha()) != alpha:
                v.setAlpha(alpha)

    def left_bound(self, f, c):
        e = self.entries.get(self.key(self.field(f, "actionBar")))
        if e is None or not self.allowed(f, e["bar"]) or e["pill"].getVisibility() != self.View.VISIBLE:
            return 0
        # Use the final target during expansion so title never overlaps the back capsule.
        right = int(e["pill"].getLeft()) + max(int(e["width"]), int(e["target"]))
        return max(0, right - int(c.getLeft()) + self.dp(8))

    def refresh(self, f, bar):
        e = self.entries.get(self.key(bar))
        if not self.allowed(f, bar):
            self.hide(e, True)
            return
        back = self.back(bar)
        if back is None or back.getVisibility() != self.View.VISIBLE or back.getWidth() <= 0:
            self.hide(e, True)
            return
        n = self.count(f)
        if n <= 0:
            self.hide(e)
            return
        e = self.entry(f, bar)
        v, pill = e["chip"], e["pill"]
        changed = e["count"] != n or pill.getVisibility() != self.View.VISIBLE
        if changed:
            hidden = pill.getVisibility() != self.View.VISIBLE
            e["count"] = n
            e["display_count"] = n
            v.setText(_beta_label(n))
            pill.setVisibility(self.View.VISIBLE)
            pill.setAlpha(1.0)
            v.setVisibility(self.View.VISIBLE)
            self.suppress_stock(e)
            bx, _, _, _, target = self.badge_geometry(e, back)
            target = float(target)
            if bx + target > int(bar.getWidth()) - self.dp(100):
                self.hide(e, True)
                return
            self.animate_width(e, target)
            back.invalidate()
            v.animate().cancel()
            v.setScaleX(0.0 if hidden else 0.88)
            v.setScaleY(0.0 if hidden else 0.88)
            v.animate().scaleX(1.0).scaleY(1.0).setDuration(380).setInterpolator(_b8_curve("PathInterpolator", 0.1, 1.0, 0.25, 1.0)).start()
            self.relayout(e)
        if e["count"] and pill.getVisibility() == self.View.VISIBLE:
            _, _, _, _, target = self.badge_geometry(e, back)
            if float(target) != e["target"]:
                self.animate_width(e, float(target))
        self.position(e)

    def layout(self, bar):
        if not self.active or not self.badge or not self.entries:
            return
        e = self.entries.get(self.key(bar))
        if e is not None:
            if self.allowed(e["fragment"], bar):
                self.position(e)
            else:
                self.hide(e, True)

    def stop_tick(self):
        self.tick_generation += 1
        self.tick_running = False

    def start_tick(self):
        if not self.active or not self.badge or self.tick_running:
            return
        self.tick_running = True
        self.tick_generation += 1
        generation = self.tick_generation
        self.api.schedule(lambda: self.tick(generation), 0)

    def tick(self, generation):
        if not self.active or not self.badge or generation != self.tick_generation:
            return
        try:
            f = self.api.get_last_fragment()
            if self.badge and self.chat(f) and self.glass(f) is not None and self.motion is None:
                self.refresh(f, self.field(f, "actionBar"))
            for key, e in list(self.entries.items()):
                if e["bar"].getParent() is None and not e["bar"].isAttachedToWindow():
                    self.remove(key)
        except Exception as exc:
            self.log("refresh unread", exc)
        if self.active and self.badge and generation == self.tick_generation:
            self.api.schedule(lambda: self.tick(generation), 750)

    def mark(self, param):
        if not self.active or not self.profile:
            return
        args = param.args
        if len(args) != 3 or not _beta_truth(args[1]):
            return
        f = self.field(param.thisObject, "parentFragment")
        if not self.chat(f):
            return
        # Exact behavior of ProfileOpen$OpenProfileHook: if the second
        # flag is true, force the first flag true. Copy the boxed Boolean
        # from args[1] instead of assuming the bridge coerces Python bool.
        if not _beta_truth(args[0]):
            args[0] = args[1]
        self.pending = f
        if _RUNTIME is not None:
            _RUNTIME.header_morph.finish(f)
        def expire():
            if self.pending is f:
                self.pending = None
        self.api.schedule(expire, 2500)

    def profile_dialog(self, profile):
        # User IDs and chat IDs may have the same absolute value; retain sign.
        try:
            did = int(profile.getDialogId())
            if did:
                return did
        except Exception:
            pass
        try:
            user_id = int(self.field(profile, "userId") or 0)
            chat_id = int(self.field(profile, "chatId") or 0)
            if user_id > 0 and not chat_id:
                return user_id
            if chat_id > 0 and not user_id:
                return -chat_id
        except Exception:
            pass
        return 0

    def matches_profile(self, f, profile):
        if not self.chat(f):
            return False
        try:
            did = self.profile_dialog(profile)
            return (did != 0 and int(f.getDialogId()) == did and
                    int(f.getCurrentAccount()) == int(profile.getCurrentAccount()))
        except Exception:
            return False

    def source(self, profile):
        try:
            stack = profile.getParentLayout().getFragmentStack()
            size = int(stack.size()) if hasattr(stack, "size") else len(stack)
            for i in range(size - 1, 0, -1):
                item = stack.get(i) if hasattr(stack, "get") else stack[i]
                if self.key(item) == self.key(profile):
                    f = stack.get(i - 1) if hasattr(stack, "get") else stack[i - 1]
                    if self.matches_profile(f, profile):
                        return f
                    break
        except Exception:
            pass
        remembered = self.profile_sources.get(self.key(profile))
        if self.matches_profile(remembered, profile):
            return remembered
        if self.matches_profile(self.pending, profile):
            return self.pending
        if _RUNTIME is not None:
            for state in list(_RUNTIME._ios_header_runtime.values()):
                f = state.get("fragment")
                if self.matches_profile(f, profile):
                    return f
        # Unknown identity: leave the client's native animation alone.
        return None

    def release_chat(self, fragment):
        key = self.key(fragment)
        if not key:
            return
        if self.pending is not None and self.key(self.pending) == key:
            self.pending = None
        if self.motion is not None and self.key(self.motion.get("source")) == key:
            self.finish()
        for profile_key, source in list(self.profile_sources.items()):
            if self.key(source) == key:
                self.profile_sources.pop(profile_key, None)
        self.clear(fragment)

    def finish(self, profile=None):
        m = self.motion
        if m is None or (profile is not None and self.key(profile) != self.key(m["profile"])):
            return
        self.motion = None
        for v, alpha, sx, sy in m["views"]:
            try:
                v.animate().cancel()
                v.animate().setStartDelay(0)
                v.setAlpha(alpha)
                v.setScaleX(sx)
                v.setScaleY(sy)
            except Exception as exc:
                self.log("restore profile chrome", exc)
        for v, visibility in m.get("held", []):
            try:
                v.setVisibility(visibility)
            except Exception as exc:
                self.log("restore profile name", exc)

    def transition(self, profile, opening, animator=None):
        if not self.active or not self.profile:
            return
        if self.motion is not None and self.key(self.motion["profile"]) == self.key(profile) and self.motion["opening"] == opening:
            if animator is None or self.motion["custom"]:
                return
        f = self.source(profile)
        if not self.chat(f):
            return
        self.finish()
        self.pending = None
        if len(self.profile_sources) >= 64:
            self.profile_sources.pop(next(iter(self.profile_sources)), None)
        self.profile_sources[self.key(profile)] = f
        glass = self.glass(f)
        if glass is None:
            return
        try:
            va = self.cls("android.animation.ValueAnimator")
            if hasattr(va, "areAnimatorsEnabled") and not va.areAnimatorsEnabled():
                return
        except Exception:
            pass
        # Port the original native photo AnimatorSet timing and Bezier curves.
        duration = 460 if opening else 506
        if animator is not None:
            try:
                avatar = self.field(profile, "avatarImage")
                receiver = avatar.getImageReceiver() if avatar is not None else None
                if receiver is not None and receiver.hasNotThumb():
                    animator.setDuration(duration)
                    curve = (0.2, 0.85, 0.25, 1.0) if opening else (0.25, 0.9, 0.25, 1.0)
                    animator.setInterpolator(_b8_curve("PathInterpolator", *curve))
                else:
                    original = int(animator.getDuration())
                    if original > 0:
                        duration = original
            except Exception as exc:
                self.log("native avatar timing", exc)
        c = self.field(f, "avatarContainer")
        bar = self.field(f, "actionBar")
        texts = [glass, self.field(c, "titleTextView"), self.field(c, "subtitleTextView")]
        if bar is not None:
            texts.append(self.back(bar))
            e = self.entries.get(self.key(bar))
            if e is not None:
                texts.extend((e["pill"], e["chip"]))
            texts.append(self.field(bar, "menu"))
        m = {"profile": profile, "source": f, "opening": opening, "custom": animator is not None, "views": [], "held": []}
        self.motion = m
        try:
            # Keep avatarImageView unmodified; native ProfileActivity owns photo interpolation.
            seen = set()
            for v in texts:
                if v is None or self.key(v) in seen or v.getVisibility() != self.View.VISIBLE:
                    continue
                seen.add(self.key(v))
                alpha, sx, sy = float(v.getAlpha()), float(v.getScaleX()), float(v.getScaleY())
                if alpha <= 0:
                    continue
                m["views"].append((v, alpha, sx, sy))
                v.animate().cancel()
                if not opening:
                    v.setAlpha(0.0)
                    v.setScaleX(sx * 0.94)
                    v.setScaleY(sy * 0.94)
                a = v.animate().alpha(0.0 if opening else alpha)
                a.scaleX(sx * 0.94 if opening else sx).scaleY(sy * 0.94 if opening else sy)
                a.setStartDelay(0 if opening else min(100, duration // 4))
                a.setDuration(min(220, duration) if opening else max(100, duration - 100))
                a.setInterpolator(_b8_curve("PathInterpolator", 0.2, 0.85, 0.25, 1.0))
                a.start()
            def expire():
                if self.motion is m:
                    self.finish(profile)
            self.api.schedule(expire, duration + 100)
        except Exception as exc:
            self.finish()
            self.log("profile transition", exc)

    def settings(self, key, value):
        if key == "profile_open":
            self.profile = value == "on"
            if not self.profile:
                self.pending = None
                self.finish()
                self.profile_sources.clear()
        elif key == "unread_badge":
            self.badge = value == "on"
            if not self.badge:
                self.stop_tick()
                self.clear()
            else:
                self.start_tick()

    def install(self):
        for name, methods, kind in (
            ("org.telegram.ui.Components.ChatAvatarContainer", ("openProfile",), "mark"),
            ("org.telegram.ui.ProfileActivity", ("onCustomTransitionAnimation",), "profile"),
            ("org.telegram.ui.ProfileActivity", ("onTransitionAnimationStart",), "profile_start"),
            ("org.telegram.ui.ProfileActivity", ("onTransitionAnimationEnd",), "end"),
            ("org.telegram.ui.ProfileActivity", ("onFragmentDestroy",), "profile_destroy"),
            ("org.telegram.ui.ActionBar.ActionBar", ("onLayout",), "layout"),
            ("org.telegram.ui.ActionBar.ActionBar", ("dispatchDraw",), "draw"),
            ("org.telegram.ui.ActionBar.BackDrawable", ("draw",), "native_arrow"),
            ("org.telegram.ui.ChatActivity", ("onFragmentDestroy",), "destroy"),
        ):
            for method in methods:
                try:
                    clazz = self.cls(name)
                    if clazz is not None:
                        self.api.hook_all_methods(clazz, method, _BetaHook(self, kind))
                except Exception as exc:
                    self.log("hook " + kind + " " + method, exc)
        self.api.register_strength_listener(self.strength)
        self.start_tick()

    def shutdown(self):
        self.active = False
        self.stop_tick()
        self.pending = None
        self.finish()
        self.profile_sources.clear()
        self.clear()


class _BetaHook(MethodHook):
    def __init__(self, features, kind):
        self.f = features
        self.kind = kind

    def before_hooked_method(self, param):
        try:
            if self.kind == "mark":
                self.f.mark(param)
            elif self.kind == "draw":
                self.f.prepare_draw(param.thisObject)
            elif self.kind == "native_arrow":
                self.f.draw_native_chevron(param)
            elif self.kind == "destroy":
                self.f.release_chat(param.thisObject)
        except Exception as exc:
            self.f.log("feature before hook", exc)

    def after_hooked_method(self, param):
        try:
            if self.kind == "layout":
                self.f.layout(param.thisObject)
            elif self.kind == "profile" and len(param.args) > 0:
                self.f.transition(param.thisObject, _beta_truth(param.args[0]), param.getResult())
            elif self.kind == "profile_start" and len(param.args) > 0:
                self.f.transition(param.thisObject, _beta_truth(param.args[0]))
            elif self.kind == "end":
                self.f.finish(param.thisObject)
            elif self.kind == "profile_destroy":
                self.f.finish(param.thisObject)
                self.f.profile_sources.pop(self.f.key(param.thisObject), None)
        except Exception as exc:
            self.f.log("feature after hook", exc)


def _beta_load(api):
    global _BETA
    try:
        _BETA = _BetaFeatures(api)
        _BETA.integrated = True
        _BETA.install()
        api.log("iOS Header beta features loaded")
    except Exception as exc:
        if _BETA is not None:
            try:
                _BETA.shutdown()
            except Exception:
                pass
        _BETA = None
        api.log("iOS Header beta features unavailable: " + str(exc))


def _beta_unload(api):
    global _BETA
    if _BETA is not None:
        _BETA.shutdown()
    _BETA = None
