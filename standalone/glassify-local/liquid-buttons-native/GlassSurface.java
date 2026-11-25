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
import android.os.SystemClock;

final class GlassSurface {
    // Refraction samples inwards. The capture margin covers the blur outside the silhouette.
    static final int CAPTURE_MARGIN_DP = 24;

    record Optics(float blurDp, float bandDp, float refractionDp, float dispersion) {
        static Optics fromStrength(int strength) {
            float t = Math.max(1, Math.min(100, strength)) / 100f;
            // Telegram iOS LegacyGlassView: 2 pt blur, a 12 pt band, and 20 pt mesh displacement.
            return new Optics(1f + t + 4f * t * t * t, 4f + Math.min(8f, 16f * t),
                    6f + 36f * t - 16f * t * t, .26f * Math.max(0f, t - .5f));
        }

        int padding(float dp) {
            return (int) Math.ceil((blurDp * 3 + 2) * dp);
        }
    }

    private static final ColorMatrixColorFilter VIBRANCY;
    static {
        ColorMatrix matrix = new ColorMatrix();
        matrix.setSaturation(1.22f);
        VIBRANCY = new ColorMatrixColorFilter(matrix);
    }

    interface Backdrop {
        void draw(Canvas canvas, float l, float t, float r, float b)
                throws ReflectiveOperationException;

        // An identity for stable recordings of a native source with live child RenderNodes.
        default Object recordingToken() { return null; }
    }

    private final float edgeStrength;
    private final int downsample;
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
    private float glowX, glowY, glowSpread = -1;
    private RuntimeShader lens;
    private RuntimeShader rim;
    private RenderEffect inputEffect;
    private Optics appliedOptics;
    private Object recordedToken;
    private long recordedAt;
    private int recordedBase;
    private float maximumCorner;
    private boolean shaderFailed;
    private boolean rimFailed;
    private boolean effectDirty = true;
    private boolean rimDirty = true;

    GlassSurface(float edgeStrength, int downsample) {
        this.edgeStrength = edgeStrength;
        this.downsample = downsample;
    }

    void draw(Canvas canvas, RectF bounds, float dp, Backdrop source, int base, int tint,
              float[] corners, Optics optics, float press, float touchX, float touchY, boolean dark,
              boolean settling, boolean hasShadow)
            throws ReflectiveOperationException {
        if (bounds.isEmpty()) return;
        updateShape(bounds, corners, dp);
        paint.setColor(base);
        if (source != null && hasShadow) {
            paint.setShadowLayer(4 * dp, 0, dp, dark ? 0x43000000 : 0x24000000);
        }
        canvas.drawPath(shape, paint);
        paint.clearShadowLayer();

        if (source != null && canvas.isHardwareAccelerated() && !shaderFailed) {
            drawBackdrop(canvas, bounds, dp, source, base, optics, settling);
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
        maximumCorner = Math.max(Math.max(radii[0], radii[2]), Math.max(radii[4], radii[6]));
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

    private void drawBackdrop(Canvas canvas, RectF bounds, float dp, Backdrop source, int base, Optics optics,
                              boolean settling)
            throws ReflectiveOperationException {
        int pad = optics.padding(dp);
        int left = (int) Math.floor(bounds.left) - pad;
        int top = (int) Math.floor(bounds.top) - pad;
        int right = (int) Math.ceil(bounds.right) + pad;
        int bottom = (int) Math.ceil(bounds.bottom) + pad;
        int width = (right - left + downsample - 1) / downsample;
        int height = (bottom - top + downsample - 1) / downsample;
        float scale = 1f / downsample;
        try {
            if (lens == null) {
                lens = new RuntimeShader(Refraction.AGSL);
                lens.setFloatUniform("depthEffect", .06f);
            }
            if (optics != appliedOptics) {
                float radius = optics.blurDp * dp * scale;
                inputEffect = RenderEffect.createBlurEffect(radius, radius,
                        RenderEffect.createColorFilterEffect(VIBRANCY), Shader.TileMode.CLAMP);
                appliedOptics = optics;
                effectDirty = true;
            }
            // Touch transforms are on the outer canvas. Rebuild only for a new shape or strength.
            if (effectDirty) {
                float halfSide = Math.min(bounds.width(), bounds.height()) * .5f;
                float band = Math.min(halfSide, Math.min(optics.bandDp * dp, Math.max(dp, maximumCorner)));
                lens.setFloatUniform("refractionHeight", band * scale);
                lens.setFloatUniform("outerEdgeBand", 2 * dp * scale);
                lens.setFloatUniform("refractionAmount", -optics.refractionDp * dp * scale);
                lens.setFloatUniform("chromaticAberration", optics.dispersion);
                lens.setFloatUniform("size", bounds.width() * scale, bounds.height() * scale);
                lens.setFloatUniform("offset", (left - bounds.left) * scale, (top - bounds.top) * scale);
                lens.setFloatUniform("cornerRadii", radii[0] * scale, radii[2] * scale, radii[4] * scale, radii[6] * scale);
                RenderEffect effect = RenderEffect.createRuntimeShaderEffect(lens, "content");
                node.setRenderEffect(RenderEffect.createChainEffect(effect, inputEffect));
                node.setPosition(left, top, left + width, top + height);
                recordedToken = null;
                effectDirty = false;
            }
        } catch (IllegalArgumentException | IllegalStateException error) {
            shaderFailed = true;
            android.util.Log.w("GlassifyKyant", "Lens unavailable", error);
            return;
        }
        Object token = source.recordingToken();
        long now = token == null ? 0 : SystemClock.uptimeMillis();
        // The children remain live. Refresh their placement if scrolling changes it mid-return.
        if (!settling || token == null || token != recordedToken || base != recordedBase
                || now - recordedAt >= 32 || !node.hasDisplayList()) {
            recordedToken = null;
            Canvas recording = node.beginRecording(width, height);
            try {
                recording.drawColor(base);
                if (downsample != 1) recording.scale(scale, scale);
                recording.translate(-left, -top);
                source.draw(recording, left, top, right, bottom);
                recordedToken = token;
                recordedAt = now;
                recordedBase = base;
            } catch (IllegalStateException unavailable) {
                // A live source can already be recording this frame. Retry the next draw.
                return;
            } finally {
                node.endRecording();
            }
        }
        int save = canvas.save();
        try {
            canvas.clipPath(shape);
            if (downsample != 1) canvas.scale(downsample, downsample, left, top);
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
        if (spread != glowSpread || touchX != glowX || touchY != glowY) {
            glowMatrix.setScale(spread, spread);
            glowMatrix.postTranslate(touchX, touchY);
            glow.setLocalMatrix(glowMatrix);
            glowSpread = spread;
            glowX = touchX;
            glowY = touchY;
        }
        paint.setAlpha(Math.round(38 * progress));
        paint.setShader(glow);
        canvas.drawPath(shape, paint);
        paint.setShader(null);
        paint.setBlendMode(null);
    }
}
