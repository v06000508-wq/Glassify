package glassify.kyant;

import android.animation.StateListAnimator;
import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ColorFilter;
import android.graphics.Matrix;
import android.graphics.Outline;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.RenderNode;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.RippleDrawable;
import android.graphics.drawable.ShapeDrawable;
import android.os.Build;
import android.util.Log;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewOutlineProvider;
import android.view.animation.AnimationUtils;
import android.view.animation.PathInterpolator;
import android.widget.TextView;

import androidx.dynamicanimation.animation.FloatValueHolder;
import androidx.dynamicanimation.animation.SpringAnimation;
import androidx.dynamicanimation.animation.SpringForce;

import java.lang.ref.WeakReference;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import java.util.WeakHashMap;

import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.XposedBridge;

final class ReleaseButtons {
    private static final String UI = "org.telegram.ui.";
    private static final String TAG = "GlassifyLiquidButtons";
    private static final String SAVE = "kyant.release.canvas";
    private static final String HEADER = "kyant.release.header";
    private static final String SCOPE = "kyant.release.backdrop";
    private static final PathInterpolator HIGHLIGHT_IN = new PathInterpolator(0f, 0f, .58f, 1f);
    private static final PathInterpolator HIGHLIGHT_OUT = new PathInterpolator(.42f, 0f, .58f, 1f);
    private static final int DAY = 0xFFF7F8FA;
    private static final int NIGHT = 0xFF202027;
    private static final ViewOutlineProvider ROUND_FAB_OUTLINE = new ViewOutlineProvider() {
        @Override public void getOutline(View view, Outline outline) {
            outline.setOval(0, 0, view.getWidth(), view.getHeight());
        }
    };
    private static final ArrayList<XC_MethodHook.Unhook> hooks = new ArrayList<>();
    private static final WeakHashMap<View, Button> buttons = new WeakHashMap<>();
    private static final WeakHashMap<View, WeakReference<View>> touchTargets = new WeakHashMap<>();
    private static final WeakHashMap<View, Header> headers = new WeakHashMap<>();
    private static final WeakHashMap<Object, Button> profileActions = new WeakHashMap<>();
    private static final WeakHashMap<View, Button> profileGestures = new WeakHashMap<>();
    private static final WeakHashMap<Object, Boolean> profileBars = new WeakHashMap<>();
    private static final WeakHashMap<Object, Boolean> profileMenus = new WeakHashMap<>();
    private static final WeakHashMap<View, ProfileBackdrop> profileBackdrops = new WeakHashMap<>();
    private static final WeakHashMap<Drawable, Boolean> replacedRipples = new WeakHashMap<>();
    private static final WeakHashMap<View, Boolean> giftSheets = new WeakHashMap<>();
    private static final WeakHashMap<View, Button> panels = new WeakHashMap<>();
    private static final WeakHashMap<Drawable, CaptureMargin> captureMargins = new WeakHashMap<>();
    private static final WeakHashMap<ViewGroup, Clip> clips = new WeakHashMap<>();
    private static final WeakHashMap<View, QrState> qrStates = new WeakHashMap<>();
    private static final WeakHashMap<Object, WeakReference<Object>> dialogsCapture = new WeakHashMap<>();

    private static Class<?> drawableClass, fabClass, dialogsClass, contactsClass, mainTabsClass, qrViewClass, scannerClass;
    private static Class<?> renderNodeSourceClass;
    private static Class<?> profileClass;
    private static Field fabSub, fabTint, fabStockGlass, dialogsFactory, messageFab, storyFab, dialogsNoise;
    private static Field contactsFab, roundBackground, pageDownInner, factoryEngine;
    private static Method baseGlass, getFragmentView, createCapture, setOutset, engineInvalidate, unregister;
    private static Method syncGlass, syncTheme, resolveSource, getSource, sourceDraw, offsetX, offsetY, paddedBounds, darkTheme;
    private static Method glassSettings, getOutsetX, getOutsetY;
    private static Field blurEnabled, liquidEnabled;
    private static Field backgroundColor, drawableProps, drawableRadii, ctaBackground, pinnedBackground, pinnedColor;
    private static Field ctaFilled;
    private static Field simpleActionBar, profileTop, profileActionsView, profileOtherItem, profileButtonColor;
    private static Method drawProfileTop;
    private static Method themeColor;
    private static int dialogBackgroundKey, giftAccentKey;
    private static Method rectangleInParent;
    private static Field[] qrRects, scannerRects;
    private static Field qrBlur, scannerBlur, scannerCamera, scannerGallery;
    private static Method qrHasBlur, qrDrawBlur, qrDrawPicture, qrTarget, scannerReady;
    private static QrState activeQr;
    private static ActiveGlass activeGlass;
    private static Header activeHeader;
    private static Drawable skipFabBackdrop;
    private static boolean profileTouch;
    private static boolean logged;
    private static int strength = 50;
    private static GlassSurface.Optics optics = GlassSurface.Optics.fromStrength(strength);

    static void setStrength(int value) {
        value = Math.max(1, Math.min(100, value));
        if (value == strength) return;
        strength = value;
        optics = GlassSurface.Optics.fromStrength(value);
        buttons.values().forEach(Button::invalidateFrame);
        headers.keySet().forEach(View::postInvalidateOnAnimation);
        panels.keySet().forEach(View::postInvalidateOnAnimation);
        profileActions.values().forEach(Button::invalidateFrame);
        qrStates.keySet().forEach(View::postInvalidateOnAnimation);
        LiquidDialogs.invalidate();
    }

