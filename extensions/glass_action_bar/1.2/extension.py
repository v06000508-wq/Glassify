GLASSIFY_EXTENSION = {
    "id": "glass_action_bar",
    "name": "Glass Action Bar",
    "version": "1.2",
    "api": 3,
}

_API = None
_RUNTIME = None

_TARGETS = (
    "org.telegram.ui.SettingsActivity",
    "org.telegram.ui.ProfileActivity",
    "org.telegram.ui.ProfileActivity2",
    "org.telegram.ui.ThemeActivity",
    "org.telegram.ui.PrivacySettingsActivity",
    "org.telegram.ui.NotificationsSettingsActivity",
    "org.telegram.ui.DataSettingsActivity",
    "org.telegram.ui.FiltersSetupActivity",
    "org.telegram.ui.SessionsActivity",
    "org.telegram.ui.LiteModeSettingsActivity",
    "org.telegram.ui.LanguageSelectActivity",
)

_EXCLUDED = (
    "ChatActivity", "DialogsActivity", "MainTabsActivity", "LaunchActivity",
    "PhotoViewer", "ArticleViewer", "SecretMediaViewer", "VoIPFragment",
)

_FACTORY_FIELDS = (
    "glassBackgroundDrawableFactory", "glassBackgroundDrawableFactoryFrosted",
    "iBlur3FactoryFrostedLiquidGlass", "iBlur3FactoryLiquidGlass",
    "iBlur3FactoryBlur", "blurredBackgroundDrawableViewFactory",
    "blurredBackgroundDrawableFactory",
)
_SOURCE_FIELDS = (
    "iBlur3SourceGlass", "iBlur3SourceGlassFrosted",
    "glassBackgroundSourceRenderNode", "glassBackgroundSourceFrostedRenderNode",
    "blurredBackgroundSource", "iBlur3Source",
)


def _field(obj: Any, name: str):
    if _API is None or obj is None:
        return None
    try:
        return _API.get_field(obj, name)
    except Exception:
        return None


def _int(value: Any, fallback: int = 0) -> int:
    try:
        return fallback if value is None else int(value)
    except Exception:
        return fallback


def _float(value: Any, fallback: float = 0.0) -> float:
    try:
        return fallback if value is None else float(value)
    except Exception:
        return fallback


def _name(obj: Any) -> str:
    try:
        return str(obj.getClass().getName())
    except Exception:
        return ""


class _CreatedHook(MethodHook):
    def __init__(self, runtime): self.runtime = runtime
    def after_hooked_method(self, param):
        try: bar = param.getResult()
        except Exception: bar = None
        self.runtime.decorate(param.thisObject, bar)


class _FragmentHook(MethodHook):
    def __init__(self, runtime): self.runtime = runtime
    def after_hooked_method(self, param):
        fragment = param.thisObject
        self.runtime.decorate(fragment)
        for delay in (0, 32, 96, 220):
            self.runtime.schedule(lambda f=fragment: self.runtime.decorate(f), delay)


class _LayoutHook(MethodHook):
    def __init__(self, runtime): self.runtime = runtime
    def after_hooked_method(self, param): self.runtime.layout(param.thisObject)


class _BarRefreshHook(MethodHook):
    def __init__(self, runtime): self.runtime = runtime
    def after_hooked_method(self, param):
        bar = param.thisObject
        self.runtime.schedule(lambda b=bar: self.runtime.layout(b), 0)


