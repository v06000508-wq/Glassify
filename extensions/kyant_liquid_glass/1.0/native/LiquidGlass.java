package glassify.kyant;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.LinearGradient;
import android.graphics.Outline;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.Shader;
import android.graphics.drawable.Drawable;
import android.os.Build;
import android.util.Log;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;

import androidx.dynamicanimation.animation.FloatValueHolder;
import androidx.dynamicanimation.animation.SpringAnimation;
import androidx.dynamicanimation.animation.SpringForce;

import java.lang.ref.WeakReference;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.WeakHashMap;

import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.XposedBridge;

public final class LiquidGlass {
    private static final String TAG = "GlassifyKyant";
    private static final ArrayList<XC_MethodHook.Unhook> hooks = new ArrayList<>();
    private static final WeakHashMap<View, Tabs> tabs = new WeakHashMap<>();
    private static final WeakHashMap<Drawable, WeakReference<View>> bars = new WeakHashMap<>();
    private static final WeakHashMap<View, Button> buttons = new WeakHashMap<>();
    private static final String DRAW_FRAME = "glassify.kyant.drawFrame";
    private static final String STOCK_SELECTOR = "glassify.kyant.stockSelector";
    private static final String STOCK_DIVIDER = "glassify.kyant.stockDivider";
    private static final int DEFAULT_LIGHT = 0xFFF7F8FB;
    private static final int DEFAULT_DARK = 0xFF1B1C21;

    private static Class<?> mainActivity, tabLayout, glassTab, blurDrawable, roundButton, fab, send;
    private static Field mainTabs, swipe, dragging, dragX, dragOffset, tabSkip, layoutSelector, layoutDivider;
    private static Field backgroundColor, roundBackground, sendRect, sendPaint, sendNew;
    private static Field fabSub;
    private static Method findSelected, syncGlass, syncTheme, resolveSource, getSource, sourceDraw;
    private static Method offsetX, offsetY, paddedBounds, themeDark, stockBlurDraw;
    private static boolean dark;
    private static boolean loggedDrawError;
    private static Button currentRound;
    private static Drawable currentRoundBackground;
    private static Button currentSend;

    // Glassify API 4 calls this on the UI thread using the app's classloader.
    public static void onLoad(Context context, Object unused) throws ReflectiveOperationException {
        if (Build.VERSION.SDK_INT < 33) {
            throw new IllegalStateException("Kyant Liquid Glass requires Android 13 or newer");
        }
        if (!hooks.isEmpty()) return;
        try {
            resolve(context.getClassLoader());
            installTabs();
            installButtons();
            Class<?> launchActivity = context.getClassLoader().loadClass("org.telegram.ui.LaunchActivity");
            attachTabs(launchActivity.getMethod("getLastFragment").invoke(null));
        } catch (ReflectiveOperationException | RuntimeException | LinkageError error) {
            onUnload();
            throw error;
        }
    }

    public static void onUnload() {
        for (XC_MethodHook.Unhook handle : hooks) handle.unhook();
        hooks.clear();
        tabs.forEach((view, state) -> {
            state.centerSpring.cancel();
            state.pressSpring.cancel();
            try {
                swipe.setBoolean(view, state.stockSwipe);
            } catch (IllegalAccessException error) {
                Log.w(TAG, "Could not restore tab swipe", error);
            }
            view.invalidate();
            if (view.getBackground() != null) view.getBackground().invalidateSelf();
            invalidateTabs((ViewGroup) view);
        });
        buttons.forEach((view, state) -> {
            state.pressSpring.cancel();
            view.invalidate();
        });
        tabs.clear();
        bars.clear();
        buttons.clear();
        loggedDrawError = false;
    }

