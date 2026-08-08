"""iOS-inspired expanded profile cover for Glassify."""

from typing import Any, Dict

from base_plugin import MethodHook
from hook_utils import get_private_field
from extera_utils.classes import Base, java_subclass, joverride
from java import jclass
from java.lang import Object

from android.graphics import Color
from android.graphics.drawable import GradientDrawable
from android.util import TypedValue
from android.view import Gravity, View, ViewGroup
from android.widget import FrameLayout, LinearLayout, TextView
from org.telegram.messenger import AndroidUtilities


GLASSIFY_EXTENSION = {
    "id": "profile_cover",
    "name": "Profile Cover",
    "version": "1.0",
    "api": 1,
}

_API = None
_STATES: Dict[int, Dict[str, Any]] = {}
_LISTENERS: Dict[int, Any] = {}
OnClickListener = jclass("android.view.View$OnClickListener")


def dp(value):
    return int(AndroidUtilities.dp(float(value)))


def ident(obj):
    try:
        return int(obj.hashCode())
    except Exception:
        return id(obj)


def field(obj, name, default=None):
    try:
        value = get_private_field(obj, name)
        return default if value is None else value
    except Exception:
        return default


def round_bg(color, radius, stroke=None):
    bg = GradientDrawable()
    bg.setColor(int(color))
    bg.setCornerRadius(float(dp(radius)))
    if stroke is not None:
        bg.setStroke(dp(1), int(stroke))
    return bg


def mark(view, name):
    try:
        view.setTag("glassify.profile_cover." + name)
    except Exception:
        pass


def ours(view):
    try:
        return str(view.getTag()).startswith("glassify.profile_cover.")
    except Exception:
        return False


def walk(view):
    if view is None or ours(view):
        return
    yield view
    try:
        count = int(view.getChildCount())
    except Exception:
        count = 0
    for i in range(count):
        try:
            child = view.getChildAt(i)
        except Exception:
            child = None
        if child is not None:
            yield from walk(child)


def description(view):
    parts = []
    try:
        text = view.getText()
        if text is not None:
            parts.append(str(text))
    except Exception:
        pass
    try:
        text = view.getContentDescription()
        if text is not None:
            parts.append(str(text))
    except Exception:
        pass
    return " ".join(parts).lower()


def native_click(root, action):
    words = {
        "edit": ("edit", "редакт", "измен"),
        "call": ("call", "звон", "позвон"),
        "video": ("video", "видео"),
        "mute": ("mute", "unmute", "уведом", "notification", "звук"),
        "search": ("search", "поиск"),
        "more": ("more", "ещё", "еще", "menu", "меню"),
    }.get(action, ())
    for view in walk(root):
        text = description(view)
        if text and any(word in text for word in words):
            try:
                if view.performClick():
                    return True
            except Exception:
                continue
    if _API is not None:
        _API.log("native profile action not found: " + action)
    return False


def go_back(fragment):
    try:
        fragment.finishFragment()
        return
    except Exception:
        pass
    try:
        fragment.onBackPressed()
    except Exception:
        pass


@java_subclass(Object, OnClickListener)
class ClickListener(Base):
    def __init__(self, callback):
        self.callback = callback

    @joverride()
    def onClick(self, view):
        try:
            self.callback()
        except Exception as exc:
            if _API is not None:
                _API.log("profile action failed: " + str(exc))


def on_click(view, callback):
    listener = ClickListener.new_instance(init_args=[callback])
    view.setOnClickListener(listener.java)
    _LISTENERS[ident(view)] = listener


def make_text(context, text, size, color, bold=False):
    view = TextView(context)
    view.setText(text)
    view.setTextColor(int(color))
    view.setTextSize(TypedValue.COMPLEX_UNIT_SP, float(size))
    view.setGravity(Gravity.CENTER)
    if bold:
        try:
            view.setTypeface(AndroidUtilities.bold())
        except Exception:
            pass
    return view


