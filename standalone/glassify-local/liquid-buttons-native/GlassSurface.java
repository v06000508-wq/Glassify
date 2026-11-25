package glassify.kyant;

import android.graphics.BlendMode;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ColorMatrix;
import android.graphics.ColorMatrixColorFilter;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RadialGradient;
import android.graphics.RectF;
import android.graphics.RenderEffect;
import android.graphics.RenderNode;
import android.graphics.RuntimeShader;
import android.graphics.Shader;

final class GlassSurface {
    private static final float BLUR_DP = 2f;
    private static final float REFRACTION_DP = 24f;
    private static final float DISPERSION = .52f;
    private static final ColorMatrixColorFilter VIBRANCY;
    static {
        ColorMatrix matrix = new ColorMatrix();
        matrix.setSaturation(1.4f);
        VIBRANCY = new ColorMatrixColorFilter(matrix);
    }

    interface Backdrop {
        void draw(Canvas canvas, float l, float t, float r, float b)
                throws ReflectiveOperationException;
    }

    private final float edgeStrength;
    private final RenderNode node = new RenderNode("Glassify Kyant backdrop");
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path shape = new Path();
    private final Path edge = new Path();
    private final RectF edgeBounds = new RectF();
    private final RectF previousBounds = new RectF();
    private final float[] radii = new float[8];
    private final float[] innerRadii = new float[8];
    private final Matrix glowMatrix = new Matrix();
    private RadialGradient glow;
    private RuntimeShader lens;
    private RuntimeShader rim;
    private RenderEffect inputEffect;
    private boolean shaderFailed;
    private boolean rimFailed;
    private boolean effectDirty = true;
    private boolean rimDirty = true;

    GlassSurface(float edgeStrength) {
        this.edgeStrength = edgeStrength;
    }

    void draw(Canvas canvas, RectF bounds, float dp, Backdrop source, int base, int tint,
              float[] corners, float press, float touchX, float touchY, boolean dark)
            throws ReflectiveOperationException {
        if (bounds.isEmpty()) return;
        updateShape(bounds, corners, dp);
        paint.setColor(base);
        if (source != null) {
            paint.setShadowLayer(4 * dp, 0, dp, dark ? 0x43000000 : 0x24000000);
        }
        canvas.drawPath(shape, paint);
        paint.clearShadowLayer();

        if (source != null && canvas.isHardwareAccelerated() && !shaderFailed) {
            drawBackdrop(canvas, bounds, dp, source, base);
        }

        paint.setColor(tint);
        canvas.drawPath(shape, paint);
        drawPressGlow(canvas, bounds, press, touchX, touchY);
        drawEdge(canvas, bounds, dp, press, dark);
    }

    private void updateShape(RectF bounds, float[] corners, float dp) {
        boolean changed = !previousBounds.equals(bounds);
        float maxRadius = Math.min(bounds.width(), bounds.height()) / 2f;
        for (int i = 0; i < radii.length; i++) {
            float radius = corners == null ? maxRadius : Math.min(corners[i], maxRadius);
            if (radii[i] != radius) {
                radii[i] = radius;
                changed = true;
            }
        }
        if (!changed) return;
        previousBounds.set(bounds);
        shape.rewind();
        shape.addRoundRect(bounds, radii, Path.Direction.CW);
        float inset = .29f * dp;
        edgeBounds.set(bounds);
        edgeBounds.inset(inset, inset);
        for (int i = 0; i < radii.length; i++) innerRadii[i] = Math.max(0, radii[i] - inset);
        edge.rewind();
        edge.addRoundRect(edgeBounds, innerRadii, Path.Direction.CW);
        effectDirty = true;
        rimDirty = true;
    }

