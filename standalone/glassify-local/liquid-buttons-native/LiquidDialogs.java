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
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.util.TypedValue;
import android.view.Display;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.view.inspector.WindowInspector;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.lang.ref.WeakReference;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.WeakHashMap;

final class LiquidDialogs {
    private static final String UI = "org.telegram.ui.ActionBar.";
    private static final String FLAGS = "kyant.dialog.nativeFlags";
    private static final int[] ROLES = {DialogInterface.BUTTON_POSITIVE, DialogInterface.BUTTON_NEGATIVE,
            DialogInterface.BUTTON_NEUTRAL, -4};
    private static final WeakHashMap<View, Panel> panels = new WeakHashMap<>();

    private static Field style, backgroundColor, topView, omitTopBackground, nativeBlur, drawBackground, customDim;
    private static Field customWidth, customView, items, bottomView, starsBalance, rows, vertical, titleView, messageView;
    private static Field[] actionLabels, headerAssets;
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
        customWidth = ReleaseButtons.field(type, "customWidth");
        customView = ReleaseButtons.field(type, "customView");
        items = ReleaseButtons.field(type, "items");
        bottomView = ReleaseButtons.field(type, "bottomView");
        starsBalance = ReleaseButtons.field(type, "needStarsBalance");
        rows = ReleaseButtons.field(type, "buttonsLayout");
        vertical = ReleaseButtons.field(type, "verticalButtons");
        titleView = ReleaseButtons.field(type, "titleTextView");
        messageView = ReleaseButtons.field(type, "messageTextView");
        actionLabels = new Field[]{ReleaseButtons.field(type, "positiveButtonText"),
                ReleaseButtons.field(type, "negativeButtonText"), ReleaseButtons.field(type, "neutralButtonText"),
                ReleaseButtons.field(type, "negative2ButtonText")};
        headerAssets = new Field[]{ReleaseButtons.field(type, "topResId"),
                ReleaseButtons.field(type, "topAnimationId"), ReleaseButtons.field(type, "topDrawable")};
        getContainer = type.getMethod("getContainerView");
        getButton = type.getMethod("getButton", int.class);
        findActivity = loader.loadClass("org.telegram.messenger.AndroidUtilities")
                .getMethod("findActivity", Context.class);