class GlassActionBarRuntime:
    def __init__(self, api):
        self.api = api
        self.active = True
        self.states: Dict[int, Dict[str, Any]] = {}
        self.View = api.find_class("android.view.View")
        self.ViewGroup = api.find_class("android.view.ViewGroup")
        self.MeasureSpec = api.find_class("android.view.View$MeasureSpec")
        self.AndroidUtilities = api.find_class("org.telegram.messenger.AndroidUtilities")
        self.Factory = api.find_class("org.telegram.ui.Components.blur3.BlurredBackgroundDrawableViewFactory")
        self.Provider = api.find_class("org.telegram.ui.Components.blur3.drawable.color.BlurredBackgroundColorProviderThemed")
        self.SourceColor = api.find_class("org.telegram.ui.Components.blur3.source.BlurredBackgroundSourceColor")
        self.Theme = api.find_class("org.telegram.ui.ActionBar.Theme")
        if any(x is None for x in (
            self.View, self.ViewGroup, self.MeasureSpec, self.AndroidUtilities,
            self.Factory, self.Provider, self.SourceColor, self.Theme,
        )):
            raise RuntimeError("required Android or Blur3 classes are unavailable")

    def log(self, value: Any): self.api.log(value)
    def schedule(self, callback, delay: int = 0):
        if self.active: self.api.schedule(callback, delay)

    def supported(self, fragment: Any) -> bool:
        short = _name(fragment).rsplit(".", 1)[-1]
        if not short or any(token in short for token in _EXCLUDED): return False
        try:
            if fragment.isInPreviewMode() or fragment.isInBubbleMode(): return False
        except Exception: pass
        return True

    def bar_for(self, fragment: Any, supplied: Any = None):
        if supplied is not None: return supplied
        bar = _field(fragment, "actionBar")
        if bar is not None: return bar
        try: return fragment.getActionBar()
        except Exception: return None

    def resources(self, fragment: Any):
        value = _field(fragment, "themeDelegate") or _field(fragment, "resourceProvider")
        if value is not None: return value
        try: return fragment.getResourceProvider()
        except Exception: return None

    def theme_color(self, fragment: Any, key: int) -> int:
        try: return int(self.Theme.getColor(int(key), self.resources(fragment)))
        except Exception:
            try: return int(self.Theme.getColor(int(key)))
            except Exception: return 0

    def resolve_factory(self, fragment: Any, bar: Any):
        for owner in (fragment, bar):
            for key in _FACTORY_FIELDS:
                value = _field(owner, key)
                if value is not None: return value, None
        for key in _SOURCE_FIELDS:
            source = _field(fragment, key)
            if source is not None:
                try: return self.Factory(source), None
                except Exception: pass
        try:
            source = self.SourceColor()
            color_key = getattr(self.Theme, "key_windowBackgroundWhite", getattr(self.Theme, "key_actionBarDefault"))
            source.setColor(self.theme_color(fragment, int(color_key)))
            return self.Factory(source), source
        except Exception as exc:
            self.log("Glass Action Bar fallback unavailable: " + str(exc))
            return None, None

    def refresh_source(self, state: Dict[str, Any]):
        source = state.get("fallback_source")
        if source is None: return
        try:
            key = getattr(self.Theme, "key_windowBackgroundWhite", getattr(self.Theme, "key_actionBarDefault"))
            source.setColor(self.theme_color(state.get("fragment"), int(key)))
        except Exception: pass

    def new_surface(self, state: Dict[str, Any], role: str, radius: float, alpha: float, light: bool):
        bar, fragment, factory = state.get("bar"), state.get("fragment"), state.get("factory")
        if bar is None or fragment is None or factory is None: return None
        view = self.View(bar.getContext())
        view.setClickable(False); view.setFocusable(False)
        try: view.setImportantForAccessibility(self.View.IMPORTANT_FOR_ACCESSIBILITY_NO)
        except Exception: pass
        bar.addView(view, 0, self.ViewGroup.LayoutParams(self.api.dp(1), self.api.dp(1)))
        try:
            provider = self.Provider(self.resources(fragment), int(getattr(self.Theme, "key_actionBarDefault")), float(alpha))
            drawable = factory.create(view, provider)
            drawable.setRadius(float(self.api.dp(radius)))
            drawable.setPadding(0 if light else self.api.dp(1))
            view.setBackground(drawable)
            info = {"role": role, "view": view, "drawable": drawable, "provider": provider, "prefer_light": light}
            state.setdefault("surfaces", []).append(info)
            self.api.apply_glass_drawable(drawable, view, self.api.current_strength(), light)
            return info
        except Exception as exc:
            try: bar.removeView(view)
            except Exception: pass
            self.log("Glass Action Bar surface failed: " + str(exc))
            return None

    def ensure_surfaces(self, state: Dict[str, Any]):
        if state.get("title") is None: state["title"] = self.new_surface(state, "title", 22, 0.74, False)
        if not state.get("stock_back") and state.get("back") is None:
            state["back"] = self.new_surface(state, "back", 21, 0.72, True)

    def visible(self, view: Any) -> bool:
        if view is None: return False
        try:
            if view.getVisibility() != self.View.VISIBLE: return False
        except Exception: pass
        try:
            if _float(view.getAlpha(), 1.0) <= 0.08: return False
        except Exception: pass
        return True

    def text(self, view: Any) -> str:
        try: value = view.getText()
        except Exception: value = None
        return "" if value is None else str(value).strip()

    def text_width(self, view: Any) -> int:
        text = self.text(view)
        if not text: return 0
        paints = []
        try: paints.append(_field(view, "textPaint"))
        except Exception: pass
        try: paints.append(view.getTextPaint())
        except Exception: pass
        try: paints.append(view.getPaint())
        except Exception: pass
        for paint in paints:
            if paint is None: continue
            try:
                width = _int(paint.measureText(text))
                if width > 0: return width
            except Exception: pass
        try: return max(0, _int(view.getTextWidth()))
        except Exception: return 0

    def title_views(self, bar: Any):
        titles = []
        array = _field(bar, "titleTextView")
        if array is not None:
            for i in (0, 1):
                try: view = array[i]
                except Exception:
                    try: view = array.get(i)
                    except Exception: view = None
                if self.visible(view) and self.text(view): titles.append(view)
        if len(titles) > 1:
            titles.sort(key=lambda v: _float(v.getAlpha(), 1.0), reverse=True)
            titles = titles[:1]
        subtitle = _field(bar, "subtitleTextView")
        if self.visible(subtitle) and self.text(subtitle): titles.append(subtitle)
        return titles

    def relative(self, view: Any, bar: Any):
        x = y = 0.0; current = view
        for _ in range(8):
            if current is bar: return int(x), int(y)
            try:
                x += _float(current.getLeft()) + _float(current.getTranslationX())
                y += _float(current.getTop()) + _float(current.getTranslationY())
                current = current.getParent()
            except Exception: break
            if current is None: break
        try: return _int(view.getLeft()), _int(view.getTop())
        except Exception: return 0, 0

    def search_mode(self, bar: Any) -> bool:
        try:
            if bar.isSearchFieldVisible(): return True
        except Exception: pass
        return bool(_field(bar, "isSearchFieldVisible")) or bool(_field(bar, "actionModeVisible"))

    def back_view(self, bar: Any):
        view = _field(bar, "backButtonImageView")
        return view if self.visible(view) else None

    def menu_children(self, bar: Any):
        menu = _field(bar, "menu")
        if not self.visible(menu): return []
        result = []
        try: count = _int(menu.getChildCount())
        except Exception: count = 0
        for i in range(count):
            try: child = menu.getChildAt(i)
            except Exception: child = None
            if child is not None and self.visible(child): result.append(child)
        return result

    def show(self, info: Any, left: int, top: int, width: int, height: int):
        if not info or width <= 0 or height <= 0: return
        view = info.get("view")
        try:
            view.setVisibility(self.View.VISIBLE)
            view.measure(self.MeasureSpec.makeMeasureSpec(width, self.MeasureSpec.EXACTLY), self.MeasureSpec.makeMeasureSpec(height, self.MeasureSpec.EXACTLY))
            view.layout(left, top, left + width, top + height)
            view.invalidate()
        except Exception: pass

    def hide(self, info: Any):
        if not info: return
        try: info.get("view").setVisibility(self.View.GONE)
        except Exception: pass

    def title_bounds(self, bar: Any):
        views = self.title_views(bar)
        if not views: return None
        left = right = None
        for view in views:
            width = self.text_width(view)
            if width <= 0: continue
            x, _ = self.relative(view, bar)
            try: start = _int(view.getTextStartX())
            except Exception:
                try: start = _int(view.getPaddingLeft())
                except Exception: start = 0
            row_left, row_right = x + start, x + start + width
            left = row_left if left is None else min(left, row_left)
            right = row_right if right is None else max(right, row_right)
        if left is None or right is None or right <= left: return None
        return int(left), int(right), len(views) > 1

    def guards(self, bar: Any, width: int):
        left, right = self.api.dp(8), width - self.api.dp(8)
        back = self.back_view(bar)
        if back is not None:
            x, _ = self.relative(back, bar)
            left = max(left, x + max(_int(back.getWidth()), _int(back.getMeasuredWidth())) + self.api.dp(4))
        children = self.menu_children(bar)
        if children:
            first = min(self.relative(child, bar)[0] for child in children)
            right = min(right, first - self.api.dp(4))
        return left, right

    def layout_title(self, state: Dict[str, Any]):
        bar, info = state.get("bar"), state.get("title")
        if bar is None or info is None: return
        if self.search_mode(bar): self.hide(info); return
        bounds = self.title_bounds(bar)
        if bounds is None: self.hide(info); return
        bar_w, bar_h = _int(bar.getWidth()), _int(bar.getHeight())
        if bar_w <= 0 or bar_h <= 0: return
        text_left, text_right, subtitle = bounds
        left, right = text_left - self.api.dp(14), text_right + self.api.dp(14)
        guard_left, guard_right = self.guards(bar, bar_w)
        left, right = max(left, guard_left), min(right, guard_right)
        if right - left < self.api.dp(38): self.hide(info); return
        height = self.api.dp(48 if subtitle else 42)
        status = _int(self.AndroidUtilities.statusBarHeight) if bool(_field(bar, "occupyStatusBar")) else 0
        top = status + max(0, (bar_h - status - height) // 2)
        self.show(info, left, top, right - left, height)

    def layout_back(self, state: Dict[str, Any]):
        info, bar = state.get("back"), state.get("bar")
        if info is None or bar is None: return
        back = self.back_view(bar)
        if back is None: self.hide(info); return
        x, y = self.relative(back, bar)
        w, h = max(_int(back.getWidth()), _int(back.getMeasuredWidth())), max(_int(back.getHeight()), _int(back.getMeasuredHeight()))
        size = self.api.dp(42)
        self.show(info, x + (w - size) // 2, y + (h - size) // 2, size, size)

    def menu_surface(self, state: Dict[str, Any], child: Any):
        key = self.api.identity(child); items = state.setdefault("menu", {})
        info = items.get(key)
        if info is None:
            info = self.new_surface(state, "menu", 21, 0.72, True)
            if info is not None: items[key] = info
        return info

    def layout_menu(self, state: Dict[str, Any]):
        bar = state.get("bar"); active = set()
        if bar is None or self.search_mode(bar):
            for info in state.get("menu", {}).values(): self.hide(info)
            return
        for child in self.menu_children(bar):
            key = self.api.identity(child); active.add(key); info = self.menu_surface(state, child)
            if info is None: continue
            x, y = self.relative(child, bar)
            w, h = max(_int(child.getWidth()), _int(child.getMeasuredWidth())), max(_int(child.getHeight()), _int(child.getMeasuredHeight()))
            if w <= 0 or h <= 0: self.hide(info); continue
            height = self.api.dp(40)
            width = height if w <= self.api.dp(62) else min(max(self.api.dp(52), w - self.api.dp(8)), self.api.dp(112))
            self.show(info, x + (w - width) // 2, y + (h - height) // 2, width, height)
        for key, info in state.get("menu", {}).items():
            if key not in active: self.hide(info)

    def apply(self, state: Dict[str, Any], strength: int):
        self.refresh_source(state)
        for info in state.get("surfaces", []):
            try:
                provider = info.get("provider")
                if provider is not None: provider.updateColors()
                self.api.apply_glass_drawable(info.get("drawable"), info.get("view"), int(strength), bool(info.get("prefer_light")))
            except Exception: pass

    def decorate(self, fragment: Any, supplied: Any = None):
        if not self.active or not self.supported(fragment): return
        bar = self.bar_for(fragment, supplied)
        if bar is None: return
        key = self.api.identity(bar); state = self.states.get(key)
        if state is not None:
            state["fragment"] = fragment; self.layout(bar); return
        factory, source = self.resolve_factory(fragment, bar)
        if factory is None: return
        try: factory.setLiquidGlassEffectAllowed(True)
        except Exception: pass
        try:
            stock_glass = bool(_field(bar, "glassMode"))
            state = {"fragment": fragment, "bar": bar, "factory": factory, "fallback_source": source, "stock_back": stock_glass, "surfaces": [], "title": None, "back": None, "menu": {}}
            self.states[key] = state
            try: bar.setBackground(None); bar.setClipChildren(False); bar.setClipToPadding(False)
            except Exception: pass
            if stock_glass:
                try:
                    if not self.api.set_field(bar, "glassOnlyBack", True): bar.setGlassOnlyBack()
                except Exception: pass
            self.ensure_surfaces(state); self.layout(bar); self.apply(state, self.api.current_strength()); self.prune()
        except Exception as exc:
            self.states.pop(key, None); self.log("Glass Action Bar skipped " + _name(fragment) + ": " + str(exc))

    def layout(self, bar: Any):
        if not self.active or bar is None: return
        state = self.states.get(self.api.identity(bar))
        if state is None: return
        self.ensure_surfaces(state); self.layout_back(state); self.layout_menu(state); self.layout_title(state)

    def update_strength(self, value: int):
        for state in list(self.states.values()): self.apply(state, value)

    def prune(self):
        if len(self.states) <= 192: return
        for key, state in list(self.states.items()):
            if len(self.states) <= 160: break
            bar = state.get("bar")
            try: detached = not bar.isAttachedToWindow() and bar.getParent() is None
            except Exception: detached = False
            if detached: self.states.pop(key, None)

    def hook(self, clazz: Any, names: Any, hook: Any):
        if clazz is None: return
        for name in names:
            try: self.api.hook_all_methods(clazz, name, hook)
            except Exception: pass

    def install(self):
        BaseFragment = self.api.find_class("org.telegram.ui.ActionBar.BaseFragment")
        ActionBar = self.api.find_class("org.telegram.ui.ActionBar.ActionBar")
        if BaseFragment is None or ActionBar is None: raise RuntimeError("BaseFragment or ActionBar unavailable")
        self.hook(BaseFragment, ("createActionBar",), _CreatedHook(self))
        self.hook(BaseFragment, ("setParentLayout", "onResume"), _FragmentHook(self))
        self.hook(ActionBar, ("onLayout",), _LayoutHook(self))
        self.hook(ActionBar, ("setTitle", "setSubtitle", "setBackButtonImage", "setBackButtonDrawable", "createMenu", "openSearchField", "closeSearchField"), _BarRefreshHook(self))
        target_hook = _FragmentHook(self)
        for class_name in _TARGETS:
            clazz = self.api.find_class(class_name)
            self.hook(clazz, ("createView", "onResume", "onTransitionAnimationEnd"), target_hook)

    def shutdown(self):
        self.active = False; self.states.clear(); self.api.rebuild_current_fragment_views()


def on_load(api):
    global _API, _RUNTIME
    _API = api
    _RUNTIME = GlassActionBarRuntime(api)
    _RUNTIME.install()
    api.register_strength_listener(_RUNTIME.update_strength)
    api.rebuild_current_fragment_views()
    api.log("Glass Action Bar 1.2 loaded")


def on_unload(api):
    global _API, _RUNTIME
    if _RUNTIME is not None: _RUNTIME.shutdown()
    _RUNTIME = None; _API = None
    api.log("Glass Action Bar unloaded")