    private static void resolve(ClassLoader loader) throws ReflectiveOperationException {
        String ui = "org.telegram.ui.";
        String components = ui + "Components.";
        mainActivity = loader.loadClass(ui + "MainTabsActivity");
        tabLayout = loader.loadClass(ui + "MainTabsLayout");
        glassTab = loader.loadClass(components + "glass.GlassTabView");
        blurDrawable = loader.loadClass(components + "blur3.drawable.BlurredBackgroundDrawable");
        roundButton = loader.loadClass(components + "chat.buttons.ChatActivityBlurredRoundButton");
        fab = loader.loadClass(components + "FragmentFloatingButton");
        send = loader.loadClass(components + "ChatActivityEnterView$SendButton");

        mainTabs = field(mainActivity, "tabsView");
        swipe = field(tabLayout, "swipeSelectionEnabled");
        dragging = field(tabLayout, "isInLongPress");
        dragX = field(tabLayout, "animatedLongSelectedViewCenterX");
        dragOffset = field(tabLayout, "animatedLongSelectedViewOffsetX");
        layoutSelector = field(tabLayout, "drawCustomSelector");
        layoutDivider = field(tabLayout, "drawTopDivider");
        stockBlurDraw = method(blurDrawable, "draw", Canvas.class);
        tabSkip = field(glassTab, "skipDrawSelector");
        findSelected = method(tabLayout, "findSelectedTab");

        syncGlass = method(blurDrawable, "checkGlassSettings");
        syncTheme = method(blurDrawable, "checkThemeColors");
        resolveSource = blurDrawable.getMethod("shouldHaveDisplayList");
        getSource = blurDrawable.getMethod("getUnwrappedSource");
        sourceDraw = loader.loadClass("org.telegram.utils.glass.source.GlassSource")
                .getMethod("draw", Canvas.class, float.class, float.class, float.class, float.class);
        offsetX = blurDrawable.getMethod("getSourceOffsetX");
        offsetY = blurDrawable.getMethod("getSourceOffsetY");
        paddedBounds = blurDrawable.getMethod("getBoundsWithPaddingInset", Rect.class);
        backgroundColor = field(blurDrawable, "backgroundColor");
        themeDark = loader.loadClass(ui + "ActionBar.Theme").getMethod("isCurrentThemeDark");

        roundBackground = field(roundButton, "backgroundDrawable");
        sendNew = field(send, "isNewDesignSendButton");
        sendRect = field(send, "backgroundRect");
        sendPaint = field(send, "backgroundPaint");
        fabSub = field(fab, "isSubButton");
    }

    private static void installTabs() throws ReflectiveOperationException {
        XC_MethodHook attach = new XC_MethodHook() {
            @Override protected void afterHookedMethod(MethodHookParam p) throws Throwable {
                if (!p.hasThrowable()) attachTabs(p.thisObject);
            }
        };
        hook(mainActivity, "createView", attach, Context.class);
        hook(mainActivity, "onResume", attach);

        hook(tabLayout, "dispatchTouchEvent", new XC_MethodHook() {
            @Override protected void beforeHookedMethod(MethodHookParam p) {
                View view = (View) p.thisObject;
                Tabs state = tabs.get(view);
                if (state != null) state.touch(view, (MotionEvent) p.args[0]);
            }
        }, MotionEvent.class);

        hook(tabLayout, "setTabSelected", new XC_MethodHook() {
            @Override protected void afterHookedMethod(MethodHookParam p) {
                View view = (View) p.thisObject;
                if (tabs.containsKey(view)) view.invalidate();
            }
        }, View.class, boolean.class);

        hook(tabLayout, "dispatchDraw", new XC_MethodHook() {
            @Override protected void beforeHookedMethod(MethodHookParam p) throws Throwable {
                ViewGroup view = (ViewGroup) p.thisObject;
                Tabs state = tabs.get(view);
                Canvas canvas = (Canvas) p.args[0];
                if (state == null || !canvas.isHardwareAccelerated()) return;
                try {
                    Drawable background = view.getBackground();
                    if (!blurDrawable.isInstance(background)) {
                        state.setHideStock(view, false);
                        return;
                    }
                    if (!state.drawPanel(canvas, view, background)) {
                        state.setHideStock(view, false);
                        XposedBridge.invokeOriginalMethod(stockBlurDraw, background, new Object[]{canvas});
                        return;
                    }
                    p.setObjectExtra(STOCK_DIVIDER, layoutDivider.getBoolean(view));
                    layoutDivider.setBoolean(view, false);
                    if (state.drawSelection(canvas, view)) {
                        p.setObjectExtra(STOCK_SELECTOR, layoutSelector.getBoolean(view));
                        layoutSelector.setBoolean(view, false);
                    }
                } catch (ReflectiveOperationException | RuntimeException error) {
                    state.setHideStock(view, false);
                    drawError(error);
                }
            }
            @Override protected void afterHookedMethod(MethodHookParam p) throws Throwable {
                Object saved = p.getObjectExtra(STOCK_SELECTOR);
                if (saved != null) layoutSelector.setBoolean(p.thisObject, (boolean) saved);
                saved = p.getObjectExtra(STOCK_DIVIDER);
                if (saved != null) layoutDivider.setBoolean(p.thisObject, (boolean) saved);
            }
        }, Canvas.class);

        hook(glassTab, "dispatchDraw", new XC_MethodHook() {
            @Override protected void beforeHookedMethod(MethodHookParam p) throws Throwable {
                View view = (View) p.thisObject;
                if (!(view.getParent() instanceof View)) return;
                Tabs state = tabs.get((View) view.getParent());
                if (state == null || !state.hideStock || !((Canvas) p.args[0]).isHardwareAccelerated()) return;
                p.setObjectExtra(STOCK_SELECTOR, tabSkip.getBoolean(view));
                tabSkip.setBoolean(view, true);
            }
            @Override protected void afterHookedMethod(MethodHookParam p) throws Throwable {
                Object saved = p.getObjectExtra(STOCK_SELECTOR);
                if (saved != null) tabSkip.setBoolean(p.thisObject, (boolean) saved);
            }
        }, Canvas.class);

        hook(blurDrawable, "draw", new XC_MethodHook() {
            @Override protected void beforeHookedMethod(MethodHookParam p) {
                Drawable drawable = (Drawable) p.thisObject;
                Canvas canvas = (Canvas) p.args[0];
                if (!canvas.isHardwareAccelerated()) return;

                WeakReference<View> owner = bars.get(drawable);
                View view = owner == null ? null : owner.get();
                Tabs state = view == null || view.getBackground() != drawable ? null : tabs.get(view);
                Button button = currentRoundBackground == drawable ? currentRound : null;
                if (state == null && button == null) return;

                try {
                    if (state != null) {
                        p.setResult(null);
                    } else if (button != null && button.drawRound(canvas, drawable)) {
                        p.setResult(null);
                    }
                } catch (ReflectiveOperationException | RuntimeException error) {
                    drawError(error);
                }
            }
        }, Canvas.class);
    }