    static void load(Context context) throws ReflectiveOperationException {
        if (Build.VERSION.SDK_INT < 33) throw new IllegalStateException("Liquid Buttons requires Android 13+");
        if (!hooks.isEmpty()) return;
        ClassLoader loader = context.getClassLoader();
        try {
            resolve(loader);
            installFloating();
            installPageDown();
            installHeaders(loader);
            installQr();
            installConnect(loader);
            installTouch();
            LiquidDialogs.install(loader);
            hook(drawableClass, "draw", new UiHook() {
                @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                    if (skipFabBackdrop == p.thisObject && ((Canvas) p.args[0]).isHardwareAccelerated()) {
                        p.setResult(null);
                        return;
                    }
                    ActiveGlass scope = activeGlass;
                    if (scope == null || (scope.drawable != null && scope.drawable != p.thisObject)) {
                        scope = activeHeader == null ? null : activeHeader.find(p.thisObject);
                    }
                    if (scope == null) return;
                    Canvas canvas = (Canvas) p.args[0];
                    Drawable drawable = (Drawable) p.thisObject;
                    Button button = scope.button;
                    if (!canvas.isHardwareAccelerated()) return;
                    if (!glassActive()) {
                        releaseCaptureMargin(drawable);
                        return;
                    }
                    if (!button.sample.resolve(drawable)) return;
                    View owner = button.view.get();
                    ProfileBackdrop profile = button.profileAction && owner != null ? profileBackdrops.get(owner) : null;
                    if (profile == null && button.sample.source != null) extendCapture(drawable, button);
                    RectF bounds = button.bounds;
                    bounds.set(button.sample.padded);
                    if (bounds.isEmpty()) return;
                    int save = canvas.save();
                    try {
                        if (scope.moveGlass) button.move(canvas, bounds);
                        boolean dark = dark();
                        int color = profile != null ? profile.tint(base(dark)) : button.sample.color;
                        drawLiquid(canvas, button, profile != null ? profile : button.sample, color == 0 ? base(dark) : color,
                                dark, drawable.getAlpha() / 255f, bounds, button.sample.radii);
                        p.setResult(null);
                    } finally {
                        button.sample.source = null;
                        canvas.restoreToCount(save);
                    }
                }
            }, Canvas.class);

            Object current = loader.loadClass(UI + "LaunchActivity").getMethod("getLastFragment").invoke(null);
            if (mainTabsClass.isInstance(current)) {
                current = mainTabsClass.getMethod("getCurrentVisibleFragment").invoke(current);
            }
            bindFabs(current);
            markProfileBar(current);
        } catch (ReflectiveOperationException | RuntimeException | LinkageError error) {
            unload();
            throw error;
        }
    }

    static void unload() {
        for (XC_MethodHook.Unhook hook : hooks) hook.unhook();
        hooks.clear();
        LiquidDialogs.unload();
        buttons.forEach((view, button) -> {
            button.restore(view);
            view.invalidate();
        });
        clips.forEach((view, clip) -> {
            view.setClipChildren(clip.children);
            view.setClipToPadding(clip.padding);
        });
        clips.clear();
        buttons.clear();
        touchTargets.clear();
        headers.keySet().forEach(View::invalidate);
        headers.clear();
        profileActions.values().forEach(button -> {
            View view = button.view.get();
            if (view != null) {
                button.restore(view);
                view.invalidate();
            } else {
                button.cancelAnimations();
            }
        });
        profileActions.clear();
        profileGestures.clear();
        profileBars.clear();
        profileMenus.clear();
        profileBackdrops.clear();
        replacedRipples.clear();
        giftSheets.clear();
        panels.keySet().forEach(View::invalidate);
        panels.clear();
        captureMargins.forEach(ReleaseButtons::restoreCaptureMargin);
        captureMargins.clear();
        qrStates.values().forEach(QrState::cancel);
        qrStates.keySet().forEach(View::invalidate);
        qrStates.clear();
        dialogsCapture.clear();
        activeQr = null;
        activeGlass = null;
        activeHeader = null;
        skipFabBackdrop = null;
        profileTouch = false;
        logged = false;
    }

    private static void resolve(ClassLoader loader) throws ReflectiveOperationException {
        String component = UI + "Components.";
        drawableClass = loader.loadClass(component + "blur3.drawable.BlurredBackgroundDrawable");
        Class<?> factory = loader.loadClass(component + "blur3.BlurredBackgroundDrawableViewFactory");
        Class<?> engine = loader.loadClass("org.telegram.utils.glass.GlassEngine");
        Class<?> base = loader.loadClass(UI + "ActionBar.BaseFragment");
        dialogsClass = loader.loadClass(UI + "DialogsActivity");
        contactsClass = loader.loadClass(UI + "ContactsActivity");
        mainTabsClass = loader.loadClass(UI + "MainTabsActivity");
        fabClass = loader.loadClass(component + "FragmentFloatingButton");
        Class<?> inner = loader.loadClass(component + "chat.buttons.ChatActivityBlurredRoundButton");
        Class<?> outer = loader.loadClass(component + "chat.buttons.ChatActivityBlurredRoundPageDownButton");

        fabSub = field(fabClass, "isSubButton");
        fabTint = field(fabClass, "themedBackgroundColor");
        fabStockGlass = field(fabClass, "iBlur3Background");
        dialogsFactory = field(dialogsClass, "iBlur3FactoryLiquidGlass");
        dialogsNoise = field(dialogsClass, "scrollableViewNoiseSuppressor");
        messageFab = field(dialogsClass, "floatingButton3");
        storyFab = field(dialogsClass, "floatingButtonStories");
        contactsFab = field(contactsClass, "floatingButton");
        baseGlass = method(base, "getBaseSimpleGlass");
        getFragmentView = base.getMethod("getFragmentView");
        factoryEngine = field(factory, "engine");
        createCapture = factory.getMethod("create", View.class);
        setOutset = drawableClass.getMethod("setOutset", int.class, int.class);
        getOutsetX = drawableClass.getMethod("getOutsetX");
        getOutsetY = drawableClass.getMethod("getOutsetY");
        engineInvalidate = engine.getMethod("invalidate");
        glassSettings = engine.getMethod("getCurrentGlassSettings");
        blurEnabled = glassSettings.getReturnType().getField("isBlurEnabled");
        liquidEnabled = glassSettings.getReturnType().getField("isLiquidGlassEnabled");
        unregister = engine.getMethod("unregisterDrawable", loader.loadClass("org.telegram.utils.glass.GlassDrawable"));
        rectangleInParent = loader.loadClass(component + "chat.ViewPositionWatcher")
                .getMethod("computeRectInParent", View.class, View.class, RectF.class);

        roundBackground = field(inner, "backgroundDrawable");
        pageDownInner = field(outer, "buttonView");
        syncGlass = method(drawableClass, "checkGlassSettings");
        syncTheme = method(drawableClass, "checkThemeColors");
        resolveSource = drawableClass.getMethod("shouldHaveDisplayList");
        getSource = drawableClass.getMethod("getUnwrappedSource");
        renderNodeSourceClass = loader.loadClass("org.telegram.utils.glass.source.GlassSourceRenderNode");
        sourceDraw = loader.loadClass("org.telegram.utils.glass.source.GlassSource")
                .getMethod("draw", Canvas.class, float.class, float.class, float.class, float.class);
        offsetX = drawableClass.getMethod("getSourceOffsetX");
        offsetY = drawableClass.getMethod("getSourceOffsetY");
        paddedBounds = drawableClass.getMethod("getBoundsWithPaddingInset", Rect.class);
        backgroundColor = field(drawableClass, "backgroundColor");
        drawableProps = field(drawableClass, "boundProps");
        drawableRadii = field(drawableProps.getType(), "radii");
        darkTheme = loader.loadClass(UI + "ActionBar.Theme").getMethod("isCurrentThemeDark");

        qrViewClass = loader.loadClass(UI + "QrShare.QrShareView");
        scannerClass = loader.loadClass(UI + "QrShare.QrScanOverlay");
        qrRects = fields(qrViewClass, "closeRect", "scanRect", "shareRect", "saveRect");
        scannerRects = fields(scannerClass, "closeRect", "galleryRect");
        qrHasBlur = method(qrViewClass, "hasBlur", Canvas.class);
        qrDrawBlur = method(qrViewClass, "drawBlurNode", Canvas.class, Object.class);
        qrDrawPicture = method(qrViewClass, "drawBlurStandIn", Canvas.class);
        qrTarget = method(qrViewClass, "rippleTarget", float.class, float.class);
        qrBlur = field(qrViewClass, "blurNode");
        scannerBlur = field(scannerClass, "blurNode");
        scannerCamera = field(scannerClass, "cameraView");
        scannerGallery = field(scannerClass, "onGallery");
        scannerReady = method(scannerClass, "blurReady", Canvas.class);
    }

    private static void installFloating() throws ReflectiveOperationException {
        UiHook bind = new UiHook() {
            @Override void after(MethodHookParam p) throws ReflectiveOperationException {
                if (!p.hasThrowable()) bindFabs(p.thisObject);
            }
        };
        for (Class<?> owner : new Class<?>[]{dialogsClass, contactsClass}) {
            hook(owner, "createView", bind, Context.class);
            hook(owner, "onResume", bind);
            hook(owner, "onFragmentDestroy", new UiHook() {
                @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                    if (dialogsClass.isInstance(p.thisObject)) {
                        dialogsCapture.remove(dialogsNoise.get(p.thisObject));
                        forget((View) messageFab.get(p.thisObject));
                        forget((View) storyFab.get(p.thisObject));
                    } else {
                        forget((View) contactsFab.get(p.thisObject));
                    }
                }
            });
        }
        hook(fabClass, "updateColors", new UiHook() {
            @Override void after(MethodHookParam p) {
                View view = (View) p.thisObject;
                Button state = buttons.get(view);
                if (state != null) state.useFace(view);
            }
        });
        hook(fabClass, "draw", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                View view = (View) p.thisObject;
                Button state = buttons.get(view);
                Canvas canvas = (Canvas) p.args[0];
                if (state == null || !canvas.isHardwareAccelerated()) return;
                state.freeClipping(view, 3);
                state.watchPress(view);
                boolean customFace = state.face != null && view.getBackground() == state.face && glassActive();
                if (!fabSub.getBoolean(view)) state.setRoundFabOutline(view, customFace);
                if (customFace) {
                    p.setObjectExtra(SCOPE, new Object[]{skipFabBackdrop});
                    skipFabBackdrop = (Drawable) fabStockGlass.get(view);
                }
                p.setObjectExtra(SAVE, canvas.save());
                state.layout.set(0, 0, view.getWidth(), view.getHeight());
                state.move(canvas, state.layout);
            }
            @Override void after(MethodHookParam p) {
                if (p.getObjectExtra(SCOPE) instanceof Object[] prior) skipFabBackdrop = (Drawable) prior[0];
                restore(p);
            }
        }, Canvas.class);
        hook(dialogsNoise.getType(), "setupRenderNodes", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                WeakReference<Object> ref = dialogsCapture.get(p.thisObject);
                Object fragment = ref == null ? null : ref.get();
                View root = fragment == null ? null : (View) getFragmentView.invoke(fragment);
                if (root == null) return;
                RectF union = new RectF();
                includeFab(union, root, (View) messageFab.get(fragment));
                includeFab(union, root, (View) storyFab.get(fragment));
                if (union.isEmpty()) return;
                List<?> original = (List<?>) p.args[0];
                int count = (int) p.args[1];
                if (count < 1 || count > original.size()) return;
                List<RectF> adjusted = new ArrayList<>();
                for (int i = 0; i < count; i++) adjusted.add((RectF) original.get(i));
                if (count > 1) {
                    union.union(adjusted.get(1));
                    adjusted.set(1, union);
                } else {
                    adjusted.add(union);
                }
                p.args[0] = adjusted;
                p.args[1] = adjusted.size();
            }
        }, List.class, int.class);
    }

    private static void includeFab(RectF union, View root, View button) throws ReflectiveOperationException {
        if (button == null || button.getVisibility() == View.GONE) return;
        RectF area = new RectF();
        if ((boolean) rectangleInParent.invoke(null, button, root, area) && !area.isEmpty()) {
            float overscan = GlassSurface.CAPTURE_MARGIN_DP * dp(button);
            area.inset(-overscan, -overscan);
            if (area.intersect(0, 0, root.getWidth(), root.getHeight())) union.union(area);
        }
    }

    private static void bindFabs(Object fragment) throws ReflectiveOperationException {
        if (dialogsClass.isInstance(fragment)) {
            Object renderer = dialogsNoise.get(fragment);
            if (renderer != null) dialogsCapture.put(renderer, new WeakReference<>(fragment));
            Object factory = dialogsFactory.get(fragment);
            bindFab((View) messageFab.get(fragment), factory);
            bindFab((View) storyFab.get(fragment), factory);
        } else if (contactsClass.isInstance(fragment)) {
            View view = (View) contactsFab.get(fragment);
            if (view == null) return;
            Object glass = baseGlass.invoke(fragment);
            bindFab(view, glass.getClass().getField("factory").get(glass));
        }
    }

    private static void bindFab(View view, Object factory) throws ReflectiveOperationException {
        if (view == null || factory == null) return;
        Button state = button(view);
        state.disableStockAnimator(view);
        state.freeClipping(view, 3);
        state.useFace(view);
        state.bindCapture(view, factory);
    }

    private static void installPageDown() throws ReflectiveOperationException {
        hook(pageDownInner.getDeclaringClass(), "reverseCounter", new UiHook() {
            @Override void after(MethodHookParam p) throws ReflectiveOperationException {
                View wrapper = (View) p.thisObject;
                View inner = (View) pageDownInner.get(wrapper);
                if (inner != null) bindPageDown(wrapper, inner);
            }
        });
        Field reversed = field(pageDownInner.getDeclaringClass(), "reversedCounter");
        hook(roundBackground.getDeclaringClass(), "draw", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                View view = (View) p.thisObject;
                Canvas canvas = (Canvas) p.args[0];
                if (!canvas.isHardwareAccelerated() || !(view.getParent() instanceof View wrapper)
                        || !pageDownInner.getDeclaringClass().isInstance(wrapper)
                        || !reversed.getBoolean(wrapper)) return;
                Button state = bindPageDown(wrapper, view);
                state.watchPress(wrapper);
                Drawable background = (Drawable) roundBackground.get(view);
                scopeGlass(p, state, background, false);
                p.setObjectExtra(SAVE, canvas.save());
                state.layout.set(0, 0, view.getWidth(), view.getHeight());
                state.move(canvas, state.layout);
            }
            @Override void after(MethodHookParam p) {
                restore(p);
                endScope(p);
            }
        }, Canvas.class);
    }

    private static Button bindPageDown(View wrapper, View view) {
        Button state = button(view);
        state.disableStockAnimator(wrapper);
        if (!touchTargets.containsKey(wrapper)) touchTargets.put(wrapper, new WeakReference<>(view));
        state.freeClipping(view, 2);
        return state;
    }

    private static void installHeaders(ClassLoader loader) throws ReflectiveOperationException {
        Class<?> actionBar = loader.loadClass(UI + "ActionBar.ActionBar");
        installHeader(actionBar, fields(actionBar, "backButtonImageView", "menu", "chatAvatarContainer"),
                "glassDrawableBack", "glassDrawableMenu", "glassDrawable");
        Class<?> simple = loader.loadClass(UI + "ActionBar.SimpleActionBar");
        installHeader(simple, fields(simple, "backButton", "menu", "doneButton"), "glassBack", "glassMenu", "glassDone");

        Class<?> item = loader.loadClass(UI + "ActionBar.ActionBarMenuItem");
        hook(item, "onTouchEvent", new UiHook() {
            @Override void before(MethodHookParam p) {
                View child = (View) p.thisObject;
                if (!child.isEnabled() || !(child.getParent() instanceof View menu)) return;
                if (!(menu.getParent() instanceof View bar)) return;
                Header header = headers.get(bar);
                if (header == null || header.menu == null || header.menu.get() != menu) return;
                Button state = buttons.get(menu);
                if (state != null) state.track((MotionEvent) p.args[0], -child.getX(), -child.getY());
            }
        }, MotionEvent.class);

        installProfileActions(loader);

        // Keep ProfileMusicView's own bounce and layout for the balance and music chips.
        installPanel(loader.loadClass(UI + "Components.ProfileMusicView"), "onDraw", "glass", 1);
        installPanel(loader.loadClass(UI + "Components.ChatActivityTopPanelLayout"), "dispatchDraw", "backgroundDrawable", 1);
        installMenuOverlay(loader);
        installPinnedAction(loader);
    }

    private static void installHeader(Class<?> type, Field[] views, String... drawableFields)
            throws ReflectiveOperationException {
        Field[] glass = fields(type, drawableFields);
        hook(type, "dispatchDraw", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                Canvas canvas = (Canvas) p.args[0];
                if (!canvas.isHardwareAccelerated()) return;
                View bar = (View) p.thisObject;
                Header header = headers.computeIfAbsent(bar, Header::new);
                for (int i = 0; i < glass.length; i++) {
                    View child = (View) views[i].get(bar);
                    if (child != null && child.getVisibility() != View.VISIBLE) child = null;
                    Drawable backdrop = (Drawable) glass[i].get(bar);
                    Button state = header.bind(i, bar, child, backdrop);
                    if (child != null && i != 1) state.watchPress(child);
                    if (i != 0 || child == null || backdrop != null || child.getAlpha() <= 0 || !glassActive()) continue;

                    // Some bars have no native back drawable until the factory is attached.
                    buttonRect(child, state.layout);
                    state.layout.inset(5 * state.dp, 5 * state.dp);
                    if (state.layout.isEmpty()) continue;
                    int save = canvas.save();
                    try {
                        state.move(canvas, state.layout);
                        boolean dark = dark();
                        drawLiquid(canvas, state, null, base(dark), dark, child.getAlpha(), state.layout, null);
                    } finally {
                        canvas.restoreToCount(save);
                    }
                }
                p.setObjectExtra(HEADER, new Header[]{activeHeader});
                activeHeader = header;
            }
            @Override void after(MethodHookParam p) {
                if (p.getObjectExtra(HEADER) instanceof Header[] prior) {
                    activeHeader.end();
                    activeHeader = prior[0];
                }
            }
        }, Canvas.class);
        hook(type, "drawChild", new UiHook() {
            @Override void before(MethodHookParam p) {
                Header header = activeHeader;
                if (header == null || header.owner.get() != p.thisObject) return;
                View child = (View) p.args[1];
                Button state = header.forTarget(child);
                if (state == null || !state.isTransforming()) return;
                Canvas canvas = (Canvas) p.args[0];
                p.setObjectExtra(SAVE, canvas.save());
                if (state.bounds.isEmpty()) {
                    buttonRect(child, state.layout);
                    state.move(canvas, state.layout);
                } else {
                    state.move(canvas, state.bounds);
                }
            }
            @Override void after(MethodHookParam p) { restore(p); }
        }, Canvas.class, View.class, long.class);
    }

    private static void buttonRect(View view, RectF rect) {
        rect.set(view.getX(), view.getY(), view.getX() + view.getWidth(), view.getY() + view.getHeight());
    }

    private static void installPanel(Class<?> type, String draw, String drawableField, int downsample)
            throws ReflectiveOperationException {
        Field glass = field(type, drawableField);
        hook(type, draw, new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                if (!((Canvas) p.args[0]).isHardwareAccelerated()) return;
                View view = (View) p.thisObject;
                Drawable drawable = (Drawable) glass.get(view);
                if (drawable != null) {
                    scopeGlass(p, panels.computeIfAbsent(view, v -> new Button(v, false, downsample)), drawable, false);
                }
            }
            @Override void after(MethodHookParam p) { endScope(p); }
        }, Canvas.class);
    }

    private static void installMenuOverlay(ClassLoader loader) throws ReflectiveOperationException {
        Class<?> overlay = loader.loadClass(UI + "ActionBar.SimpleActionBarMenuOverlay");
        profileClass = loader.loadClass(UI + "ProfileActivity");
        simpleActionBar = field(loader.loadClass(UI + "ActionBar.BaseFragment"), "simpleActionBar");
        profileTop = field(profileClass, "topView");
        profileActionsView = field(profileClass, "actionsView");
        profileOtherItem = field(profileClass, "otherItem");
        profileButtonColor = field(profileTop.getType(), "btnColor");
        drawProfileTop = method(profileTop.getType(), "drawForCapture", Canvas.class);
        UiHook mark = new UiHook() {
            @Override void after(MethodHookParam p) throws ReflectiveOperationException {
                markProfileBar(p.thisObject);
            }
        };
        hook(profileClass, "createHeaderBar", mark, Context.class);
        hook(profileClass, "setupHeaderGlass", mark);
        hook(profileClass, "onResume", mark);
        Field dimMenu = field(loader.loadClass(UI + "ActionBar.ActionBarMenuItem"), "dimMenu");
        hook(dimMenu.getDeclaringClass(), "toggleSubMenu", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                if (!profileMenus.containsKey(p.thisObject) || !glassActive()) return;
                p.setObjectExtra(SCOPE, dimMenu.getFloat(p.thisObject));
                dimMenu.setFloat(p.thisObject, 0);
            }
            @Override void after(MethodHookParam p) throws ReflectiveOperationException {
                if (p.getObjectExtra(SCOPE) instanceof Float original) dimMenu.setFloat(p.thisObject, original);
            }
        }, View.class, View.class);
        Field bar = field(overlay, "bar");
        Field glass = field(overlay, "glass");
        hook(overlay, "dispatchDraw", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                if (!((Canvas) p.args[0]).isHardwareAccelerated()) return;
                View view = (View) p.thisObject;
                Drawable drawable = (Drawable) glass.get(view);
                if (drawable == null) return;
                Button state = panels.computeIfAbsent(view, v -> new Button(v, false, 2));
                Object host = bar.get(view);
                state.noShadow = profileBars.containsKey(host);
                scopeGlass(p, state, drawable, false);
            }
            @Override void after(MethodHookParam p) { endScope(p); }
        }, Canvas.class);
        hook(overlay, "drawShadow", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                Button state = panels.get(p.thisObject);
                if (state != null && state.noShadow && ((Canvas) p.args[0]).isHardwareAccelerated()
                        && glassActive()) p.setResult(null);
            }
        }, Canvas.class, float.class);
    }

    private static void markProfileBar(Object fragment) throws ReflectiveOperationException {
        if (!profileClass.isInstance(fragment)) return;
        Object bar = simpleActionBar.get(fragment);
        if (bar != null) profileBars.put(bar, true);
        Object menu = profileOtherItem.get(fragment);
        if (menu != null) profileMenus.put(menu, true);
        View actions = (View) profileActionsView.get(fragment);
        View top = (View) profileTop.get(fragment);
        if (actions != null && top != null) profileBackdrops.put(actions, new ProfileBackdrop(actions, top));
    }

    private static void installProfileActions(ClassLoader loader) throws ReflectiveOperationException {
        Class<?> viewType = loader.loadClass(UI + "Components.ProfileActionsView");
        Class<?> actionType = loader.loadClass(UI + "Components.ProfileActionsView$Action");
        Field used = field(viewType, "glassUsed");
        Field actions = field(viewType, "actions");
        Field factory = field(viewType, "glassFactory");
        Field hit = field(viewType, "hit");
        Field deleted = field(actionType, "isDeleted");
        Field ripple = field(actionType, "rippleDrawable");
        Field materialRect = field(actionType, "containerInView");
        Field layoutMatrix = field(actionType, "layoutMatrix");

        hook(viewType, "onTouchEvent", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                View view = (View) p.thisObject;
                MotionEvent event = (MotionEvent) p.args[0];
                int type = event.getActionMasked();
                Button state = profileGestures.get(view);
                if (state != null && type != MotionEvent.ACTION_DOWN) {
                    state.track(event, 0, 0);
                    if (type == MotionEvent.ACTION_UP || type == MotionEvent.ACTION_CANCEL
                            || type == MotionEvent.ACTION_POINTER_DOWN) profileGestures.remove(view);
                }
                p.setObjectExtra(SCOPE, profileTouch);
                profileTouch = factory.get(view) != null && glassActive();
            }

            @Override void after(MethodHookParam p) throws ReflectiveOperationException {
                if (!(p.getObjectExtra(SCOPE) instanceof Boolean previous)) return;
                try {
                    MotionEvent event = (MotionEvent) p.args[0];
                    if (!profileTouch || event.getActionMasked() != MotionEvent.ACTION_DOWN
                            || !Boolean.TRUE.equals(p.getResult())) return;
                    View view = (View) p.thisObject;
                    Object action = hit.get(view);
                    if (action == null) return;
                    Button state = profileButton(view, action);
                    state.freeClipping(view, 2);
                    profileGestures.put(view, state);
                    state.track(event, 0, 0);
                } finally {
                    profileTouch = previous;
                }
            }
        }, MotionEvent.class);
        hook(actionType, "setPressed", new UiHook() {
            @Override void before(MethodHookParam p) {
                if (profileTouch) p.setResult(null);
            }
        }, boolean.class);
        hook(viewType, "drawGlass", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                Canvas canvas = (Canvas) p.args[0];
                if (!canvas.isHardwareAccelerated() || !glassActive()) return;
                View view = (View) p.thisObject;
                int index = used.getInt(view);
                // Native drawGlass consumes a slot only for actions that have not been deleted.
                for (Object action : (List<?>) actions.get(view)) {
                    if (deleted.getBoolean(action)) continue;
                    if (index-- != 0) continue;
                    Button state = profileButton(view, action);
                    state.layout.set((RectF) p.args[1]);
                    replacedRipples.put((Drawable) ripple.get(action), true);
                    if (state.isTransforming()) {
                        p.setObjectExtra(SAVE, canvas.save());
                        state.move(canvas, state.layout);
                    }
                    scopeGlass(p, new ActiveGlass(state, null, false));
                    break;
                }
            }
            @Override void after(MethodHookParam p) {
                endScope(p);
                restore(p);
            }
        }, Canvas.class, RectF.class, float[].class, float.class);
        hook(actionType, "updateMaterial3Layout", new UiHook() {
            @Override void after(MethodHookParam p) throws ReflectiveOperationException {
                Button state = profileActions.get(p.thisObject);
                if (state == null || !state.isTransforming() || !glassActive()) return;
                RectF area = (RectF) materialRect.get(p.thisObject);
                Matrix matrix = (Matrix) layoutMatrix.get(p.thisObject);
                ButtonMotion.Transform pose = state.transform(area);
                matrix.postScale(pose.scaleX(), pose.scaleY(), area.centerX(), area.centerY());
                matrix.postTranslate(pose.x(), pose.y());
            }
        }, float.class);
        hook(viewType, "drawAction", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                Button state = profileActions.get(p.args[1]);
                Canvas canvas = (Canvas) p.args[0];
                if (state == null || !state.isTransforming() || state.layout.isEmpty()
                        || !canvas.isHardwareAccelerated() || !glassActive()) return;
                p.setObjectExtra(SAVE, canvas.save());
                state.move(canvas, state.layout);
            }
            @Override void after(MethodHookParam p) { restore(p); }
        }, Canvas.class, actionType, float.class, float.class);
        hook(RippleDrawable.class, "draw", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                if (replacedRipples.containsKey(p.thisObject) && ((Canvas) p.args[0]).isHardwareAccelerated()
                        && glassActive()) p.setResult(null);
            }
        }, Canvas.class);
    }

    private static Button profileButton(View view, Object action) {
        return profileActions.computeIfAbsent(action, key -> {
            Button state = new Button(view, true);
            state.noShadow = true;
            state.profileAction = true;
            return state;
        });
    }

    private static void installPinnedAction(ClassLoader loader) throws ReflectiveOperationException {
        Class<?> chat = loader.loadClass(UI + "ChatActivity");
        Class<?> type = loader.loadClass(UI + "ChatActivity$PinnedMessageButton");
        Field field = field(chat, "pinnedMessageButton");
        pinnedBackground = field(type, "appliedBackground");
        pinnedColor = field(type, "appliedColor");
        hook(chat, "updatePinnedMessageView", new UiHook() {
            @Override void after(MethodHookParam p) throws ReflectiveOperationException {
                View[] controls = (View[]) field.get(p.thisObject);
                for (View view : controls) {
                    if (view == null || view.getBackground() != pinnedBackground.get(view)) continue;
                    Button state = button(view);
                    state.pinned = true;
                    state.useFace(view);
                }
            }
        }, boolean.class, int.class);
        hook(type, "updateColors", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                View view = (View) p.thisObject;
                Button state = buttons.get(view);
                if (state != null && state.face != null && view.getBackground() == state.face) {
                    view.setBackground((Drawable) pinnedBackground.get(view));
                    p.setObjectExtra(SCOPE, state);
                }
            }
            @Override void after(MethodHookParam p) {
                if (p.getObjectExtra(SCOPE) instanceof Button state) state.useFace((View) p.thisObject);
            }
        });
    }

    private static void installQr() throws ReflectiveOperationException {
        // Each QR control has an existing canvas save/restore and keeps its native hit testing.
        hook(qrViewClass, "onTouchEvent", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                View view = (View) p.thisObject;
                MotionEvent event = (MotionEvent) p.args[0];
                QrState state = qr(view, qrRects.length);
                int index = -1;
                if (event.getActionMasked() == MotionEvent.ACTION_DOWN) {
                    int target = (int) qrTarget.invoke(view, event.getX(), event.getY());
                    index = switch (target) {
                        case 3 -> 0; // RP_CLOSE
                        case 5 -> 1; // RP_SCAN
                        case 4 -> 2; // RP_SHARE (the arrow)
                        case 11 -> 3; // RP_SAVE
                        default -> -1;
                    };
                }
                state.track(event, index);
            }
        }, MotionEvent.class);
        hook(qrViewClass, "drawGlass", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                View view = (View) p.thisObject;
                RectF bounds = (RectF) p.args[1];
                Canvas canvas = (Canvas) p.args[0];
                int index = slot(qrRects, view, bounds);
                if (index < 0 || bounds.isEmpty() || !canvas.isHardwareAccelerated() || !glassActive()) return;
                Button state = qr(view, qrRects.length).items[index];
                boolean dark = !(boolean) p.args[3];
                float alpha = (float) p.args[4];
                if (alpha <= 0) return;
                GlassSurface.Backdrop scene = (target, l, t, r, b) -> {
                    if ((boolean) qrHasBlur.invoke(view, target)) qrDrawBlur.invoke(view, target, qrBlur.get(view));
                    else qrDrawPicture.invoke(view, target);
                };
                // Draw first so the original Canvas is intact if backdrop rendering fails.
                drawQrGlass(canvas, state, scene, dark, alpha, bounds);
                state.move(canvas, bounds);
                p.setResult(null);
            }
        }, Canvas.class, RectF.class, float.class, boolean.class, float.class);
        hook(qrViewClass, "drawRipple", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                if (((Canvas) p.args[0]).isHardwareAccelerated()
                        && slot(qrRects, p.thisObject, (RectF) p.args[2]) >= 0 && glassActive()) p.setResult(null);
            }
        }, Canvas.class, int.class, RectF.class, boolean.class);

        Class<?> qrRender = scannerClass.getClassLoader().loadClass(UI + "QrShare.QrRender");
        Method drawNode = method(qrRender, "draw", Canvas.class, Object.class);
        hook(scannerClass, "dispatchTouchEvent", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                View view = (View) p.thisObject;
                MotionEvent event = (MotionEvent) p.args[0];
                int index = -1;
                if (event.getActionMasked() == MotionEvent.ACTION_DOWN) {
                    for (int i = 0; i < scannerRects.length; i++) {
                        if ((i == 0 || scannerGallery.get(view) != null)
                                && ((RectF) scannerRects[i].get(view)).contains(event.getX(), event.getY())) {
                            index = i;
                            break;
                        }
                    }
                }
                qr(view, scannerRects.length).track(event, index);
            }
        }, MotionEvent.class);
        hook(scannerClass, "drawButton", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                Canvas canvas = (Canvas) p.args[0];
                if (!canvas.isHardwareAccelerated() || slot(scannerRects, p.thisObject, (RectF) p.args[1]) < 0
                        || !glassActive()) return;
                p.setObjectExtra(SCOPE, new Object[]{activeQr});
                activeQr = qr((View) p.thisObject, scannerRects.length);
                p.args[2] = 1f;
            }
            @Override void after(MethodHookParam p) {
                if (p.getObjectExtra(SCOPE) instanceof Object[] prior) activeQr = (QrState) prior[0];
            }
        }, Canvas.class, RectF.class, float.class, float.class, Drawable.class);
        hook(scannerClass, "drawGlassBody", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                if (activeQr == null) return;
                View view = (View) p.thisObject;
                RectF bounds = (RectF) p.args[1];
                Canvas canvas = (Canvas) p.args[0];
                int slot = slot(scannerRects, view, bounds);
                if (slot < 0 || bounds.isEmpty() || !canvas.isHardwareAccelerated()) return;
                float alpha = (float) p.args[3];
                if (alpha <= 0) return;
                GlassSurface.Backdrop scene = null;
                if ((boolean) scannerReady.invoke(view, canvas)) {
                    RenderNode node = (RenderNode) scannerBlur.get(view);
                    View camera = (View) scannerCamera.get(view);
                    scene = (target, l, t, r, b) -> {
                        target.translate(camera.getLeft(), camera.getTop());
                        drawNode.invoke(null, target, node);
                    };
                }
                Button state = activeQr.items[slot];
                drawQrGlass(canvas, state, scene, true, alpha, bounds);
                state.move(canvas, bounds);
                p.setResult(null);
            }
        }, Canvas.class, RectF.class, float.class, float.class, boolean.class);
    }

    private static void installConnect(ClassLoader loader) throws ReflectiveOperationException {
        Class<?> scanCell = loader.loadClass(UI + "SessionsActivity$ScanQRCodeView");
        Class<?> cta = loader.loadClass(UI + "Stories.recorder.ButtonWithCounterView");
        Field connect = field(scanCell, "buttonTextView");
        ctaBackground = field(cta, "backgroundColor");
        ctaFilled = field(cta, "filled");
        Field ripple = cta.getField("rippleView");
        installGiftSheets(loader, cta);
        hook(scanCell, "onAttachedToWindow", new UiHook() {
            @Override void after(MethodHookParam p) throws ReflectiveOperationException {
                bindConnect((View) connect.get(p.thisObject));
            }
        });
        hook(cta, "onDraw", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                View view = (View) p.thisObject;
                Canvas canvas = (Canvas) p.args[0];
                if (!canvas.isHardwareAccelerated()) return;
                Button state = buttons.get(view);
                if (state == null && inGiftSheet(view)) state = bindGiftButton(view, true);
                if (state == null) return;
                if (state.giftBackdrop != null) {
                    if (!prepareGiftButton(view, state)) return;
                    Drawable background = ((View) ripple.get(view)).getBackground();
                    if (background != null) replacedRipples.put(background, true);
                } else if (!state.connect) {
                    return;
                }
                state.watchPress(view);
                if (view.getBackground() != state.face) state.useFace(view);
                p.setObjectExtra(SAVE, canvas.save());
                state.layout.set(0, 0, view.getWidth(), view.getHeight());
                state.move(canvas, state.layout);
            }
            @Override void after(MethodHookParam p) { restore(p); }
        }, Canvas.class);
    }

    private static void installGiftSheets(ClassLoader loader, Class<?> cta) throws ReflectiveOperationException {
        Class<?> bottomSheet = loader.loadClass(UI + "ActionBar.BottomSheet");
        Class<?> infoAction = loader.loadClass(UI + "Stars.StarGiftSheet$TopView$Button");
        Class<?> previewAction = loader.loadClass(UI + "Stars.StarGiftPreviewSheet$Button");
        Class<?> theme = loader.loadClass(UI + "ActionBar.Theme");
        themeColor = theme.getMethod("getColor", int.class);
        dialogBackgroundKey = theme.getField("key_dialogBackground").getInt(null);
        giftAccentKey = theme.getField("key_featuredStickers_addButton").getInt(null);
        Method containerView = bottomSheet.getMethod("getContainerView");
        Class<?>[] sheets = new Class<?>[]{
                loader.loadClass(UI + "Stars.StarGiftSheet"),
                loader.loadClass(UI + "Stars.StarGiftPreviewSheet"),
                loader.loadClass(UI + "Stars.GiftOfferSheet"),
                loader.loadClass(UI + "Stars.SellGiftEnterPriceSheet"),
                loader.loadClass(UI + "Gifts.GiftSheet"),
                loader.loadClass(UI + "Gifts.SendGiftSheet"),
                loader.loadClass(UI + "Gifts.SelectGiftsBottomSheet"),
                loader.loadClass(UI + "Gifts.AcquiredGiftsSheet"),
                loader.loadClass(UI + "Gifts.ActiveAuctionsSheet"),
                loader.loadClass(UI + "Gifts.AuctionJoinSheet"),
                loader.loadClass(UI + "Gifts.AuctionBidSheet"),
                loader.loadClass(UI + "Gifts.AuctionWearingSheet")
        };
        hook(bottomSheet, "show", new UiHook() {
            @Override void after(MethodHookParam p) throws ReflectiveOperationException {
                for (Class<?> sheet : sheets) {
                    if (!sheet.isInstance(p.thisObject)) continue;
                    View root = (View) containerView.invoke(p.thisObject);
                    if (root != null) {
                        giftSheets.put(root, true);
                        bindGiftTree(root, cta, infoAction, previewAction);
                    }
                    break;
                }
            }
        });
        hook(ViewGroup.class, "dispatchDraw", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                View view = (View) p.thisObject;
                if (!infoAction.isInstance(view) && !previewAction.isInstance(view)) return;
                Canvas canvas = (Canvas) p.args[0];
                if (!canvas.isHardwareAccelerated()) return;
                Button state = buttons.get(view);
                if (state == null && inGiftSheet(view)) state = bindGiftButton(view, false);
                if (state == null || !prepareGiftButton(view, state)) return;
                state.watchPress(view);
                if (state.isTransforming()) {
                    p.setObjectExtra(SAVE, canvas.save());
                    state.layout.set(0, 0, view.getWidth(), view.getHeight());
                    state.move(canvas, state.layout);
                }
            }
            @Override void after(MethodHookParam p) { restore(p); }
        }, Canvas.class);
    }

    private static boolean inGiftSheet(View view) {
        if (giftSheets.isEmpty()) return false;
        for (View ancestor = view; ancestor != null;
                ancestor = ancestor.getParent() instanceof View parent ? parent : null) {
            if (giftSheets.containsKey(ancestor)) return true;
        }
        return false;
    }

    private static void bindGiftTree(View view, Class<?> cta, Class<?> infoAction, Class<?> previewAction)
            throws ReflectiveOperationException {
        if (cta.isInstance(view) || infoAction.isInstance(view) || previewAction.isInstance(view)) {
            prepareGiftButton(view, bindGiftButton(view, cta.isInstance(view)));
        } else if (view instanceof ViewGroup group) {
            for (int i = 0; i < group.getChildCount(); i++) {
                bindGiftTree(group.getChildAt(i), cta, infoAction, previewAction);
            }
        }
    }

    private static Button bindGiftButton(View view, boolean counter) {
        Button state = buttons.computeIfAbsent(view, v -> new Button(v, false, 2));
        if (state.giftBackdrop == null) state.giftBackdrop = new GiftBackdrop(view);
        state.giftCounter = counter;
        return state;
    }

    private static boolean prepareGiftButton(View view, Button state) throws ReflectiveOperationException {
        if (!glassActive()) {
            state.restoreStockAnimator();
            return false;
        }
        state.disableStockAnimator(view);
        state.freeClipping(view, 2);
        state.useFace(view);
        return true;
    }

    static int strength() { return strength; }

    static void bindDialogAction(View view, boolean positive) {
        if (view == null) return;
        Button state = button(view);
        state.dialogAction = true;
        state.dialogPositive = positive;
        state.noShadow = true;
        state.useFace(view);
    }

    static void installDialogActionMotion(Class<?> text) throws ReflectiveOperationException {
        hook(text, "onDraw", new UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                View view = (View) p.thisObject;
                Canvas canvas = (Canvas) p.args[0];
                Button state = buttons.get(view);
                if (state == null || !state.dialogAction || !canvas.isHardwareAccelerated() || !glassActive()) return;
                state.watchPress(view);
                state.useFace(view);
                if (!state.isTransforming()) return;
                p.setObjectExtra(SAVE, canvas.save());
                state.layout.set(0, 0, view.getWidth(), view.getHeight());
                state.move(canvas, state.layout);
            }
            @Override void after(MethodHookParam p) { restore(p); }
        }, Canvas.class);
    }

    private static void bindConnect(View view) {
        if (view == null) return;
        Button state = button(view);
        state.connect = true;
        state.disableStockAnimator(view);
        state.freeClipping(view, 2);
        state.useFace(view);
    }

    private static void installTouch() {
        UiHook observe = new UiHook() {
            @Override void before(MethodHookParam p) {
                View view = (View) p.thisObject;
                WeakReference<View> target = touchTargets.get(view);
                View owner = target == null ? view : target.get();
                Button state = owner == null ? null : buttons.get(owner);
                if (state != null && !state.menuTarget) {
                    float x = target == null ? 0f : owner.getX();
                    float y = target == null ? 0f : owner.getY();
                    state.track((MotionEvent) p.args[0], x, y);
                }
            }
        };
        for (Class<?> type : new Class<?>[]{View.class, ViewGroup.class}) {
            try {
                hook(type, "dispatchTouchEvent", observe, MotionEvent.class);
            } catch (ReflectiveOperationException | RuntimeException error) {
                report(error);
            }
        }
    }

    private static void drawQrGlass(Canvas canvas, Button button, GlassSurface.Backdrop source,
                                    boolean dark, float alpha, RectF bounds) throws ReflectiveOperationException {
        int save = canvas.save();
        try {
            button.move(canvas, bounds);
            drawLiquid(canvas, button, source, base(dark), dark, alpha, bounds, null);
        } finally {
            canvas.restoreToCount(save);
        }
    }

    private static void drawLiquid(Canvas canvas, Button button, GlassSurface.Backdrop source,
                                   int color, boolean dark, float alpha, RectF bounds, float[] corners)
            throws ReflectiveOperationException {
        if (alpha <= 0 || bounds.isEmpty()) return;
        int save = alpha >= .999f ? canvas.save() : canvas.saveLayerAlpha(
                bounds.left - 6 * button.dp, bounds.top - 6 * button.dp,
                bounds.right + 6 * button.dp, bounds.bottom + 6 * button.dp, Math.round(255 * alpha));
        boolean sampled = source instanceof Sample;
        try {
            float press = button.highlight;
            if (sampled && button.sample.source == null) source = null;
            float tint = source == null ? (dark ? .89f : .88f) : (dark ? .26f : .33f);
            if (source != null && sampled) tint += (button.sample.color >>> 24) / 255f * .10f;
            if (button.giftBackdrop != null) tint = button.giftFilled ? .86f : .32f;
            if (button.dialogAction) tint = button.dialogPositive ? .22f : .13f;
            boolean screenCoordinates = button.canvasControl;
            button.surface.draw(canvas, bounds, button.dp, source, source == null ? 0 : base(dark),
                    (Math.round(tint * 255) << 24) | (color & 0xFFFFFF), corners,
                    optics, press, button.glowX(bounds, screenCoordinates), button.glowY(bounds, screenCoordinates),
                    dark, button.settling(), !button.noShadow);
        } finally {
            if (sampled) button.sample.source = null;
            canvas.restoreToCount(save);
        }
    }

    private static Button button(View view) {
        return buttons.computeIfAbsent(view, v -> new Button(v, false));
    }

    private static void forget(View view) {
        if (view == null) return;
        Button state = buttons.remove(view);
        if (state != null) state.restore(view);
        view.invalidate();
    }

    private static QrState qr(View view, int count) {
        return qrStates.computeIfAbsent(view, v -> new QrState(v, count));
    }

    private static int slot(Field[] fields, Object owner, RectF rect) throws IllegalAccessException {
        for (int i = 0; i < fields.length; i++) if (fields[i].get(owner) == rect) return i;
        return -1;
    }

    private static void scopeGlass(XC_MethodHook.MethodHookParam p, Button state, Drawable drawable, boolean move) {
        if (drawable != null) scopeGlass(p, new ActiveGlass(state, drawable, move));
    }

    private static void scopeGlass(XC_MethodHook.MethodHookParam p, ActiveGlass scope) {
        p.setObjectExtra(SCOPE, new Object[]{activeGlass});
        activeGlass = scope;
    }

    private static void endScope(XC_MethodHook.MethodHookParam p) {
        if (p.getObjectExtra(SCOPE) instanceof Object[] prior) activeGlass = (ActiveGlass) prior[0];
    }

    private static void restore(XC_MethodHook.MethodHookParam p) {
        if (p.getObjectExtra(SAVE) instanceof Integer count) ((Canvas) p.args[0]).restoreToCount(count);
    }

    private static int base(boolean dark) { return dark ? NIGHT : DAY; }
    private static boolean dark() throws ReflectiveOperationException { return (boolean) darkTheme.invoke(null); }
    private static float dp(View view) { return view.getResources().getDisplayMetrics().density; }

    static boolean glassActive() throws ReflectiveOperationException {
        Object settings = glassSettings.invoke(null);
        return blurEnabled.getBoolean(settings) && liquidEnabled.getBoolean(settings);
    }

    private static void extendCapture(Drawable drawable, Button button) throws ReflectiveOperationException {
        if (captureMargins.containsKey(drawable)) return;
        int margin = (int) Math.ceil(GlassSurface.CAPTURE_MARGIN_DP * button.dp);
        int x = (int) getOutsetX.invoke(drawable);
        int y = (int) getOutsetY.invoke(drawable);
        int extendedX = Math.max(x, margin);
        int extendedY = Math.max(y, margin);
        captureMargins.put(drawable, new CaptureMargin(x, y, extendedX, extendedY));
        if (extendedX != x || extendedY != y) {
            setOutset.invoke(drawable, extendedX, extendedY);
            button.invalidateFrame();
        }
    }

    private static void releaseCaptureMargin(Drawable drawable) {
        CaptureMargin margin = captureMargins.remove(drawable);
        if (margin != null) restoreCaptureMargin(drawable, margin);
    }

    private static void restoreCaptureMargin(Drawable drawable, CaptureMargin margin) {
        if (margin.extendedX == margin.x && margin.extendedY == margin.y) return;
        try {
            if ((int) getOutsetX.invoke(drawable) == margin.extendedX
                    && (int) getOutsetY.invoke(drawable) == margin.extendedY) {
                setOutset.invoke(drawable, margin.x, margin.y);
            }
        } catch (ReflectiveOperationException | RuntimeException error) {
            report(error);
        }
    }

    static Field field(Class<?> type, String name) throws ReflectiveOperationException {
        Field f = type.getDeclaredField(name);
        f.setAccessible(true);
        return f;
    }

    private static Field[] fields(Class<?> type, String... names) throws ReflectiveOperationException {
        Field[] result = new Field[names.length];
        for (int i = 0; i < names.length; i++) result[i] = field(type, names[i]);
        return result;
    }

    private static Method method(Class<?> type, String name, Class<?>... params) throws ReflectiveOperationException {
        Method m = type.getDeclaredMethod(name, params);
        m.setAccessible(true);
        return m;
    }

    static void hook(Class<?> type, String name, UiHook hook, Class<?>... params)
            throws ReflectiveOperationException {
        hooks.add(XposedBridge.hookMethod(method(type, name, params), hook));
    }

    static void report(Exception error) {
        if (logged) return;
        logged = true;
        Log.w(TAG, "Could not draw a liquid control", error);
    }

    abstract static class UiHook extends XC_MethodHook {
        @Override public final void beforeHookedMethod(MethodHookParam p) {
            try { before(p); } catch (ReflectiveOperationException | RuntimeException error) { report(error); }
        }
        @Override public final void afterHookedMethod(MethodHookParam p) {
            try { after(p); } catch (ReflectiveOperationException | RuntimeException error) { report(error); }
        }
        void before(MethodHookParam p) throws ReflectiveOperationException {}
        void after(MethodHookParam p) throws ReflectiveOperationException {}
    }

    private static final class Clip {
        final boolean children, padding;
        int owners;
        Clip(ViewGroup group) {
            children = group.getClipChildren();
            padding = group.getClipToPadding();
        }
    }
    private record ActiveGlass(Button button, Drawable drawable, boolean moveGlass) {}
    private record CaptureMargin(int x, int y, int extendedX, int extendedY) {}

    private static final class Header {
        final WeakReference<View> owner;
        final ActiveGlass[] scopes = new ActiveGlass[3];
        final Button[] stationary = new Button[3];
        WeakReference<View> menu;

        Header(View bar) {
            owner = new WeakReference<>(bar);
        }

        Button bind(int index, View bar, View child, Drawable backdrop) {
            if (index == 1 && (menu == null || menu.get() != child)) {
                menu = child == null ? null : new WeakReference<>(child);
            }
            Button state;
            if (child == null) {
                if (backdrop == null) {
                    scopes[index] = null;
                    return null;
                }
                if (stationary[index] == null) stationary[index] = new Button(bar, false);
                state = stationary[index];
            } else {
                state = button(child);
                state.invalidateHost = owner;
                state.menuTarget = index == 1;
            }
            scopes[index] = new ActiveGlass(state, backdrop, child != null);
            return state;
        }

        void end() {
            // Drawables belong to the native bar and may have it as their callback.
            for (int i = 0; i < scopes.length; i++) scopes[i] = null;
        }

        View target(int index) {
            ActiveGlass scope = scopes[index];
            return scope == null || !scope.moveGlass ? null : scope.button.view.get();
        }

        Button forTarget(View view) {
            for (int i = 0; i < scopes.length; i++) {
                if (view == target(i)) return scopes[i].button;
            }
            return null;
        }

        ActiveGlass find(Object drawable) {
            for (ActiveGlass scope : scopes) {
                if (scope != null && drawable == scope.drawable) return scope;
            }
            return null;
        }
    }

    private static final class QrState {
        final Button[] items;
        int active = -1;
        QrState(View view, int count) {
            items = new Button[count];
            for (int i = 0; i < count; i++) items[i] = new Button(view, true);
        }
        void track(MotionEvent event, int index) {
            if (event.getActionMasked() == MotionEvent.ACTION_DOWN) active = index;
            if (active < 0) return;
            items[active].track(event, 0, 0);
            if (event.getActionMasked() == MotionEvent.ACTION_UP || event.getActionMasked() == MotionEvent.ACTION_CANCEL
                    || event.getActionMasked() == MotionEvent.ACTION_POINTER_DOWN) active = -1;
        }
        void cancel() {
            for (Button item : items) item.cancelAnimations();
        }
    }

    private static final class Sample implements GlassSurface.Backdrop {
        final Rect padded = new Rect();
        Object source;
        Object recordingToken;
        WeakReference<Object> recordedSource;
        float[] radii;
        float x, y;
        int color;
        boolean resolve(Drawable drawable) throws ReflectiveOperationException {
            if (drawable == null || drawable.getAlpha() <= 0) return false;
            syncTheme.invoke(drawable);
            syncGlass.invoke(drawable);
            resolveSource.invoke(drawable);
            source = getSource.invoke(drawable);
            float nextX = (float) offsetX.invoke(drawable);
            float nextY = (float) offsetY.invoke(drawable);
            if (!renderNodeSourceClass.isInstance(source)) {
                recordingToken = null;
                recordedSource = null;
            } else if (recordedSource == null || recordedSource.get() != source || nextX != x || nextY != y) {
                recordedSource = new WeakReference<>(source);
                recordingToken = new Object();
            }
            x = nextX;
            y = nextY;
            color = backgroundColor.getInt(drawable);
            radii = (float[]) drawableRadii.get(drawableProps.get(drawable));
            paddedBounds.invoke(drawable, padded);
            return !padded.isEmpty();
        }

        @Override public Object recordingToken() { return recordingToken; }

        @Override public void draw(Canvas canvas, float l, float t, float r, float b)
                throws ReflectiveOperationException {
            if (source == null) return;
            int save = canvas.save();
            try {
                canvas.translate(-x, -y);
                sourceDraw.invoke(source, canvas, l + x, t + y, r + x, b + y);
            } catch (InvocationTargetException error) {
                if (error.getCause() instanceof IllegalStateException unavailable) throw unavailable;
                throw error;
            } finally {
                canvas.restoreToCount(save);
            }
        }
    }

    private static final class ProfileBackdrop implements GlassSurface.Backdrop {
        final WeakReference<View> owner, header;
        final int[] ownerLocation = new int[2];
        final int[] headerLocation = new int[2];
        final RenderNode backgroundNode = new RenderNode("Glassify profile backdrop");
        long recordedFrame = -1;

        ProfileBackdrop(View owner, View header) {
            this.owner = new WeakReference<>(owner);
            this.header = new WeakReference<>(header);
        }

        int tint(int fallback) throws IllegalAccessException {
            View top = header.get();
            if (top == null) return fallback;
            int color = profileButtonColor.getInt(top);
            return (color >>> 24) == 0 ? fallback : color;
        }

        @Override public void draw(Canvas canvas, float left, float top, float right, float bottom)
                throws ReflectiveOperationException {
            View actions = owner.get(), background = header.get();
            if (actions == null || background == null || !background.isShown()
                    || background.getWidth() <= 0 || background.getHeight() <= 0) return;
            long frame = AnimationUtils.currentAnimationTimeMillis();
            if (recordedFrame != frame || !backgroundNode.hasDisplayList()) {
                backgroundNode.setPosition(0, 0, background.getWidth(), background.getHeight());
                Canvas recording = backgroundNode.beginRecording();
                try {
                    drawProfileTop.invoke(background, recording);
                } finally {
                    backgroundNode.endRecording();
                }
                recordedFrame = frame;
            }
            actions.getLocationOnScreen(ownerLocation);
            background.getLocationOnScreen(headerLocation);
            int save = canvas.save();
            try {
                canvas.translate(headerLocation[0] - ownerLocation[0], headerLocation[1] - ownerLocation[1]);
                canvas.drawRenderNode(backgroundNode);
            } finally {
                canvas.restoreToCount(save);
            }
        }
    }

    private static final class GiftBackdrop implements GlassSurface.Backdrop {
        final WeakReference<View> owner;
        int fallback;

        GiftBackdrop(View view) { owner = new WeakReference<>(view); }

        @Override public void draw(Canvas canvas, float left, float top, float right, float bottom) {
            // Only draw the surface behind the button. Recording the sheet itself would include the lens.
            canvas.drawColor(fallback);
            View layer = owner.get();
            float x = 0, y = 0;
            while (layer != null && layer.getParent() instanceof View parent) {
                x += layer.getX() - parent.getScrollX();
                y += layer.getY() - parent.getScrollY();
                Drawable background = parent.getBackground();
                if (background != null && !(background instanceof Face) && background.getAlpha() > 0) {
                    int save = canvas.save();
                    try {
                        canvas.translate(-x, -y);
                        background.draw(canvas);
                    } finally {
                        canvas.restoreToCount(save);
                    }
                    break;
                }
                layer = parent;
            }
        }
    }

    private static final class Button {
        final WeakReference<View> view;
        final float dp;
        final boolean canvasControl;
        final FloatValueHolder phase = new FloatValueHolder(1f);
        final SpringAnimation press = new SpringAnimation(phase);
        final RectF bounds = new RectF();
        final RectF layout = new RectF();
        final Sample sample = new Sample();
        final GlassSurface surface;
        final List<WeakReference<ViewGroup>> clipOwners = new ArrayList<>();
        boolean tracking, touchReleased, lifted, touchKnown, outlineDisabled, connect, pinned, menuTarget;
        boolean noShadow, profileAction, giftCounter, giftFilled, dialogAction, dialogPositive;
        GiftBackdrop giftBackdrop;
        ButtonMotion.Transform shown = ButtonMotion.REST;
        ButtonMotion.Transform from = ButtonMotion.REST;
        float highlight;
        ValueAnimator highlightAnimation;
        WeakReference<View> invalidateHost;
        WeakReference<ViewGroup> clipParent;
        float startX, startY, x, y;
        Drawable capture;
        WeakReference<Object> engine;
        WeakReference<View> animatorOwner;
        StateListAnimator originalAnimator;
        ViewOutlineProvider originalFabOutline;
        Face face;
        View.OnAttachStateChangeListener attach;
        View.OnLayoutChangeListener layoutListener;
        int warmup;

        Button(View target, boolean canvasControl) {
            this(target, canvasControl, 1);
        }

        Button(View target, boolean canvasControl, int downsample) {
            view = new WeakReference<>(target);
            dp = dp(target);
            this.canvasControl = canvasControl;
            surface = new GlassSurface(.40f, downsample);
            press.setMinimumVisibleChange(.001f);
            press.setSpring(new SpringForce(1f));
            press.addUpdateListener((animation, value, velocity) -> invalidateAnimationFrame());
        }

        void animate(boolean pressed) {
            if (!ValueAnimator.areAnimatorsEnabled()) {
                cancelAnimations();
                phase.setValue(1f);
                lifted = false;
                shown = from = ButtonMotion.REST;
                highlight = 0;
                return;
            }
            if (lifted == pressed) return;
            boolean wasResting = !lifted && !press.isRunning();
            from = wasResting ? ButtonMotion.REST : shown;
            lifted = pressed;
            animateHighlight(pressed);
            press.cancel();
            if (!pressed && from == ButtonMotion.REST) {
                phase.setValue(1f);
                return;
            }
            phase.setValue(0f);
            ButtonMotion.Spring spring = pressed ? ButtonMotion.LIFT_ON : ButtonMotion.LIFT_OFF;
            press.getSpring()
                    .setStiffness(spring.androidStiffness())
                    .setDampingRatio(spring.androidDamping());
            press.setStartValue(0f).setStartVelocity(0f).start();
        }

        private void animateHighlight(boolean pressed) {
            stopHighlightAnimation();
            float target = pressed ? 1f : 0f;
            if (highlight == target) return;
            highlightAnimation = ValueAnimator.ofFloat(highlight, target);
            highlightAnimation.setDuration(pressed ? 120L : 220L);
            highlightAnimation.setInterpolator(pressed ? HIGHLIGHT_IN : HIGHLIGHT_OUT);
            highlightAnimation.addUpdateListener(animation -> {
                highlight = (float) animation.getAnimatedValue();
                invalidateAnimationFrame();
            });
            highlightAnimation.start();
        }

        private void stopHighlightAnimation() {
            if (highlightAnimation == null) return;
            highlightAnimation.cancel();
            highlightAnimation = null;
        }

        void cancelAnimations() {
            press.cancel();
            stopHighlightAnimation();
        }

        boolean isTransforming() { return lifted || press.isRunning(); }

        boolean settling() { return !lifted && press.isRunning(); }

        void watchPress(View owner) {
            boolean nativePress = owner.isPressed() && owner.isEnabled();
            // Android may keep isPressed set after UP to finish its own click animation.
            if (!nativePress && !press.isRunning()) touchReleased = false;
            animate(tracking || (nativePress && !touchReleased));
        }

        void track(MotionEvent event, float offsetX, float offsetY) {
            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    tracking = true;
                    touchReleased = false;
                    touchKnown = true;
                    x = startX = event.getX() - offsetX;
                    y = startY = event.getY() - offsetY;
                    animate(true);
                    break;
                case MotionEvent.ACTION_MOVE:
                    if (!tracking) return;
                    float nextX = event.getX() - offsetX;
                    float nextY = event.getY() - offsetY;
                    if (x == nextX && y == nextY) return;
                    x = nextX;
                    y = nextY;
                    // Like TouchEffect.setStretchVector, follow the finger immediately.
                    if (lifted) {
                        cancelAnimations();
                        phase.setValue(1f);
                        highlight = 1f;
                    }
                    break;
                case MotionEvent.ACTION_UP:
                case MotionEvent.ACTION_CANCEL:
                case MotionEvent.ACTION_POINTER_DOWN:
                    if (!tracking) return;
                    tracking = false;
                    touchReleased = true;
                    animate(false);
                    break;
                default:
                    return;
            }
            invalidateFrame();
        }

        void invalidateFrame() {
            View target = invalidateTarget();
            if (target != null) target.postInvalidateOnAnimation();
        }

        private void invalidateAnimationFrame() {
            // Animation callbacks already run in this frame, so draw without posting another frame.
            View target = invalidateTarget();
            if (target != null) target.invalidate();
        }

        private View invalidateTarget() {
            View host = invalidateHost == null ? null : invalidateHost.get();
            return host == null ? view.get() : host;
        }

        ButtonMotion.Transform transform(RectF area) {
            ButtonMotion.Transform target = lifted
                    ? ButtonMotion.transform(area.width(), area.height(), dp, 1f,
                            touchKnown ? x - startX : 0, touchKnown ? y - startY : 0)
                    : ButtonMotion.REST;
            shown = ButtonMotion.interpolate(from, target, phase.getValue());
            return shown;
        }

        void move(Canvas canvas, RectF area) {
            ButtonMotion.Transform pose = transform(area);
            if (pose == ButtonMotion.REST) return;
            canvas.translate(pose.x(), pose.y());
            canvas.scale(pose.scaleX(), pose.scaleY(), area.centerX(), area.centerY());
        }

        float glowX(RectF area, boolean absolute) {
            if (!touchKnown) return area.centerX();
            View target = view.get();
            return absolute || target == null ? x : area.centerX() + x - target.getWidth() / 2f;
        }

        float glowY(RectF area, boolean absolute) {
            if (!touchKnown) return area.centerY();
            View target = view.get();
            return absolute || target == null ? y : area.centerY() + y - target.getHeight() / 2f;
        }

        void freeClipping(View target, int levels) {
            if (!(target.getParent() instanceof ViewGroup parent)) return;
            if (clipParent != null && clipParent.get() == parent) return;
            releaseClipping();
            clipParent = new WeakReference<>(parent);
            if (target.getClipToOutline()) {
                outlineDisabled = true;
                target.setClipToOutline(false);
            }
            View current = target;
            for (int i = 0; i < levels && current.getParent() instanceof ViewGroup group; i++) {
                Clip clip = clips.computeIfAbsent(group, Clip::new);
                clip.owners++;
                clipOwners.add(new WeakReference<>(group));
                group.setClipChildren(false);
                group.setClipToPadding(false);
                current = group;
            }
        }

        void disableStockAnimator(View owner) {
            if (animatorOwner != null && animatorOwner.get() == owner) return;
            animatorOwner = new WeakReference<>(owner);
            originalAnimator = owner.getStateListAnimator();
            if (originalAnimator != null) owner.setStateListAnimator(null);
        }

        void restoreStockAnimator() {
            if (animatorOwner == null) return;
            View owner = animatorOwner.get();
            if (owner != null && owner.getStateListAnimator() == null) owner.setStateListAnimator(originalAnimator);
            animatorOwner = null;
            originalAnimator = null;
        }

        void setRoundFabOutline(View target, boolean enabled) {
            ViewOutlineProvider outline = target.getOutlineProvider();
            if (enabled && outline != ROUND_FAB_OUTLINE) {
                originalFabOutline = outline;
                target.setOutlineProvider(ROUND_FAB_OUTLINE);
            } else if (!enabled && outline == ROUND_FAB_OUTLINE) {
                target.setOutlineProvider(originalFabOutline);
                originalFabOutline = null;
            }
        }

        void useFace(View view) {
            if (view.getBackground() == face && face != null) return;
            face = new Face(this, view.getBackground());
            view.setBackground(face);
        }

        void bindCapture(View view, Object factory) throws ReflectiveOperationException {
            if (capture != null || attach != null) return;
            if (view.isAttachedToWindow()) {
                create(view, factory);
                return;
            }
            attach = new View.OnAttachStateChangeListener() {
                @Override public void onViewAttachedToWindow(View target) {
                    target.removeOnAttachStateChangeListener(this);
                    attach = null;
                    try { create(target, factory); } catch (ReflectiveOperationException | RuntimeException error) { report(error); }
                }
                @Override public void onViewDetachedFromWindow(View target) {}
            };
            view.addOnAttachStateChangeListener(attach);
        }

        private void create(View view, Object factory) throws ReflectiveOperationException {
            engine = new WeakReference<>(factoryEngine.get(factory));
            capture = (Drawable) createCapture.invoke(factory, view);
            int margin = (int) Math.ceil(GlassSurface.CAPTURE_MARGIN_DP * dp);
            setOutset.invoke(capture, margin, margin);
            layoutListener = (v, l, t, r, b, oldL, oldT, oldR, oldB) -> updateCapture(v);
            view.addOnLayoutChangeListener(layoutListener);
            updateCapture(view);
        }

        private void updateCapture(View target) {
            if (capture == null || target.getWidth() <= 0 || target.getHeight() <= 0) return;
            capture.setBounds(0, 0, target.getWidth(), target.getHeight());
            try {
                Object owner = engine.get();
                if (owner != null) engineInvalidate.invoke(owner);
            } catch (ReflectiveOperationException | RuntimeException error) {
                report(error);
            }
            // Native capture is populated during the following root draw.
            warmup = 3;
            target.postInvalidateOnAnimation();
            target.getRootView().postInvalidateOnAnimation();
        }

        private void releaseClipping() {
            for (WeakReference<ViewGroup> owner : clipOwners) {
                ViewGroup group = owner.get();
                Clip clip = group == null ? null : clips.get(group);
                if (clip != null && --clip.owners == 0) {
                    group.setClipChildren(clip.children);
                    group.setClipToPadding(clip.padding);
                    clips.remove(group);
                }
            }
            clipOwners.clear();
            clipParent = null;
        }

        void restore(View target) {
            cancelAnimations();
            releaseClipping();
            setRoundFabOutline(target, false);
            if (outlineDisabled) target.setClipToOutline(true);
            if (attach != null) target.removeOnAttachStateChangeListener(attach);
            if (layoutListener != null) target.removeOnLayoutChangeListener(layoutListener);
            if (target.getBackground() == face && face != null) target.setBackground(face.stock);
            restoreStockAnimator();
            if (capture != null && engine != null && engine.get() != null) {
                try { unregister.invoke(engine.get(), capture); }
                catch (ReflectiveOperationException | RuntimeException error) { report(error); }
            }
            capture = null;
        }
    }

    private static final class Face extends Drawable {
        final Button state;
        final Drawable stock;
        private int alpha = 255;

        Face(Button state, Drawable stock) { this.state = state; this.stock = stock; }

        @Override public void draw(Canvas canvas) {
            View view = state.view.get();
            if (view != null && canvas.isHardwareAccelerated() && alpha > 0) {
                try {
                    if (state.warmup > 0) {
                        state.warmup--;
                        view.postInvalidateOnAnimation();
                    }
                    if (glassActive()) {
                        drawGlass(canvas, view);
                        return;
                    }
                } catch (ReflectiveOperationException | RuntimeException error) {
                    report(error);
                }
            }
            drawStock(canvas);
        }

        private void drawGlass(Canvas canvas, View view) throws ReflectiveOperationException {
            state.bounds.set(getBounds());
            if (state.giftBackdrop != null) {
                state.giftFilled = state.giftCounter && ctaFilled.getBoolean(view);
                state.giftBackdrop.fallback = state.giftCounter
                        ? (int) themeColor.invoke(null, dialogBackgroundKey) : NIGHT;
                boolean dark = !state.giftCounter || dark();
                int color = base(dark);
                if (state.giftFilled) {
                    color = stock instanceof ShapeDrawable shape ? shape.getPaint().getColor()
                            : ctaBackground.getInt(view);
                    if (Color.luminance(color) < .055f) {
                        color = (int) themeColor.invoke(null, giftAccentKey);
                        if (Color.luminance(color) < .055f) {
                            color = Color.rgb(
                                    Math.round(ButtonMotion.lerp(Color.red(color), 255, .33f)),
                                    Math.round(ButtonMotion.lerp(Color.green(color), 255, .33f)),
                                    Math.round(ButtonMotion.lerp(Color.blue(color), 255, .33f)));
                        }
                    }
                } else {
                    color = Color.WHITE;
                }
                int save = canvas.save();
                try {
                    state.move(canvas, state.bounds);
                    drawLiquid(canvas, state, state.giftBackdrop, color, dark, alpha / 255f, state.bounds, null);
                } finally {
                    canvas.restoreToCount(save);
                }
                return;
            }
            if (state.dialogAction && view instanceof TextView label) {
                int save = canvas.save();
                try {
                    state.move(canvas, state.bounds);
                    drawLiquid(canvas, state, null, label.getCurrentTextColor(), dark(), alpha / 255f, state.bounds, null);
                } finally {
                    canvas.restoreToCount(save);
                }
                return;
            }
            if (state.connect || state.pinned) {
                int save = canvas.save();
                try {
                    if (state.connect) state.move(canvas, state.bounds);
                    boolean dark = dark();
                    int color = (state.pinned ? pinnedColor : ctaBackground).getInt(view);
                    drawLiquid(canvas, state, null, color == 0 ? 0xFF345784 : color,
                            dark, alpha / 255f, state.bounds, null);
                } finally {
                    canvas.restoreToCount(save);
                }
                return;
            }
            boolean subButton = fabSub.getBoolean(view);
            if (subButton) state.bounds.inset(4 * state.dp, 4 * state.dp);
            boolean dark = dark();
            int color = subButton ? base(dark) : fabTint.getInt(view);
            GlassSurface.Backdrop backdrop = state.sample.resolve(state.capture) ? state.sample : null;
            // Capture bounds describe a texture. The floating control owns its circular silhouette.
            drawLiquid(canvas, state, backdrop, color == 0 ? base(dark) : color, dark,
                    alpha / 255f, state.bounds, null);
        }

        private void drawStock(Canvas canvas) {
            if (stock != null && alpha > 0) {
                stock.setState(getState());
                stock.setBounds(getBounds());
                stock.draw(canvas);
            }
        }

        @Override public boolean isStateful() { return true; }
        @Override protected boolean onStateChange(int[] state) { invalidateSelf(); return true; }
        @Override public boolean getPadding(Rect result) { return stock != null && stock.getPadding(result); }
        @Override public int getMinimumWidth() { return stock == null ? 0 : stock.getMinimumWidth(); }
        @Override public int getMinimumHeight() { return stock == null ? 0 : stock.getMinimumHeight(); }
        @Override public void setAlpha(int alpha) { this.alpha = alpha; invalidateSelf(); }
        @Override public int getAlpha() { return alpha; }
        @Override public void setColorFilter(ColorFilter filter) {}
        @Override public int getOpacity() { return PixelFormat.TRANSLUCENT; }
    }
}