def action_item(context, root, icon, label, action):
    column = LinearLayout(context)
    column.setOrientation(LinearLayout.VERTICAL)
    column.setGravity(Gravity.CENTER_HORIZONTAL)
    mark(column, "action_" + action)

    circle = make_text(context, icon, 22, Color.WHITE)
    circle.setBackground(round_bg(0x59000000, 24, 0x24FFFFFF))
    circle.setClickable(True)
    circle.setFocusable(True)
    mark(circle, "action_button_" + action)
    on_click(circle, lambda: native_click(root, action))
    column.addView(circle, LinearLayout.LayoutParams(dp(48), dp(48)))

    caption = make_text(context, label, 10, 0xE8FFFFFF)
    caption.setPadding(0, dp(3), 0, 0)
    mark(caption, "action_label_" + action)
    column.addView(caption, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(18)))
    return column


def is_user_profile(fragment):
    try:
        dialog_id = int(fragment.getDialogId())
    except Exception:
        dialog_id = int(field(fragment, "dialogId", 0) or 0)
    return dialog_id > 0


def relative_top(fragment):
    avatar = field(fragment, "avatarImage")
    if avatar is None:
        return 1.0
    try:
        return float(field(avatar, "relativeTop", 1.0))
    except Exception:
        return 1.0


def force_expanded(fragment):
    if not is_user_profile(fragment):
        return
    list_view = field(fragment, "listView")
    if list_view is None:
        return
    try:
        list_view.scrollToPosition(0)
        list_view.requestLayout()
    except Exception:
        pass


def make_overlay(fragment, root):
    context = root.getContext()
    overlay = FrameLayout(context)
    mark(overlay, "overlay")
    overlay.setClickable(False)

    height = dp(340)
    root.addView(
        overlay,
        FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            height,
            Gravity.TOP,
        ),
    )

    scrim = View(context)
    mark(scrim, "scrim")
    scrim.setBackgroundColor(0x28000000)
    overlay.addView(
        scrim,
        FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            dp(145),
            Gravity.BOTTOM,
        ),
    )

    status = int(getattr(AndroidUtilities, "statusBarHeight", dp(24)))

    back = make_text(context, "‹", 35, 0xE8000000)
    back.setBackground(round_bg(0xBFFFFFFF, 22, 0x48FFFFFF))
    back.setClickable(True)
    back.setFocusable(True)
    mark(back, "back")
    lp = FrameLayout.LayoutParams(dp(44), dp(44), Gravity.TOP | Gravity.LEFT)
    lp.leftMargin = dp(12)
    lp.topMargin = status + dp(8)
    overlay.addView(back, lp)
    on_click(back, lambda: go_back(fragment))

    edit = make_text(context, "Edit", 13, 0xE8000000, True)
    edit.setBackground(round_bg(0xBFFFFFFF, 20, 0x48FFFFFF))
    edit.setClickable(True)
    edit.setFocusable(True)
    mark(edit, "edit")
    lp = FrameLayout.LayoutParams(dp(54), dp(40), Gravity.TOP | Gravity.RIGHT)
    lp.rightMargin = dp(12)
    lp.topMargin = status + dp(10)
    overlay.addView(edit, lp)
    on_click(edit, lambda: native_click(root, "edit"))

    try:
        edit.setVisibility(View.VISIBLE if bool(fragment.isSelf()) else View.GONE)
    except Exception:
        pass

    actions = LinearLayout(context)
    actions.setOrientation(LinearLayout.HORIZONTAL)
    actions.setGravity(Gravity.CENTER)
    actions.setPadding(dp(8), 0, dp(8), 0)
    mark(actions, "actions")
    lp = FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(70), Gravity.BOTTOM)
    lp.bottomMargin = dp(4)
    overlay.addView(actions, lp)

    for icon, label, action in (
        ("☎", "call", "call"),
        ("▣", "video", "video"),
        ("●", "mute", "mute"),
        ("⌕", "search", "search"),
        ("•••", "more", "more"),
    ):
        item = action_item(context, root, icon, label, action)
        actions.addView(item, LinearLayout.LayoutParams(0, dp(70), 1.0))

    try:
        overlay.bringToFront()
    except Exception:
        pass

    return {"overlay": overlay, "actions": actions, "root": root}


