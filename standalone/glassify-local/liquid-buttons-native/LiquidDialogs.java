package glassify.kyant;

import android.app.Activity;
import android.app.Dialog;
import android.content.Context;
import android.content.DialogInterface;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.drawable.Drawable;
import android.view.Display;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.view.inspector.WindowInspector;

import java.lang.ref.WeakReference;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.WeakHashMap;

final class LiquidDialogs {
    private static final String UI = "org.telegram.ui.ActionBar.";
    private static final String FLAGS = "kyant.dialog.nativeFlags";
    private static final WeakHashMap<View, Panel> panels = new WeakHashMap<>();

    private static Field style, backgroundColor, topView, omitTopBackground, nativeBlur, drawBackground, customDim;
    private static Method getContainer, getButton, findActivity;

    static void install(ClassLoader loader) throws ReflectiveOperationException {
        Class<?> type = loader.loadClass(UI + "AlertDialog");
        Class<?> viewType = loader.loadClass(UI + "AlertDialog$AlertDialogView");
        style = ReleaseButtons.field(type, "progressViewStyle");
        backgroundColor = ReleaseButtons.field(type, "backgroundColor");
        topView = ReleaseButtons.field(type, "topView");
        omitTopBackground = ReleaseButtons.field(type, "notDrawBackgroundOnTopView");
        nativeBlur = ReleaseButtons.field(type, "blurredNativeBackground");
        drawBackground = ReleaseButtons.field(type, "drawBackground");
        customDim = ReleaseButtons.field(type, "dimCustom");
        getContainer = type.getMethod("getContainerView");
        getButton = type.getMethod("getButton", int.class);
        findActivity = loader.loadClass("org.telegram.messenger.AndroidUtilities")
                .getMethod("findActivity", Context.class);

        ReleaseButtons.installDialogActionMotion(loader.loadClass(UI + "TextViewWithLoading"));
        ReleaseButtons.hook(type, "inflateContent", new ReleaseButtons.UiHook() {
            @Override void after(MethodHookParam p) throws ReflectiveOperationException {
                if (!p.hasThrowable()) prepare((Dialog) p.thisObject);
            }
        }, boolean.class);
        ReleaseButtons.hook(type, "show", new ReleaseButtons.UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                Dialog dialog = (Dialog) p.thisObject;
                if (!dialog.isShowing()) prepare(dialog);
            }
        });
        ReleaseButtons.hook(type, "dismiss", new ReleaseButtons.UiHook() {
            @Override void after(MethodHookParam p) throws ReflectiveOperationException {
                Dialog dialog = (Dialog) p.thisObject;
                if (dialog.isShowing()) return;
                View view = (View) getContainer.invoke(dialog);
                Panel panel = panels.remove(view);
                if (panel != null) panel.restore(view);
            }
        });
        ReleaseButtons.hook(viewType, "draw", new ReleaseButtons.UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                View view = (View) p.thisObject;
                Panel panel = panels.get(view);
                if (panel == null || view.getBackground() != panel) return;
                if (!((Canvas) p.args[0]).isHardwareAccelerated()) return;
                if (!ReleaseButtons.glassActive()) {
                    panel.restoreDim();
                    return;
                }
                Dialog dialog = panel.dialog.get();
                if (dialog == null) return;
                panel.applyDim();
                p.setObjectExtra(FLAGS, new NativeFlags(dialog, nativeBlur.getBoolean(dialog), drawBackground.getBoolean(dialog)));
                nativeBlur.setBoolean(dialog, true);
                drawBackground.setBoolean(dialog, false);
            }

            @Override void after(MethodHookParam p) throws ReflectiveOperationException {
                if (p.getObjectExtra(FLAGS) instanceof NativeFlags prior) {
                    nativeBlur.setBoolean(prior.dialog, prior.blur);
                    drawBackground.setBoolean(prior.dialog, prior.background);
                }
            }
        }, Canvas.class);
    }

    private static void prepare(Dialog dialog) throws ReflectiveOperationException {
        // Native message and linear-progress windows share this layout.
        int kind = style.getInt(dialog);
        if (kind != 0 && kind != 2) return;
        View view = (View) getContainer.invoke(dialog);
        if (view == null || panels.containsKey(view) || !ReleaseButtons.glassActive()) return;
        Panel panel = new Panel(dialog, view, capture(dialog));
        panels.put(view, panel);
        setBackground(view, panel);
        panel.applyDim();
        for (int role : new int[]{DialogInterface.BUTTON_POSITIVE, DialogInterface.BUTTON_NEGATIVE,
                DialogInterface.BUTTON_NEUTRAL, -4}) {
            ReleaseButtons.bindDialogAction((View) getButton.invoke(dialog, role), role == DialogInterface.BUTTON_POSITIVE);
        }
    }

    private static Snapshot capture(Dialog dialog) throws ReflectiveOperationException {
        Activity activity = (Activity) findActivity.invoke(null, dialog.getContext());
        if (activity == null || activity.getWindow() == null) return null;
        View root = activity.getWindow().peekDecorView();
        if (root == null || root.getWidth() <= 0 || root.getHeight() <= 0) return null;
        Bitmap bitmap = Bitmap.createBitmap(Math.max(1, root.getWidth() / 4),
                Math.max(1, root.getHeight() / 4), Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        canvas.scale(bitmap.getWidth() / (float) root.getWidth(), bitmap.getHeight() / (float) root.getHeight());
        int[] location = new int[2];
        root.getLocationOnScreen(location);
        try {
            canvas.drawColor(backgroundColor.getInt(dialog));
            root.draw(canvas);
        } catch (RuntimeException unavailable) {
            return null;
        }
        View own = dialog.getWindow() == null ? null : dialog.getWindow().peekDecorView();
        Display display = root.getDisplay();
        int[] layerPosition = new int[2];
        boolean afterActivity = false;
        for (View layer : WindowInspector.getGlobalWindowViews()) {
            if (layer == own) break;
            if (layer == root) {
                afterActivity = true;
                continue;
            }
            Display layerDisplay = layer.getDisplay();
            if (!afterActivity || !layer.isShown() || display == null || layerDisplay == null
                    || layerDisplay.getDisplayId() != display.getDisplayId()
                    || findActivity.invoke(null, layer.getContext()) != activity) continue;
            if (!(layer.getLayoutParams() instanceof WindowManager.LayoutParams params)
                    || params.type >= WindowManager.LayoutParams.FIRST_SYSTEM_WINDOW) continue;
            if ((params.flags & WindowManager.LayoutParams.FLAG_DIM_BEHIND) != 0) {
                canvas.drawColor(Math.round(255 * params.dimAmount) << 24);
            }
            layer.getLocationOnScreen(layerPosition);
            int save = canvas.save();
            try {
                canvas.translate(layerPosition[0] - location[0], layerPosition[1] - location[1]);
                layer.draw(canvas);
            } catch (RuntimeException unavailable) {
                // Surfaces backed by a separate compositor layer may not have a software draw path.
            } finally {
                canvas.restoreToCount(save);
            }
        }
        return new Snapshot(bitmap, location[0], location[1], root.getWidth(), root.getHeight());
    }

    private static void setBackground(View view, Drawable background) {
        int left = view.getPaddingLeft(), top = view.getPaddingTop();
        int right = view.getPaddingRight(), bottom = view.getPaddingBottom();
        view.setBackground(background);
        view.setPadding(left, top, right, bottom);
    }

    static void invalidate() { panels.keySet().forEach(View::postInvalidateOnAnimation); }

    static void unload() {
        panels.forEach((view, panel) -> panel.restore(view));
        panels.clear();
    }

    private record Snapshot(Bitmap bitmap, int x, int y, int width, int height) {}
    private record NativeFlags(Dialog dialog, boolean blur, boolean background) {}

    private static final class Panel extends Drawable implements GlassSurface.Backdrop {
        final WeakReference<Dialog> dialog;
        final WeakReference<View> view;
        final Drawable stock;
        final GlassSurface surface = new GlassSurface(.52f, 2);
        final RectF bounds = new RectF(), imageBounds = new RectF();
        final Paint imagePaint = new Paint(Paint.FILTER_BITMAP_FLAG);
        final float[] corners = new float[8];
        final int[] location = new int[2];
        Snapshot snapshot;
        Object snapshotToken;
        GlassSurface.Optics optics;
        boolean dark;
        int strength;
        int alpha = 255;
        float originalDim = -1, appliedDim;

        Panel(Dialog dialog, View view, Snapshot snapshot) {
            this.dialog = new WeakReference<>(dialog);
            this.view = new WeakReference<>(view);
            this.stock = view.getBackground();
            this.snapshot = snapshot;
        }

        @Override public void draw(Canvas canvas) {
            View owner = view.get();
            Dialog windowOwner = dialog.get();
            if (owner != null && windowOwner != null && canvas.isHardwareAccelerated() && alpha > 0) {
                try {
                    if (ReleaseButtons.glassActive()) {
                        drawGlass(canvas, owner, windowOwner);
                        return;
                    }
                } catch (ReflectiveOperationException | RuntimeException error) {
                    ReleaseButtons.report(error);
                }
            }
            if (stock != null) {
                stock.setState(getState());
                stock.setBounds(getBounds());
                stock.draw(canvas);
            }
        }

        private void drawGlass(Canvas canvas, View owner, Dialog windowOwner) throws ReflectiveOperationException {
            float top = owner.getPaddingTop();
            if (omitTopBackground.getBoolean(windowOwner) && topView.get(windowOwner) instanceof View image) {
                top = Math.max(top, image.getBottom());
            }
            bounds.set(owner.getPaddingLeft(), top, owner.getWidth() - owner.getPaddingRight(),
                    owner.getHeight() - owner.getPaddingBottom());
            if (bounds.isEmpty()) return;

            int color = backgroundColor.getInt(windowOwner) | 0xFF000000;
            boolean darkTheme = Color.luminance(color) < .30f;
            float dp = owner.getResources().getDisplayMetrics().density;
            int currentStrength = ReleaseButtons.strength();
            if (optics == null || strength != currentStrength || dark != darkTheme) {
                strength = currentStrength;
                dark = darkTheme;
                float scale = .60f + .80f * strength / 100f;
                optics = new GlassSurface.Optics((dark ? 8 : 16) * scale, 24 * scale, 48 * scale, 0);
            }
            float radius = Math.min(48 * dp, Math.min(bounds.width(), bounds.height()) / 2f);
            for (int i = 0; i < corners.length; i++) corners[i] = radius;
            owner.getLocationOnScreen(location);
            if (snapshot != null) {
                int x = snapshot.x - location[0], y = snapshot.y - location[1];
                if (snapshotToken == null || imageBounds.left != x || imageBounds.top != y) {
                    imageBounds.set(x, y, x + snapshot.width, y + snapshot.height);
                    snapshotToken = new Object();
                }
            }
            int tint = (color & 0x00FFFFFF) | (dark ? 0x66000000 : 0x99000000);
            surface.draw(canvas, bounds, dp, snapshot == null ? null : this, color, tint, corners,
                    optics, 0, bounds.centerX(), bounds.centerY(), dark, true, true);
        }

        @Override public Object recordingToken() { return snapshotToken; }

        @Override public void draw(Canvas canvas, float l, float t, float r, float b) {
            if (snapshot != null) canvas.drawBitmap(snapshot.bitmap, null, imageBounds, imagePaint);
        }

        void applyDim() {
            if (originalDim >= 0) return;
            Dialog owner = dialog.get();
            Window window = owner == null ? null : owner.getWindow();
            if (window == null) return;
            WindowManager.LayoutParams params = window.getAttributes();
            if ((params.flags & WindowManager.LayoutParams.FLAG_DIM_BEHIND) == 0 || params.dimAmount != .5f) return;
            try {
                if (customDim.getBoolean(owner)) return;
                originalDim = params.dimAmount;
                appliedDim = Color.luminance(backgroundColor.getInt(owner) | 0xFF000000) < .30f ? .56f : .23f;
                window.setDimAmount(appliedDim);
            } catch (IllegalAccessException error) {
                originalDim = -1;
                ReleaseButtons.report(error);
            }
        }

        void restoreDim() {
            if (originalDim < 0) return;
            Dialog owner = dialog.get();
            Window window = owner == null ? null : owner.getWindow();
            if (window != null && window.getAttributes().dimAmount == appliedDim) window.setDimAmount(originalDim);
            originalDim = -1;
        }

        void restore(View owner) {
            restoreDim();
            if (owner.getBackground() == this) setBackground(owner, stock);
            snapshot = null;
            snapshotToken = null;
        }

        @Override public boolean getPadding(Rect result) { return stock != null && stock.getPadding(result); }
        @Override public void setAlpha(int alpha) { this.alpha = alpha; invalidateSelf(); }
        @Override public void setColorFilter(ColorFilter filter) {}
        @Override public int getOpacity() { return PixelFormat.TRANSLUCENT; }
    }
}