    private static void attachTabs(Object fragment) throws ReflectiveOperationException {
        if (!mainActivity.isInstance(fragment)) return;
        ViewGroup view = (ViewGroup) mainTabs.get(fragment);
        if (view == null || !blurDrawable.isInstance(view.getBackground())) return;
        if (!tabs.containsKey(view)) tabs.put(view, new Tabs(view, swipe.getBoolean(view)));
        bars.put(view.getBackground(), new WeakReference<>(view));
        swipe.setBoolean(view, true);
        view.getBackground().invalidateSelf();
        view.invalidate();
        invalidateTabs(view);
    }

    private static void installButtons() throws ReflectiveOperationException {
        hook(roundButton, "draw", drawButton(0), Canvas.class);
        hook(fab, "draw", drawButton(1), Canvas.class);
        hook(send, "onDraw", drawButton(2), Canvas.class);
        hook(send, "checkBackgroundRect", new XC_MethodHook() {
            @Override protected void afterHookedMethod(MethodHookParam p) throws Throwable {
                if (currentSend == null || currentSend.view.get() != p.thisObject) return;
                Paint paint = (Paint) sendPaint.get(p.thisObject);
                RectF rect = (RectF) sendRect.get(p.thisObject);
                if (rect.isEmpty()) return;
                currentSend.savedShader = paint.getShader();
                currentSend.sendShaderChanged = true;
                paint.setShader(currentSend.gradient(rect, paint.getColor()));
                currentSend.bounds.set(rect);
            }
        });
    }