        ReleaseButtons.installDialogActionMotion(loader.loadClass(UI + "TextViewWithLoading"));
        ReleaseButtons.hook(type, "getDialogWidth", new ReleaseButtons.UiHook() {
            @Override void after(MethodHookParam p) throws ReflectiveOperationException {
                Dialog dialog = (Dialog) p.thisObject;
                if (p.hasThrowable() || !plainAlert(dialog) || !ReleaseButtons.glassActive()) return;
                View view = (View) getContainer.invoke(dialog);
                if (view == null) return;
                int padding = view.getPaddingLeft() + view.getPaddingRight();
                p.setResult(Math.min((int) p.getResult(), px(dialog, 300) + padding));
            }
        });
        ReleaseButtons.hook(type, "inflateContent", new ReleaseButtons.UiHook() {
            @Override void before(MethodHookParam p) throws ReflectiveOperationException {
                Dialog dialog = (Dialog) p.thisObject;
                if (plainAlert(dialog) && ReleaseButtons.glassActive() && stackActions(dialog)) {
                    p.setObjectExtra(FLAGS, vertical.getBoolean(dialog));
                    vertical.setBoolean(dialog, true);
                }
            }
            @Override void after(MethodHookParam p) throws ReflectiveOperationException {
                try {
                    if (!p.hasThrowable()) prepare((Dialog) p.thisObject);
                } finally {
                    if (p.getObjectExtra(FLAGS) instanceof Boolean prior) vertical.setBoolean(p.thisObject, prior);
                }
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
        boolean dark = Color.luminance(backgroundColor.getInt(dialog) | 0xFF000000) < .30f;
        for (int role : ROLES) {
            if (getButton.invoke(dialog, role) instanceof View action) {
                panel.actions.add(new ActionStyle(action));
                ReleaseButtons.bindDialogAction(action, role == DialogInterface.BUTTON_POSITIVE, dark);
            }
        }
        if (plainAlert(dialog)) panel.configureLayout(dialog);
    }

    private static int px(Dialog dialog, float dp) {
        return Math.round(dp * dialog.getContext().getResources().getDisplayMetrics().density);
    }

    private static boolean plainAlert(Dialog dialog) throws IllegalAccessException {
        if (style.getInt(dialog) != 0 || customWidth.getInt(dialog) > 0 || customView.get(dialog) != null
                || items.get(dialog) != null || bottomView.get(dialog) != null || topView.get(dialog) != null
                || starsBalance.getBoolean(dialog)) return false;
        for (Field asset : headerAssets) {
            Object value = asset.get(dialog);
            if (value != null && (!(value instanceof Integer resource) || resource != 0)) return false;
        }
        return true;
    }

    private static boolean stackActions(Dialog dialog) throws IllegalAccessException {
        Paint measure = new Paint(Paint.ANTI_ALIAS_FLAG);
        measure.setTypeface(Typeface.DEFAULT_BOLD);
        measure.setTextSize(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, 16,
                dialog.getContext().getResources().getDisplayMetrics()));
        int viewport = dialog.getContext().getResources().getDisplayMetrics().widthPixels;
        int bodyWidth = Math.min(px(dialog, 300), viewport - px(dialog, 56));
        int half = Math.max(1, (bodyWidth - px(dialog, 40)) / 2);
        int count = 0;
        boolean longLabel = false;
        for (Field label : actionLabels) {
            if (label.get(dialog) instanceof CharSequence text) {
                count++;
                if (measure.measureText(text, 0, text.length()) + px(dialog, 24) > half) longLabel = true;
            }
        }
        return count == 1 || count > 2 || longLabel;
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

    private static final class ActionStyle {
        final WeakReference<View> view;
        final int width, height;
        ActionStyle(View view) {
            this.view = new WeakReference<>(view);
            width = view.getLayoutParams().width;
            height = view.getLayoutParams().height;
        }
        void restore() {
            View action = view.get();
            if (action == null) return;
            action.getLayoutParams().width = width;
            action.getLayoutParams().height = height;
            action.requestLayout();
            ReleaseButtons.unbindDialogAction(action);
        }
    }

    private static final class Panel extends Drawable implements GlassSurface.Backdrop {
        final WeakReference<Dialog> dialog;
        final WeakReference<View> view;
        final Drawable stock;
        final GlassSurface surface = new GlassSurface(.22f, 2);
        final ArrayList<ActionStyle> actions = new ArrayList<>();
        WeakReference<ViewGroup> row;
        int rowHeight;
        final Rect rowPadding = new Rect();
        WeakReference<TextView> title, message;
        float titleSize, messageSize;
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

        void configureLayout(Dialog dialog) throws IllegalAccessException {
            if (titleView.get(dialog) instanceof TextView text) {
                title = new WeakReference<>(text);
                titleSize = text.getTextSize();
                text.setTextSize(TypedValue.COMPLEX_UNIT_SP, 17);
            }
            if (messageView.get(dialog) instanceof TextView text) {
                message = new WeakReference<>(text);
                messageSize = text.getTextSize();
                text.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15);
            }
            if (!(rows.get(dialog) instanceof ViewGroup group) || actions.isEmpty()) return;
            row = new WeakReference<>(group);
            rowHeight = group.getLayoutParams().height;
            rowPadding.set(group.getPaddingLeft(), group.getPaddingTop(), group.getPaddingRight(), group.getPaddingBottom());
            boolean stacked = group instanceof LinearLayout;
            int viewport = dialog.getContext().getResources().getDisplayMetrics().widthPixels;
            int bodyWidth = Math.min(px(dialog, 300), viewport - px(dialog, 56));
            int side = px(dialog, 16);
            int half = Math.max(1, (bodyWidth - side * 2 - px(dialog, 8)) / 2);
            group.setPadding(side, px(dialog, 4), side, side);
            group.getLayoutParams().height = stacked ? ViewGroup.LayoutParams.WRAP_CONTENT : px(dialog, 68);
            for (ActionStyle entry : actions) {
                View action = entry.view.get();
                if (action == null) continue;
                action.getLayoutParams().height = px(dialog, 48);
                if (!stacked && actions.size() == 2) action.getLayoutParams().width = half;
                action.requestLayout();
            }
            group.requestLayout();
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
                float scale = .80f + .40f * strength / 100f;
                optics = new GlassSurface.Optics((dark ? 28 : 30) * scale, 10 * scale, 7 * scale, 0);
            }
            float radius = Math.min(35 * dp, Math.min(bounds.width(), bounds.height()) / 2f);
            for (int i = 0; i < corners.length; i++) corners[i] = radius;
            owner.getLocationOnScreen(location);
            if (snapshot != null) {
                int x = snapshot.x - location[0], y = snapshot.y - location[1];
                if (snapshotToken == null || imageBounds.left != x || imageBounds.top != y) {
                    imageBounds.set(x, y, x + snapshot.width, y + snapshot.height);
                    snapshotToken = new Object();
                }
            }
            int tint = (color & 0x00FFFFFF) | (dark ? 0xD9000000 : 0xC4000000);
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
                appliedDim = .20f;
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
            ViewGroup group = row == null ? null : row.get();
            if (group != null) {
                group.getLayoutParams().height = rowHeight;
                group.setPadding(rowPadding.left, rowPadding.top, rowPadding.right, rowPadding.bottom);
                group.requestLayout();
            }
            TextView titleText = title == null ? null : title.get();
            TextView messageText = message == null ? null : message.get();
            if (titleText != null) titleText.setTextSize(TypedValue.COMPLEX_UNIT_PX, titleSize);
            if (messageText != null) messageText.setTextSize(TypedValue.COMPLEX_UNIT_PX, messageSize);
            actions.forEach(ActionStyle::restore);
            actions.clear();
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