def decorate(fragment, root):
    if fragment is None or root is None or not is_user_profile(fragment):
        return

    key = ident(fragment)
    state = _STATES.get(key)
    if state is None:
        try:
            state = make_overlay(fragment, root)
            _STATES[key] = state
        except Exception as exc:
            if _API is not None:
                _API.log("Profile Cover UI failed: " + str(exc))
            return

    try:
        action_bar = fragment.getActionBar()
        back = field(action_bar, "backButtonImageView")
        if back is not None and "native_back_alpha" not in state:
            state["native_back"] = back
            state["native_back_alpha"] = float(back.getAlpha())
            back.setAlpha(0.0)
    except Exception:
        pass

    update_scroll_style(fragment)
    try:
        state["overlay"].bringToFront()
    except Exception:
        pass


def update_scroll_style(fragment):
    state = _STATES.get(ident(fragment))
    if state is None:
        return
    top = max(-1.0, min(1.0, relative_top(fragment)))
    expanded = max(0.0, top)

    try:
        state["actions"].setAlpha(expanded)
        state["actions"].setVisibility(View.VISIBLE if expanded > 0.04 else View.GONE)
    except Exception:
        pass

    for name, amount in (("title", 74), ("subtitle", 74)):
        view = field(fragment, name)
        if view is None:
            continue
        try:
            native_y = float(view.getTranslationY())
            last = state.get("last_" + name)
            if last is not None:
                native_y += float(last)
            offset = dp(amount) * expanded
            view.setTranslationY(native_y - offset)
            state["last_" + name] = offset
        except Exception:
            pass


class CreateHook(MethodHook):
    def after_hooked_method(self, param):
        fragment = param.thisObject
        root = param.getResult()
        if _API is None:
            return
        _API.schedule(lambda: force_expanded(fragment), 40)
        _API.schedule(lambda: decorate(fragment, root), 100)
        _API.schedule(lambda: decorate(fragment, root), 380)


class InfoHook(MethodHook):
    def after_hooked_method(self, param):
        if _API is None:
            return
        fragment = param.thisObject
        root = field(fragment, "fragmentView")
        if root is not None:
            _API.schedule(lambda: decorate(fragment, root), 50)


class ScrollHook(MethodHook):
    def after_hooked_method(self, param):
        update_scroll_style(param.thisObject)


def cleanup():
    for key, state in list(_STATES.items()):
        try:
            back = state.get("native_back")
            if back is not None:
                back.setAlpha(float(state.get("native_back_alpha", 1.0)))
        except Exception:
            pass
        try:
            overlay = state.get("overlay")
            parent = overlay.getParent() if overlay is not None else None
            if parent is not None:
                parent.removeView(overlay)
        except Exception:
            pass
        _STATES.pop(key, None)
    _LISTENERS.clear()


def on_load(api):
    global _API
    _API = api
    cls = api.find_class("org.telegram.ui.ProfileActivity2")
    if cls is None:
        raise RuntimeError("ProfileActivity2 not found")

    api.hook_all_methods(cls, "createView", CreateHook())
    api.hook_all_methods(cls, "updateScrollLayout", ScrollHook())
    info = InfoHook()
    for name in ("updateInfo", "updateAvatar", "onResume"):
        try:
            api.hook_all_methods(cls, name, info)
        except Exception:
            pass
    api.log("Profile Cover 1.0 loaded")


def on_unload(api):
    global _API
    cleanup()
    if api is not None:
        api.log("Profile Cover 1.0 unloaded")
    _API = None