    private static XC_MethodHook drawButton(int kind) {
        return new XC_MethodHook() {
            @Override protected void beforeHookedMethod(MethodHookParam p) throws Throwable {
                View view = (View) p.thisObject;
                Canvas canvas = (Canvas) p.args[0];
                if (!canvas.isHardwareAccelerated() || !view.isAttachedToWindow()
                        || view.getWidth() <= 0 || view.getHeight() <= 0
                        || kind == 2 && !sendNew.getBoolean(view)) return;

                Button state = buttons.get(view);
                if (state == null) {
                    state = new Button(view);
                    buttons.put(view, state);
                }
                dark = (boolean) themeDark.invoke(null);
                boolean pressed = view.isPressed() && view.isEnabled();
                state.setPressed(pressed);
                p.setObjectExtra(DRAW_FRAME, state);
                state.save = canvas.save();
                state.transform(canvas, view);

                if (kind == 0) {
                    currentRoundBackground = (Drawable) roundBackground.get(view);
                    currentRound = state;
                } else if (kind == 1) {
                    state.bounds.set(0, 0, view.getWidth(), view.getHeight());
                    if (fabSub.getBoolean(view)) state.bounds.inset(4 * state.dp, 4 * state.dp);
                    state.radius = Math.min(state.bounds.width(), state.bounds.height()) / 2f;
                    if (!fabSub.getBoolean(view) && view.getOutlineProvider() != null) {
                        view.getOutlineProvider().getOutline(view, state.outline);
                        float radius = state.outline.getRadius();
                        if (radius >= 0) state.radius = radius;
                    }
                } else {
                    currentSend = state;
                    state.bounds.setEmpty();
                    state.radius = 20 * state.dp;
                }
            }

            @Override protected void afterHookedMethod(MethodHookParam p) throws Throwable {
                Button state = (Button) p.getObjectExtra(DRAW_FRAME);
                if (state == null) return;
                Canvas canvas = (Canvas) p.args[0];
                try {
                    if (kind == 0) {
                        currentRoundBackground = null;
                        currentRound = null;
                    } else if (kind == 1 && !p.hasThrowable()) {
                        state.finish(canvas);
                    } else if (kind == 2) {
                        currentSend = null;
                        if (state.sendShaderChanged) {
                            ((Paint) sendPaint.get(p.thisObject)).setShader(state.savedShader);
                            state.sendShaderChanged = false;
                            state.savedShader = null;
                        }
                        if (!p.hasThrowable()) state.finish(canvas);
                    }
                } finally {
                    canvas.restoreToCount(state.save);
                }
            }
        };
    }

    private static void invalidateTabs(ViewGroup view) {
        for (int i = 0; i < view.getChildCount(); i++) view.getChildAt(i).invalidate();
    }

    private static float dp(View view) {
        return view.getResources().getDisplayMetrics().density;
    }

    private static Field field(Class<?> owner, String name) throws ReflectiveOperationException {
        Field f = owner.getDeclaredField(name);
        f.setAccessible(true);
        return f;
    }

    private static Method method(Class<?> owner, String name, Class<?>... params)
            throws ReflectiveOperationException {
        Method m = owner.getDeclaredMethod(name, params);
        m.setAccessible(true);
        return m;
    }

    private static void hook(Class<?> owner, String name, XC_MethodHook callback, Class<?>... params)
            throws ReflectiveOperationException {
        hooks.add(XposedBridge.hookMethod(method(owner, name, params), callback));
    }

    private static void drawError(Exception error) {
        if (!loggedDrawError) {
            Log.w(TAG, "Glass drawing fell back", error);
            loggedDrawError = true;
        }
    }

    private static int opacity(int color, float alpha) {
        return (Math.round(Math.max(0, Math.min(1, alpha)) * 255) << 24) | (color & 0xFFFFFF);
    }

    private static SpringAnimation spring(FloatValueHolder holder, View view, float stiffness,
                                          float damping, float threshold) {
        WeakReference<View> ref = new WeakReference<>(view);
        SpringAnimation animation = new SpringAnimation(holder);
        animation.setMinimumVisibleChange(threshold);
        animation.setSpring(new SpringForce(0f).setStiffness(stiffness).setDampingRatio(damping));
        animation.addUpdateListener((running, value, velocity) -> {
            View attached = ref.get();
            if (attached != null) attached.invalidate();
        });
        return animation;
    }

    private static final class Sample implements GlassSurface.Backdrop {
        Object source;
        float x, y;
        int tint;
        final Rect padded = new Rect();

        boolean resolve(Drawable drawable) throws ReflectiveOperationException {
            if (drawable == null || drawable.getAlpha() == 0) return false;
            syncTheme.invoke(drawable);
            syncGlass.invoke(drawable);
            resolveSource.invoke(drawable);
            source = getSource.invoke(drawable);
            x = (float) offsetX.invoke(drawable);
            y = (float) offsetY.invoke(drawable);
            tint = backgroundColor.getInt(drawable);
            paddedBounds.invoke(drawable, padded);
            return !padded.isEmpty();
        }

        @Override public void draw(Canvas canvas, float l, float t, float r, float b)
                throws ReflectiveOperationException {
            if (source == null) return;
            canvas.translate(-x, -y);
            try {
                sourceDraw.invoke(source, canvas, l + x, t + y, r + x, b + y);
            } catch (InvocationTargetException error) {
                // Capture may be recording during a page transition. The base was recorded first.
                if (!(error.getCause() instanceof IllegalStateException)) throw error;
            }
        }
    }

