GLASSIFY_EXTENSION = {
    "id": "ios_header",
    "name": "iOS Header",
    "version": "1.4",
    "api": 3,
    "description": "iOS-шапка чата с настройками размера, затуханием имени и Glass Header Morph.",
    "min_glassify": "0.5.0",
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

_SETTINGS = [
    {
        "type": "choice",
        "key": "pill_size",
        "text": "Размер капсулы",
        "icon": "msg_customize",
        "default": "adaptive",
        "options": [
            {"value": "adaptive", "text": "По имени", "subtext": "Ширина зависит от имени и статуса."},
            {"value": "ios", "text": "Базовый размер iOS", "subtext": "178 × 44 dp. Сужается только при нехватке места."},
        ],
    },
    {
        "type": "choice",
        "key": "title_scroll",
        "text": "Прокрутка имени",
        "icon": "msg_settings",
        "default": "off",
        "options": [
            {"value": "off", "text": "Выключена", "subtext": "Конец длинного имени плавно затухает."},
            {"value": "on", "text": "Для длинных имён", "subtext": "Имя движется только при нехватке места."},
        ],
    },
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
    return _API.find_class(name)


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
            if title is not None:
                title.setRightDrawableOutside(False)
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

            fixed_pill = self.plugin.fixed_pill
            pill_height = self.plugin.dp(44 if fixed_pill else 48)
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

            header_item = None
            try:
                header_item = _field(fragment, "headerItem")
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)
            if header_item is not None:
                try:
                    avatar_visible = (
                        avatar is not None
                        and avatar.getVisibility() == View.VISIBLE
                    )
                    header_item.setAlpha(0.0 if avatar_visible else 1.0)
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)

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

            # Keep ChatAvatarContainer full-width so native hit targets stay
            # intact. ActionBar itself is switched to glassOnlyBack, preventing
            # its stretched center pill from being drawn. One compact blur3
            # island is then drawn behind the real title/subtitle block.
            # Size the glass for whichever visible row is wider. Group and
            # channel subtitles (for example "30 участников") can be wider
            # than very short titles, so title-only sizing lets the subtitle
            # escape past the rounded island.
            title_width = 0
            subtitle_width = 0
            if title is not None:
                try:
                    if title.getVisibility() != View.GONE:
                        title_width = _ios_header_text_extent(title)
                except Exception:
                    title_width = _ios_header_text_extent(title)
            if subtitle is not None:
                try:
                    if subtitle.getVisibility() != View.GONE:
                        subtitle_width = _ios_header_text_extent(subtitle)
                except Exception:
                    subtitle_width = _ios_header_text_extent(subtitle)
            content_width = max(title_width, subtitle_width)

            horizontal_inset = self.plugin.dp(14 if fixed_pill else 16)
            island_padding = horizontal_inset * 2

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
                            or float(time_item.getAlpha()) > 0.01
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

            min_island = self.plugin.dp(82)
            if time_item_active:
                needed_left = time_item_width - timer_overlap_x + time_item_gap
                left_bound += max(0, min(needed_left, available - min_island))
            desired_width = (
                self.plugin.dp(178)
                if fixed_pill
                else max(min_island, content_width + island_padding)
            )
            toolbar_center = (
                parent_width // 2 - left_on_screen if parent_width > 0 else width // 2
            )
            island_left, island_width = _ios_header_pill_bounds(
                toolbar_center, left_bound, right_bound, desired_width, min_island
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

            def place_text(view: Any, y: int, row_width: int, allow_scroll: bool):
                if view is None or view.getVisibility() == View.GONE:
                    return

                # Telegram creates subtitleTextView with a 10dp right padding
                # and gradient clipping. Re-measuring that same view as a
                # centered compact row makes its internal drawing area
                # asymmetric and is what intermittently cuts the left edge.
                # Keep vertical padding, but own horizontal geometry here.
                try:
                    padding_top = _ios_header_int(view.getPaddingTop())
                    padding_bottom = _ios_header_int(view.getPaddingBottom())
                    if (
                        _ios_header_int(view.getPaddingLeft()) != 0
                        or _ios_header_int(view.getPaddingRight()) != 0
                    ):
                        view.setPadding(0, padding_top, 0, padding_bottom)
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)

                # Native header transitions may leave a temporary X
                # translation on the text view. The compact island owns X.
                try:
                    view.setTranslationX(0.0)
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)

                overflow = row_width > text_width
                row_left = text_left
                row_box_width = text_width
                if 0 < row_width <= text_width:
                    row_box_width = min(text_width, row_width + self.plugin.dp(2))
                    row_left = island_left + (island_width - row_box_width) // 2

                view.setGravity(Gravity.LEFT | Gravity.CENTER_VERTICAL)
                scrolling = overflow and allow_scroll
                _ios_header_set_text_overflow(view, scrolling, overflow and not scrolling)

                try:
                    view.measure(
                        MeasureSpec.makeMeasureSpec(
                            int(row_box_width),
                            MeasureSpec.EXACTLY,
                        ),
                        MeasureSpec.makeMeasureSpec(
                            int(height),
                            MeasureSpec.AT_MOST,
                        ),
                    )
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)

                measured_h = _ios_header_int(view.getMeasuredHeight())
                view.layout(
                    int(row_left),
                    int(y),
                    int(row_left + row_box_width),
                    int(y + measured_h),
                )

            if title is not None and title.getVisibility() != View.GONE:
                try:
                    title.setRightDrawableOutside(False)
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)
                title_y = pill_top + self.plugin.dp(4 if fixed_pill else 5)
                try:
                    title_y -= _ios_header_int(title.getPaddingTop())
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)
                place_text(title, title_y, title_width, self.plugin.scroll_title)

            if subtitle is not None and subtitle.getVisibility() != View.GONE:
                place_text(subtitle, pill_top + self.plugin.dp(22 if fixed_pill else 25), subtitle_width, False)
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
                animation.setInterpolator(Interpolator(1.0))
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
        self.morph.finish(param.thisObject)


