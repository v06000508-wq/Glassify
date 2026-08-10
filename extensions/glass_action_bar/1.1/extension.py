GLASSIFY_EXTENSION = {
    "id": "glass_action_bar",
    "name": "Glass Action Bar",
    "version": "1.1",
    "api": 3,
}

_API = None
_RUNTIME = None

_EXCLUDED = (
    "ChatActivity",
    "DialogsActivity",
    "MainTabsActivity",
    "LaunchActivity",
    "PhotoViewer",
    "ArticleViewer",
    "SecretMediaViewer",
    "VoIPFragment",
)

_FACTORY_FIELDS = (
    "glassBackgroundDrawableFactory",
    "glassBackgroundDrawableFactoryFrosted",
    "iBlur3FactoryFrostedLiquidGlass",
    "iBlur3FactoryLiquidGlass",
    "iBlur3FactoryBlur",
    "blurredBackgroundDrawableViewFactory",
    "blurredBackgroundDrawableFactory",
)

_SOURCE_FIELDS = (
    "iBlur3SourceGlass",
    "iBlur3SourceGlassFrosted",
    "glassBackgroundSourceRenderNode",
    "glassBackgroundSourceFrostedRenderNode",
    "blurredBackgroundSource",
    "iBlur3Source",
)


def _field(obj: Any, name: str):
    if _API is None or obj is None:
        return None
    try:
        return _API.get_field(obj, name)
    except Exception:
        return None


def _class_name(obj: Any) -> str:
    if obj is None:
        return ""
    try:
        return str(obj.getClass().getName())
    except Exception:
        return ""


def _int(value: Any, fallback: int = 0) -> int:
    try:
        return fallback if value is None else int(value)
    except Exception:
        return fallback


class _ActionBarCreatedHook(MethodHook):
    def __init__(self, runtime):
        self.runtime = runtime

    def after_hooked_method(self, param):
        try:
            bar = param.getResult()
        except Exception:
            bar = None
        self.runtime.decorate(param.thisObject, bar)


class _ParentLayoutHook(MethodHook):
    def __init__(self, runtime):
        self.runtime = runtime

    def after_hooked_method(self, param):
        fragment = param.thisObject
        self.runtime.decorate(fragment)
        self.runtime.schedule(lambda: self.runtime.decorate(fragment), 48)


class _ResumeHook(MethodHook):
    def __init__(self, runtime):
        self.runtime = runtime

    def after_hooked_method(self, param):
        fragment = param.thisObject
        self.runtime.schedule(lambda: self.runtime.decorate(fragment), 0)


class _ActionBarLayoutHook(MethodHook):
    def __init__(self, runtime):
        self.runtime = runtime

    def after_hooked_method(self, param):
        self.runtime.layout_bar(param.thisObject)


