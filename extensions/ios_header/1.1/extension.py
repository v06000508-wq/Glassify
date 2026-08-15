GLASSIFY_EXTENSION = {
    "id": "ios_header",
    "name": "iOS Header",
    "version": "1.1",
    "api": 2,
}

_API = None
_RUNTIME = None
AndroidUtilities = None
View = None
ViewGroup = None
Gravity = None
Theme = None


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
    """Measure the actual rendered text, not the View/container width."""
    if view is None:
        return 0

    text = None
    try:
        text = view.getText()
    except Exception as _suppressed_exc:
        _note_suppressed(_suppressed_exc)

    # Prefer Paint.measureText(). Some Telegram SimpleTextView builds expose
    # getTextWidth() as a layout/cache width, which can equal the whole bar.
    if text is not None:
        paints = []
        try:
            paints.append(_field(view, "textPaint"))
        except Exception as _suppressed_exc:
            _note_suppressed(_suppressed_exc)
        try:
            paints.append(view.getPaint())
        except Exception as _suppressed_exc:
            _note_suppressed(_suppressed_exc)
        try:
            drawable = _field(view, "drawable")
            if drawable is not None:
                paints.append(_field(drawable, "textPaint"))
                paints.append(_field(drawable, "paint"))
        except Exception as _suppressed_exc:
            _note_suppressed(_suppressed_exc)

        for paint in paints:
            if paint is None:
                continue
            try:
                width = _ios_header_int(paint.measureText(str(text)))
                if width > 0:
                    # Keep room for Telegram's small title-side icons.
                    icons = 0
                    for field_name in (
                        "leftDrawable",
                        "rightDrawable",
                        "rightDrawable2",
                        "rightDrawableOuter",
                    ):
                        try:
                            if _field(view, field_name) is not None:
                                icons += AndroidUtilities.dp(22)
                        except Exception as _suppressed_exc:
                            _note_suppressed(_suppressed_exc)
                    return max(0, width + icons)
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)

    try:
        width = _ios_header_int(view.getTextWidth())
        if width > 0:
            return width
    except Exception as _suppressed_exc:
        _note_suppressed(_suppressed_exc)
    return 0


def _ios_header_set_marquee(view: Any, enabled: bool, fade_px: int):
    if view is None:
        return
    try:
        view.setFadeWidth(int(fade_px if enabled else 0))
    except Exception as _suppressed_exc:
        _note_suppressed(_suppressed_exc)
    for name in ("setScrollNonFitText", "setScrolling"):
        try:
            getattr(view, name)(bool(enabled))
        except Exception as _suppressed_exc:
            _note_suppressed(_suppressed_exc)

    if not enabled:
        # SimpleTextView keeps its scrollingOffset when marquee is disabled.
        # The stale offset still translates the canvas and can clip a fitting
        # title/subtitle from the left by a different amount on each refresh.
        reset = False
        try:
            view.resetScrolling()
            reset = True
        except Exception as _suppressed_exc:
            _note_suppressed(_suppressed_exc)
        if not reset and _API is not None:
            try:
                _API.set_field(view, "scrollingOffset", 0.0)
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)
        try:
            view.invalidate()
        except Exception as _suppressed_exc:
            _note_suppressed(_suppressed_exc)


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

            title_block_top = (bar_height - self.plugin.dp(45)) // 2 + top_offset
            activity_subtitle = _ios_header_subtitle_is_activity(
                subtitle,
                fragment,
            )

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

                show_avatar = not saved and not activity_subtitle
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

            horizontal_inset = self.plugin.dp(16)
            island_padding = horizontal_inset * 2
            min_island = self.plugin.dp(82)
            desired_width = max(min_island, content_width + island_padding)
            island_width = min(available, desired_width)

            # Prefer the visual center, clamped between back/navigation controls
            # and the avatar. Short names now visibly produce a short glass pill.
            island_left = (width - island_width) // 2
            island_left = max(left_bound, island_left)
            island_left = min(island_left, right_bound - island_width)
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
                title_block_top - self.plugin.dp(1),
                island_width,
                self.plugin.dp(48),
                MeasureSpec,
            )

            text_left = island_left + horizontal_inset
            text_right = island_right - horizontal_inset
            text_width = max(self.plugin.dp(24), text_right - text_left)

            def place_text(view: Any, y: int):
                if view is None or view.getVisibility() == View.GONE:
                    return

                row_width = _ios_header_text_extent(view)
                fits = row_width <= text_width if row_width > 0 else True
                try:
                    view.setGravity(Gravity.CENTER if fits else Gravity.LEFT)
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)
                _ios_header_set_marquee(
                    view,
                    not fits,
                    self.plugin.dp(10),
                )

                try:
                    view.measure(
                        MeasureSpec.makeMeasureSpec(
                            int(text_width),
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
                    int(text_left),
                    int(y),
                    int(text_right),
                    int(y + measured_h),
                )

            if title is not None and title.getVisibility() != View.GONE:
                try:
                    title.setRightDrawableOutside(False)
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)
                title_y = title_block_top + self.plugin.dp(4)
                try:
                    title_y -= _ios_header_int(title.getPaddingTop())
                except Exception as _suppressed_exc:
                    _note_suppressed(_suppressed_exc)
                place_text(title, title_y)

            if subtitle is not None and subtitle.getVisibility() != View.GONE:
                place_text(subtitle, title_block_top + self.plugin.dp(24))
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