    private static final class Tabs {
        final boolean stockSwipe;
        final GlassSurface panel = new GlassSurface();
        final GlassSurface indicator = new GlassSurface();
        final Sample sample = new Sample();
        final RectF panelBounds = new RectF();
        final RectF tabBounds = new RectF();
        final FloatValueHolder center = new FloatValueHolder();
        final FloatValueHolder press = new FloatValueHolder();
        final SpringAnimation centerSpring;
        final SpringAnimation pressSpring;
        final float dp;
        float target = Float.NaN;
        float touchX, touchY;
        boolean held, wasDragging, hideStock;

        Tabs(View view, boolean stockSwipe) {
            this.dp = dp(view);
            this.stockSwipe = stockSwipe;
            centerSpring = spring(center, view, 400, .75f, .25f);
            pressSpring = spring(press, view, 650, .78f, .004f);
        }

        void touch(View view, MotionEvent event) {
            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    held = true;
                    break;
                case MotionEvent.ACTION_UP:
                case MotionEvent.ACTION_CANCEL:
                    held = false;
                    break;
                case MotionEvent.ACTION_MOVE:
                    break;
                default:
                    return;
            }
            touchX = event.getX();
            touchY = event.getY();
            view.invalidate();
        }

        boolean drawPanel(Canvas canvas, ViewGroup view, Drawable drawable)
                throws ReflectiveOperationException {
            if (!sample.resolve(drawable) || !panelBounds(view)) return false;
            dark = (boolean) themeDark.invoke(null);
            int base = dark ? DEFAULT_DARK : DEFAULT_LIGHT;
            float tintAlpha = Math.max(.32f, Math.min(.54f, (sample.tint >>> 24) / 255f));
            int tint = opacity(sample.tint == 0 ? base : sample.tint, tintAlpha);
            panel.draw(canvas, panelBounds, dp, sample, base, tint, 8, 24, 24, 0,
                    held ? press.getValue() * .55f : 0, touchX, touchY, dark);
            return true;
        }

        boolean panelBounds(ViewGroup view) {
            int top = view.getHeight(), bottom = 0;
            for (int i = 0; i < view.getChildCount(); i++) {
                View item = view.getChildAt(i);
                if (item.getVisibility() != View.VISIBLE || item.getHeight() <= 0) continue;
                top = Math.min(top, item.getTop());
                bottom = Math.max(bottom, item.getBottom());
            }
            float inset = 4 * dp;
            panelBounds.set(Math.max(inset, sample.padded.left), Math.max(sample.padded.top, top - inset),
                    Math.min(view.getWidth() - inset, sample.padded.right),
                    Math.min(sample.padded.bottom, bottom + inset));
            return !panelBounds.isEmpty();
        }

        boolean drawSelection(Canvas canvas, ViewGroup view) throws ReflectiveOperationException {
            View selected = (View) findSelected.invoke(view);
            if (selected == null) {
                setHideStock(view, false);
                return false;
            }

            float selectedCenter = selected.getX() + selected.getWidth() / 2f;
            float selectedY = selected.getY() + selected.getHeight() / 2f;
            boolean drag = dragging.getBoolean(view);
            boolean animations = ValueAnimator.areAnimatorsEnabled();
            if (!animations) centerSpring.cancel();
            if (Float.isNaN(target) || !animations) center.setValue(selectedCenter);
            if (drag) {
                centerSpring.cancel();
                center.setValue(dragX.getFloat(view) + dragOffset.getFloat(view));
            } else if (animations && (target != selectedCenter || wasDragging)) {
                centerSpring.animateToFinalPosition(selectedCenter);
            }
            target = selectedCenter;
            wasDragging = drag;

            boolean tracking = (held && Math.abs(touchX - selectedCenter) <= selected.getWidth() / 2f) || drag;
            float targetPress = tracking && animations ? 1f : 0f;
            if (!animations) {
                pressSpring.cancel();
                press.setValue(0);
            } else if (pressSpring.getSpring().getFinalPosition() != targetPress) {
                pressSpring.animateToFinalPosition(targetPress);
            }
            float amount = Math.max(0, Math.min(1, press.getValue()));
            float cx = center.getValue();
            // Cap the stretch at the edge of the panel to keep the glass out of the system inset.
            float stretch = 1f + .15f * amount;
            float w = Math.min(panelBounds.width() - 4 * dp, (selected.getWidth() - 4 * dp) * stretch);
            float h = Math.min(panelBounds.height() - 4 * dp, selected.getHeight() * (.88f + .17f * amount));
            if (w <= 0 || h <= 0) {
                setHideStock(view, false);
                return false;
            }
            cx = Math.max(panelBounds.left + 2 * dp + w / 2, Math.min(panelBounds.right - 2 * dp - w / 2, cx));
            float cy = Math.max(panelBounds.top + 2 * dp + h / 2,
                    Math.min(panelBounds.bottom - 2 * dp - h / 2, selectedY));
            tabBounds.set(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2);
            int base = dark ? DEFAULT_DARK : DEFAULT_LIGHT;
            int tint = dark ? opacity(0xFF94BFFF, .13f + .11f * amount)
                            : opacity(0xFF5675A1, .12f + .10f * amount);
            indicator.draw(canvas, tabBounds, dp, sample, base, tint, 0,
                    10, 14, .25f + .5f * amount, amount, cx, cy, dark);
            setHideStock(view, true);
            return true;
        }