class GlassActionBarRuntime:
    def __init__(self, api):
        self.api = api
        self.active = True
        self.states: Dict[int, Dict[str, Any]] = {}
        self.View = api.find_class("android.view.View")
        self.ViewGroup = api.find_class("android.view.ViewGroup")
        self.MeasureSpec = api.find_class("android.view.View$MeasureSpec")
        self.Factory = api.find_class(
            "org.telegram.ui.Components.blur3.BlurredBackgroundDrawableViewFactory"
        )
        self.Provider = api.find_class(
            "org.telegram.ui.Components.blur3.drawable.color.BlurredBackgroundColorProviderThemed"
        )
        self.Theme = api.find_class("org.telegram.ui.ActionBar.Theme")
        if any(item is None for item in (
            self.View,
            self.ViewGroup,
            self.MeasureSpec,
            self.Factory,
            self.Provider,
            self.Theme,
        )):
            raise RuntimeError("required Android or Blur3 classes are unavailable")

    def log(self, text: Any):
        self.api.log(text)

    def schedule(self, callback, delay: int = 0):
        if self.active:
            self.api.schedule(callback, delay)

    def supported(self, fragment: Any) -> bool:
        name = _class_name(fragment)
        if not name:
            return False
        short = name.rsplit(".", 1)[-1]
        for token in _EXCLUDED:
            if token in short:
                return False
        try:
            if bool(fragment.isInPreviewMode()):
                return False
        except Exception:
            pass
        try:
            if bool(fragment.isInBubbleMode()):
                return False
        except Exception:
            pass
        return True

    def action_bar(self, fragment: Any, supplied: Any = None):
        if supplied is not None:
            return supplied
        bar = _field(fragment, "actionBar")
        if bar is not None:
            return bar
        try:
            return fragment.getActionBar()
        except Exception:
            return None

    def resources_provider(self, fragment: Any):
        provider = _field(fragment, "themeDelegate") or _field(fragment, "resourceProvider")
        if provider is not None:
            return provider
        try:
            return fragment.getResourceProvider()
        except Exception:
            return None

    def direct_factory(self, fragment: Any, bar: Any):
        for owner in (fragment, bar):
            for name in _FACTORY_FIELDS:
                value = _field(owner, name)
                if value is not None:
                    return value
        return None

    def source_factory(self, fragment: Any):
        source = None
        for name in _SOURCE_FIELDS:
            source = _field(fragment, name)
            if source is not None:
                break
        if source is None:
            return None
        try:
            factory = self.Factory(source)
            try:
                factory.setLiquidGlassEffectAllowed(True)
            except Exception:
                pass
            return factory
        except Exception as exc:
            self.log("Glass Action Bar: factory fallback failed: " + str(exc))
            return None

    def resolve_factory(self, fragment: Any, bar: Any):
        return self.direct_factory(fragment, bar) or self.source_factory(fragment)

    def title_view(self, bar: Any):
        title_array = _field(bar, "titleTextView")
        if title_array is None:
            return None
        try:
            title = title_array[0]
        except Exception:
            try:
                title = title_array.get(0)
            except Exception:
                return None
        if title is None:
            return None
        try:
            if title.getVisibility() == self.View.GONE:
                return None
        except Exception:
            pass
        try:
            text = title.getText()
        except Exception:
            text = None
        if text is None or not str(text).strip():
            return None
        return title

    def text_width(self, title: Any) -> int:
        if title is None:
            return 0
        try:
            width = _int(title.getTextWidth())
            if width > 0:
                return width
        except Exception:
            pass
        try:
            text = title.getText()
        except Exception:
            text = None
        if text is None:
            return 0
        paint = _field(title, "textPaint")
        if paint is not None:
            try:
                return max(0, _int(paint.measureText(str(text))))
            except Exception:
                pass
        try:
            paint = title.getPaint()
            return max(0, _int(paint.measureText(str(text))))
        except Exception:
            return 0

    def create_title_pill(self, fragment: Any, bar: Any, state: Dict[str, Any]):
        pill = self.View(bar.getContext())
        pill.setClickable(False)
        pill.setFocusable(False)
        try:
            pill.setImportantForAccessibility(self.View.IMPORTANT_FOR_ACCESSIBILITY_NO)
        except Exception:
            pass
        bar.addView(pill, 0, self.ViewGroup.LayoutParams(self.api.dp(1), self.api.dp(1)))

        color_key = int(getattr(self.Theme, "key_actionBarDefault"))
        info = self.api.create_glass_surface(
            fragment,
            pill,
            color_key,
            0.72,
            self.api.dp(23),
            False,
        )
        if info is None:
            try:
                bar.removeView(pill)
            except Exception:
                pass
            return None, None
        state["pill"] = pill
        state["pill_info"] = info
        return pill, info

    def decorate(self, fragment: Any, supplied_bar: Any = None):
        if not self.active or not self.supported(fragment):
            return

        bar = self.action_bar(fragment, supplied_bar)
        if bar is None:
            return

        key = self.api.identity(bar)
        existing = self.states.get(key)
        if existing is not None:
            existing["fragment"] = fragment
            self.layout_bar(bar)
            self.apply_state(existing, self.api.current_strength())
            return

        factory = self.resolve_factory(fragment, bar)
        if factory is None:
            return

        try:
            color_key = int(getattr(self.Theme, "key_actionBarDefault"))
            provider = self.Provider(
                self.resources_provider(fragment),
                color_key,
                0.82,
            )
            bar.setupGlass(factory, provider)

            try:
                if not self.api.set_field(bar, "glassOnlyBack", True):
                    bar.setGlassOnlyBack()
            except Exception:
                try:
                    bar.setGlassOnlyBack()
                except Exception:
                    pass

            state = {
                "fragment": fragment,
                "bar": bar,
                "factory": factory,
                "provider": provider,
                "drawables": [],
                "pill": None,
                "pill_info": None,
            }

            back_drawable = _field(bar, "glassDrawableBack")
            if back_drawable is not None:
                state["drawables"].append(back_drawable)

            self.states[key] = state
            self.create_title_pill(fragment, bar, state)
            self.layout_bar(bar)
            self.apply_state(state, self.api.current_strength())
            self.prune()
        except Exception as exc:
            self.log(
                "Glass Action Bar: skipped "
                + _class_name(fragment).rsplit(".", 1)[-1]
                + ": "
                + str(exc)
            )

    def layout_bar(self, bar: Any):
        if not self.active or bar is None:
            return
        state = self.states.get(self.api.identity(bar))
        if state is None:
            return

        pill = state.get("pill")
        if pill is None:
            return

        title = self.title_view(bar)
        if title is None:
            try:
                pill.setVisibility(self.View.GONE)
            except Exception:
                pass
            return

        width = self.text_width(title)
        if width <= 0:
            try:
                pill.setVisibility(self.View.GONE)
            except Exception:
                pass
            return

        bar_w = _int(bar.getWidth())
        bar_h = _int(bar.getHeight())
        if bar_w <= 0 or bar_h <= 0:
            return

        horizontal_padding = self.api.dp(16)
        pill_w = min(
            max(self.api.dp(54), width + horizontal_padding * 2),
            max(self.api.dp(54), bar_w - self.api.dp(132)),
        )
        pill_h = self.api.dp(46)

        try:
            text_start = _int(title.getTextStartX())
            center_x = _int(title.getLeft()) + text_start + width // 2
        except Exception:
            center_x = (_int(title.getLeft()) + _int(title.getRight())) // 2

        left = center_x - pill_w // 2
        min_left = self.api.dp(58)
        max_right = bar_w - self.api.dp(58)
        left = max(min_left, min(left, max_right - pill_w))

        occupy_status = bool(_field(bar, "occupyStatusBar"))
        status_h = 0
        if occupy_status:
            AndroidUtilities = self.api.find_class("org.telegram.messenger.AndroidUtilities")
            try:
                status_h = _int(AndroidUtilities.statusBarHeight)
            except Exception:
                status_h = 0

        content_h = max(0, bar_h - status_h)
        top = status_h + max(0, (content_h - pill_h) // 2)

        try:
            pill.setVisibility(self.View.VISIBLE)
            pill.measure(
                self.MeasureSpec.makeMeasureSpec(int(pill_w), self.MeasureSpec.EXACTLY),
                self.MeasureSpec.makeMeasureSpec(int(pill_h), self.MeasureSpec.EXACTLY),
            )
            pill.layout(int(left), int(top), int(left + pill_w), int(top + pill_h))
            pill.invalidate()
        except Exception as exc:
            self.log("Glass Action Bar: pill layout failed: " + str(exc))

    def apply_state(self, state: Dict[str, Any], strength: int):
        bar = state.get("bar")
        for drawable in list(state.get("drawables") or []):
            try:
                self.api.apply_glass_drawable(drawable, bar, int(strength), False)
            except Exception:
                pass

        info = state.get("pill_info")
        if info:
            try:
                self.api.apply_glass_drawable(
                    info.get("drawable"),
                    info.get("view"),
                    int(strength),
                    bool(info.get("prefer_light", False)),
                )
            except Exception:
                pass

        try:
            provider = state.get("provider")
            if provider is not None:
                provider.updateColors()
        except Exception:
            pass
        try:
            if bar is not None:
                bar.invalidate()
        except Exception:
            pass

    def update_strength(self, strength: int):
        for state in list(self.states.values()):
            self.apply_state(state, int(strength))

    def prune(self):
        if len(self.states) <= 192:
            return
        for key, state in list(self.states.items()):
            if len(self.states) <= 160:
                break
            bar = state.get("bar")
            detached = False
            try:
                detached = not bool(bar.isAttachedToWindow()) and bar.getParent() is None
            except Exception:
                pass
            if detached:
                self.states.pop(key, None)
        while len(self.states) > 192:
            self.states.pop(next(iter(self.states)), None)

    def install(self):
        BaseFragment = self.api.find_class("org.telegram.ui.ActionBar.BaseFragment")
        ActionBar = self.api.find_class("org.telegram.ui.ActionBar.ActionBar")
        if BaseFragment is None or ActionBar is None:
            raise RuntimeError("BaseFragment or ActionBar is unavailable")

        for method_name, hook in (
            ("createActionBar", _ActionBarCreatedHook(self)),
            ("setParentLayout", _ParentLayoutHook(self)),
            ("onResume", _ResumeHook(self)),
        ):
            try:
                self.api.hook_all_methods(BaseFragment, method_name, hook)
            except Exception as exc:
                self.log("Glass Action Bar: hook " + method_name + " failed: " + str(exc))

        try:
            self.api.hook_all_methods(ActionBar, "onLayout", _ActionBarLayoutHook(self))
        except Exception as exc:
            self.log("Glass Action Bar: ActionBar layout hook failed: " + str(exc))

    def shutdown(self):
        self.active = False
        self.states.clear()
        self.api.rebuild_current_fragment_views()


def on_load(api):
    global _API, _RUNTIME
    _API = api
    runtime = GlassActionBarRuntime(api)
    _RUNTIME = runtime
    runtime.install()
    api.register_strength_listener(runtime.update_strength)
    api.rebuild_current_fragment_views()
    api.log("Glass Action Bar 1.1 loaded")


def on_unload(api):
    global _API, _RUNTIME
    runtime = _RUNTIME
    if runtime is not None:
        runtime.shutdown()
    _RUNTIME = None
    _API = None
    api.log("Glass Action Bar unloaded")
