GLASSIFY_EXTENSION = {
    "id": "glass_action_bar",
    "name": "Glass Action Bar",
    "version": "1.0",
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


class GlassActionBarRuntime:
    def __init__(self, api):
        self.api = api
        self.active = True
        self.states: Dict[int, Dict[str, Any]] = {}
        self.Factory = api.find_class(
            "org.telegram.ui.Components.blur3.BlurredBackgroundDrawableViewFactory"
        )
        self.Provider = api.find_class(
            "org.telegram.ui.Components.blur3.drawable.color.BlurredBackgroundColorProviderThemed"
        )
        self.Theme = api.find_class("org.telegram.ui.ActionBar.Theme")
        if self.Factory is None or self.Provider is None or self.Theme is None:
            raise RuntimeError("required Blur3 classes are unavailable")

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

    def already_glass(self, bar: Any) -> bool:
        try:
            return bool(_field(bar, "glassMode"))
        except Exception:
            return False

    def decorate(self, fragment: Any, supplied_bar: Any = None):
        if not self.active or not self.supported(fragment):
            return

        bar = self.action_bar(fragment, supplied_bar)
        if bar is None:
            return

        key = self.api.identity(bar)
        existing = self.states.get(key)
        if existing is not None:
            self.apply_state(existing, self.api.current_strength())
            return

        # Do not stack another material over screens Telegram already renders
        # with its own ActionBar glass mode.
        if self.already_glass(bar):
            return

        factory = self.resolve_factory(fragment, bar)
        if factory is None:
            return

        try:
            color_key = getattr(self.Theme, "key_actionBarDefault")
            provider = self.Provider(
                self.resources_provider(fragment),
                int(color_key),
                0.82,
            )
            bar.setupGlass(factory, provider)

            state = {
                "fragment": fragment,
                "bar": bar,
                "factory": factory,
                "provider": provider,
                "drawables": [],
            }
            for field_name in ("glassDrawable", "glassDrawableBack", "glassDrawableMenu"):
                drawable = _field(bar, field_name)
                if drawable is not None:
                    state["drawables"].append(drawable)

            self.states[key] = state
            self.apply_state(state, self.api.current_strength())
            try:
                bar.invalidate()
            except Exception:
                pass
            self.prune()
        except Exception as exc:
            self.log(
                "Glass Action Bar: skipped "
                + _class_name(fragment).rsplit(".", 1)[-1]
                + ": "
                + str(exc)
            )

    def apply_state(self, state: Dict[str, Any], strength: int):
        bar = state.get("bar")
        stale = True
        for drawable in list(state.get("drawables") or []):
            if self.api.apply_glass_drawable(drawable, bar, int(strength), False):
                stale = False
        if stale and state.get("drawables"):
            return
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
        if BaseFragment is None:
            raise RuntimeError("BaseFragment is unavailable")

        for method_name, hook in (
            ("createActionBar", _ActionBarCreatedHook(self)),
            ("setParentLayout", _ParentLayoutHook(self)),
            ("onResume", _ResumeHook(self)),
        ):
            try:
                self.api.hook_all_methods(BaseFragment, method_name, hook)
            except Exception as exc:
                self.log("Glass Action Bar: hook " + method_name + " failed: " + str(exc))

    def shutdown(self):
        self.active = False
        self.states.clear()
        # setupGlass changes private ActionBar drawing state, so rebuilding the
        # visible fragment is the safest exact restoration without touching Core.
        self.api.rebuild_current_fragment_views()


def on_load(api):
    global _API, _RUNTIME
    _API = api
    runtime = GlassActionBarRuntime(api)
    _RUNTIME = runtime
    runtime.install()
    api.register_strength_listener(runtime.update_strength)
    api.rebuild_current_fragment_views()
    api.log("Glass Action Bar 1.0 loaded")


def on_unload(api):
    global _API, _RUNTIME
    runtime = _RUNTIME
    if runtime is not None:
        runtime.shutdown()
    _RUNTIME = None
    _API = None
    api.log("Glass Action Bar unloaded")