class IOSHeaderRuntime:
    def __init__(self, api):
        self.api = api
        self._active = True
        self.fixed_pill = api.get_setting("pill_size", "adaptive") == "ios"
        self.scroll_title = api.get_setting("title_scroll", "off") == "on"
        self.morph_enabled = api.get_setting("header_morph", "on") == "on"
        self.header_morph = _HeaderMorph(self)
        self._ios_header_runtime: Dict[int, Dict[str, Any]] = {}
        self._header_error_logged = False
        self._suppressed_errors: Dict[str, int] = {}

    def ios_header_enabled(self) -> bool:
        return bool(self._active)

    def settings_changed(self, key, value):
        if key == "pill_size":
            self.fixed_pill = value == "ios"
        elif key == "title_scroll":
            self.scroll_title = value == "on"
        elif key == "header_morph":
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
            state.setdefault("fragment", fragment)
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

    def restore_ios_header_glass(self):
        for state in list(self._ios_header_runtime.values()):
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
                "header_item_state",
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

        self._ios_header_runtime.clear()

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
                self._ios_header_runtime.pop(key, None)
        while len(self._ios_header_runtime) > 256:
            self._ios_header_runtime.pop(next(iter(self._ios_header_runtime)), None)

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

    def shutdown(self):
        self._active = False
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
    api.register_settings(_SETTINGS, runtime.settings_changed)
    api.register_strength_listener(runtime.update_ios_header_strength)
    runtime.rebuild_current_fragment_views()
    api.log("iOS Header 1.4 loaded")


def on_unload(api):
    global _RUNTIME, _API
    runtime = _RUNTIME
    if runtime is not None:
        runtime.shutdown()
    _RUNTIME = None
    _API = None
    api.log("iOS Header unloaded")