class IOSHeaderRuntime:
    def __init__(self, api):
        self.api = api
        self._active = True
        self._ios_header_runtime: Dict[int, Dict[str, Any]] = {}
        self._header_error_logged = False
        self._suppressed_errors: Dict[str, int] = {}

    def ios_header_enabled(self) -> bool:
        return bool(self._active)

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
        if "scroll_non_fit" in snapshot:
            try:
                view.setScrollNonFitText(bool(snapshot["scroll_non_fit"]))
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)
        if "scrolling" in snapshot:
            try:
                view.setScrolling(bool(snapshot["scrolling"]))
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)
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
                    or snapshot.get("view") is not view
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
                or snapshot.get("view") is not view
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

        previous_bar = state.get("action_bar")
        if previous_bar is not action_bar:
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

            original = False
            try:
                value = self.field(action_bar, "glassOnlyBack")
                if value is not None:
                    original = bool(value)
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)
            state["action_bar"] = action_bar
            state["stock_glass_only_back"] = original

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
                if glass is not None and glass.getParent() is container:
                    # Telegram can refresh header backgrounds on state/theme
                    # changes. Keep the full-width surfaces suppressed while
                    # the compact island is active.
                    try:
                        container.setBackground(None)
                    except Exception as _suppressed_exc:
                        _note_suppressed(_suppressed_exc)
                    try:
                        if title is not None:
                            title.setBackground(None)
                    except Exception as _suppressed_exc:
                        _note_suppressed(_suppressed_exc)
                    try:
                        if subtitle is not None:
                            subtitle.setBackground(None)
                    except Exception as _suppressed_exc:
                        _note_suppressed(_suppressed_exc)
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

            # The stock/foreign header glass is tied to the full-width
            # ChatAvatarContainer. Remove those backgrounds only after our
            # compact native blur drawable was created successfully.
            try:
                container.setBackground(None)
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)
            try:
                if title is not None:
                    title.setBackground(None)
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)
            try:
                if subtitle is not None:
                    subtitle.setBackground(None)
            except Exception as _suppressed_exc:
                _note_suppressed(_suppressed_exc)

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
            glass.setVisibility(View.VISIBLE)
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
        stale = []
        for key, state in list(self._ios_header_runtime.items()):
            info = state.get("glass_info")
            if not info:
                continue
            if not self.apply_glass_drawable(
                info.get("drawable"),
                info.get("view"),
                strength,
                bool(info.get("prefer_light", False)),
            ):
                stale.append(key)
        for key in stale:
            self._ios_header_runtime.pop(key, None)

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
            ("setTitle", "setTopic", "setSubtitle", "updateSubtitle"),
            _IOSHeaderRefreshHook(self),
        )
        self._hook_optional_methods(
            chat_header_class, ("onLayout",), _IOSHeaderLayoutHook(self)
        )
        chat_activity_class = self.api.find_class("org.telegram.ui.ChatActivity")
        self._hook_optional_methods(
            chat_activity_class, ("createView",), _IOSHeaderChatViewHook(self)
        )

    def shutdown(self):
        self._active = False
        self.restore_ios_header_glass()
        self.rebuild_current_fragment_views()


def on_load(api):
    global _API, _RUNTIME, AndroidUtilities, View, ViewGroup, Gravity, Theme
    _API = api
    AndroidUtilities = api.find_class("org.telegram.messenger.AndroidUtilities")
    View = api.find_class("android.view.View")
    ViewGroup = api.find_class("android.view.ViewGroup")
    Gravity = api.find_class("android.view.Gravity")
    Theme = api.find_class("org.telegram.ui.ActionBar.Theme")
    if any(item is None for item in (AndroidUtilities, View, ViewGroup, Gravity, Theme)):
        raise RuntimeError("required Android or Telegram class is unavailable")
    runtime = IOSHeaderRuntime(api)
    _RUNTIME = runtime
    runtime.install_hooks()
    api.register_strength_listener(runtime.update_ios_header_strength)
    runtime.rebuild_current_fragment_views()
    api.log("iOS Header 1.1 loaded")


def on_unload(api):
    global _RUNTIME, _API
    runtime = _RUNTIME
    if runtime is not None:
        runtime.shutdown()
    _RUNTIME = None
    _API = None
    api.log("iOS Header unloaded")