    private void drawBackdrop(Canvas canvas, RectF bounds, float dp, Backdrop source, int base)
            throws ReflectiveOperationException {
        int pad = (int) Math.ceil((REFRACTION_DP * (1 + DISPERSION) + BLUR_DP * 2 + 2) * dp);
        int left = (int) Math.floor(bounds.left) - pad;
        int top = (int) Math.floor(bounds.top) - pad;
        int right = (int) Math.ceil(bounds.right) + pad;
        int bottom = (int) Math.ceil(bounds.bottom) + pad;
        try {
            if (lens == null) {
                lens = new RuntimeShader(Refraction.AGSL);
                lens.setFloatUniform("depthEffect", .15f);
                lens.setFloatUniform("refractionHeight", 12 * dp);
                lens.setFloatUniform("refractionAmount", -REFRACTION_DP * dp);
                lens.setFloatUniform("chromaticAberration", DISPERSION);
                inputEffect = RenderEffect.createBlurEffect(BLUR_DP * dp, BLUR_DP * dp,
                        RenderEffect.createColorFilterEffect(VIBRANCY), Shader.TileMode.CLAMP);
            }
            // The touch transform belongs to the outer Canvas. Optics and the effect stay
            // reusable as long as the drawable's native bounds and corners stay the same.
            if (effectDirty) {
                lens.setFloatUniform("size", bounds.width(), bounds.height());
                lens.setFloatUniform("offset", left - bounds.left, top - bounds.top);
                lens.setFloatUniform("cornerRadii", radii[0], radii[2], radii[4], radii[6]);
                RenderEffect effect = RenderEffect.createRuntimeShaderEffect(lens, "content");
                node.setRenderEffect(RenderEffect.createChainEffect(effect, inputEffect));
                node.setPosition(left, top, right, bottom);
                effectDirty = false;
            }
        } catch (IllegalArgumentException | IllegalStateException error) {
            shaderFailed = true;
            android.util.Log.w("GlassifyKyant", "Lens unavailable", error);
            return;
        }
        Canvas recording = node.beginRecording(right - left, bottom - top);
        try {
            recording.drawColor(base);
            recording.translate(-left, -top);
            source.draw(recording, left, top, right, bottom);
        } catch (IllegalStateException unavailable) {
            // A live source can already be recording this frame. Retry the next draw.
            return;
        } finally {
            node.endRecording();
        }
        int save = canvas.save();
        try {
            canvas.clipPath(shape);
            canvas.drawRenderNode(node);
        } finally {
            canvas.restoreToCount(save);
        }
    }

    private void updateRimShape(RectF bounds) {
        rim.setFloatUniform("origin", bounds.left, bounds.top);
        rim.setFloatUniform("size", bounds.width(), bounds.height());
        rim.setFloatUniform("cornerRadii", radii[0], radii[2], radii[4], radii[6]);
    }

    private void drawEdge(Canvas canvas, RectF bounds, float dp, float press, boolean dark) {
        if (edgeBounds.isEmpty() || !canvas.isHardwareAccelerated() || rimFailed) return;
        try {
            if (rim == null) {
                rim = new RuntimeShader(Refraction.HIGHLIGHT);
                rim.setFloatUniform("angle", (float) (-Math.PI / 3));
                rim.setFloatUniform("falloff", 3.5f);
                rim.setColorUniform("color", Color.WHITE);
            }
            if (rimDirty) {
                updateRimShape(bounds);
                rimDirty = false;
            }
            float strength = Math.min(1f, edgeStrength * (1f + .24f * press));
            paint.setColor(Color.WHITE);
            paint.setAlpha(Math.round((dark ? 164 : 197) * strength));
            paint.setShader(rim);
            paint.setStrokeWidth(.55f * dp);
            paint.setStyle(Paint.Style.STROKE);
            canvas.drawPath(edge, paint);
        } catch (IllegalArgumentException | IllegalStateException error) {
            rimFailed = true;
            android.util.Log.w("GlassifyKyant", "Highlight shader unavailable", error);
        } finally {
            paint.setStyle(Paint.Style.FILL);
            paint.setShader(null);
        }
    }

    private void drawPressGlow(Canvas canvas, RectF bounds, float press, float touchX, float touchY) {
        if (press <= .01f) return;
        if (glow == null) {
            glow = new RadialGradient(0, 0, 1,
                    new int[]{Color.WHITE, Color.WHITE, 0x00FFFFFF},
                    new float[]{0, .48f, 1}, Shader.TileMode.CLAMP);
        }
        float progress = Math.min(1f, press);
        paint.setBlendMode(BlendMode.PLUS);
        paint.setColor(Color.WHITE);
        paint.setAlpha(Math.round(20 * progress));
        canvas.drawPath(shape, paint);

        float spread = Math.min(bounds.width(), bounds.height()) * 1.5f;
        glowMatrix.setScale(spread, spread);
        glowMatrix.postTranslate(touchX, touchY);
        glow.setLocalMatrix(glowMatrix);
        paint.setAlpha(Math.round(38 * progress));
        paint.setShader(glow);
        canvas.drawPath(shape, paint);
        paint.setShader(null);
        paint.setBlendMode(null);
    }
}