        void setHideStock(ViewGroup view, boolean hide) {
            if (hideStock == hide) return;
            hideStock = hide;
            invalidateTabs(view);
        }
    }

    private static final class Button {
        final WeakReference<View> view;
        final float dp;
        final GlassSurface surface = new GlassSurface();
        final Sample sample = new Sample();
        final RectF bounds = new RectF();
        final FloatValueHolder press = new FloatValueHolder();
        final SpringAnimation pressSpring;
        final Outline outline = new Outline();
        float radius;
        Shader savedShader;
        boolean sendShaderChanged;
        LinearGradient gradient;
        float gradientTop, gradientBottom;
        int gradientColor;
        int save;

        Button(View view) {
            this.view = new WeakReference<>(view);
            dp = dp(view);
            pressSpring = spring(press, view, 500, .68f, .004f);
        }

        void setPressed(boolean pressed) {
            if (!ValueAnimator.areAnimatorsEnabled()) {
                pressSpring.cancel();
                press.setValue(0f);
                return;
            }
            float value = pressed ? 1f : 0f;
            if (pressSpring.getSpring().getFinalPosition() != value) pressSpring.animateToFinalPosition(value);
        }

        void transform(Canvas canvas, View view) {
            float cx = view.getWidth() / 2f;
            float cy = view.getHeight() / 2f;
            float scale = press.getValue() * Math.min(.11f, 4 * dp / view.getHeight());
            canvas.scale(1 + scale, 1 + scale, cx, cy);
        }

        boolean drawRound(Canvas canvas, Drawable drawable) throws ReflectiveOperationException {
            if (!sample.resolve(drawable)) return false;
            bounds.set(sample.padded);
            int base = dark ? DEFAULT_DARK : DEFAULT_LIGHT;
            int tint = opacity(sample.tint == 0 ? base : sample.tint,
                    Math.max(.24f, Math.min(.68f, (sample.tint >>> 24) / 255f)));
            surface.draw(canvas, bounds, dp, sample, base, tint, 2, 12, 24, .20f,
                    press.getValue(), bounds.centerX(), bounds.centerY(), dark);
            return true;
        }

        LinearGradient gradient(RectF rect, int color) {
            if (gradient == null || gradientTop != rect.top || gradientBottom != rect.bottom
                    || gradientColor != color) {
                gradientTop = rect.top;
                gradientBottom = rect.bottom;
                gradientColor = color;
                gradient = new LinearGradient(0, rect.top, 0, rect.bottom,
                        new int[]{mix(color, 255, .10f), color, mix(color, 0, .15f)},
                        new float[]{0, .45f, 1}, Shader.TileMode.CLAMP);
            }
            return gradient;
        }

        void finish(Canvas canvas) {
            surface.finish(canvas, bounds, radius, dp,
                    press.getValue(), bounds.centerX(), bounds.centerY(), dark);
        }

        private static int mix(int color, int channel, float weight) {
            int r = Math.round(((color >>> 16) & 255) * (1 - weight) + channel * weight);
            int g = Math.round(((color >>> 8) & 255) * (1 - weight) + channel * weight);
            int b = Math.round((color & 255) * (1 - weight) + channel * weight);
            return color & 0xFF000000 | r << 16 | g << 8 | b;
        }
    }
}
