package glassify.kyant;

import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ColorMatrix;
import android.graphics.ColorMatrixColorFilter;
import android.graphics.BlendMode;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RadialGradient;
import android.graphics.RectF;
import android.graphics.RenderEffect;
import android.graphics.RenderNode;
import android.graphics.RuntimeShader;
import android.graphics.Shader;

final class GlassSurface {
    private final float edgeStrength;

    GlassSurface(float edgeStrength) {
        this.edgeStrength = edgeStrength;
    }
    interface Backdrop {
        void draw(Canvas canvas, float l, float t, float r, float b)
                throws ReflectiveOperationException;
    }

    private static final ColorMatrixColorFilter VIBRANCY;
    static {
        ColorMatrix matrix = new ColorMatrix();
        matrix.setSaturation(1.4f);
        VIBRANCY = new ColorMatrixColorFilter(matrix);
    }

    private final RenderNode node = new RenderNode("Glassify Kyant backdrop");
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path clip = new Path();
    private RuntimeShader lens;
    private float blur = -1;
    private boolean shaderFailed;
    private RuntimeShader rim;
    private boolean rimFailed;

    void draw(Canvas canvas, RectF bounds, float dp, Backdrop source, int base, int tint,
              float blurDp, float heightDp, float amountDp, float dispersion,
              float press, float touchX, float touchY, boolean dark) throws ReflectiveOperationException {
        if (bounds.isEmpty()) return;
        float radius = Math.min(bounds.width(), bounds.height()) / 2f;
        paint.setColor(base);
        if (source != null) {
            paint.setShadowLayer(4 * dp, 0, dp, dark ? 0x43000000 : 0x24000000);
        }
        canvas.drawRoundRect(bounds, radius, radius, paint);
        paint.clearShadowLayer();

        if (source != null && canvas.isHardwareAccelerated() && !shaderFailed) {
            int pad = (int) Math.ceil((amountDp * 1.8f + blurDp * 2 + 2) * dp);
            int left = (int) Math.floor(bounds.left) - pad;
            int top = (int) Math.floor(bounds.top) - pad;
            int right = (int) Math.ceil(bounds.right) + pad;
            int bottom = (int) Math.ceil(bounds.bottom) + pad;
            try {
                if (lens == null) lens = new RuntimeShader(Refraction.AGSL);
                lens.setFloatUniform("size", bounds.width(), bounds.height());
                lens.setFloatUniform("offset", left - bounds.left, top - bounds.top);
                lens.setFloatUniform("cornerRadii", radius, radius, radius, radius);
                lens.setFloatUniform("refractionHeight", heightDp * dp);
                lens.setFloatUniform("refractionAmount", -amountDp * dp);
                lens.setFloatUniform("depthEffect", .15f);
                lens.setFloatUniform("chromaticAberration", dispersion);

                RenderEffect effect = RenderEffect.createRuntimeShaderEffect(lens, "content");
                if (blur != blurDp * dp) {
                    blur = blurDp * dp;
                    inputEffect = RenderEffect.createColorFilterEffect(VIBRANCY);
                    if (blur > 0) {
                        inputEffect = RenderEffect.createBlurEffect(blur, blur, inputEffect,
                                Shader.TileMode.CLAMP);
                    }
                }
                node.setRenderEffect(RenderEffect.createChainEffect(effect, inputEffect));
                node.setPosition(left, top, right, bottom);
                Canvas recording = node.beginRecording(right - left, bottom - top);
                try {
                    recording.drawColor(base);
                    recording.translate(-left, -top);
                    source.draw(recording, left, top, right, bottom);
                } finally {
                    node.endRecording();
                }
                int save = canvas.save();
                try {
                    clip.rewind();
                    clip.addRoundRect(bounds, radius, radius, Path.Direction.CW);
                    canvas.clipPath(clip);
                    canvas.drawRenderNode(node);
                } finally {
                    canvas.restoreToCount(save);
                }
            } catch (IllegalArgumentException | IllegalStateException error) {
                // Some Android GPU backends reject RuntimeShader; keep the tinted fallback.
                shaderFailed = true;
                android.util.Log.w("GlassifyKyant", "Lens unavailable", error);
            }
        }

        paint.setColor(tint);
        canvas.drawRoundRect(bounds, radius, radius, paint);
        finish(canvas, bounds, radius, dp, press, touchX, touchY, dark);
    }

    private RenderEffect inputEffect;

    private void finish(Canvas canvas, RectF bounds, float radius, float dp, float press,
                float touchX, float touchY, boolean dark) {
        if (bounds.isEmpty()) return;
        drawPressGlow(canvas, bounds, radius, press, touchX, touchY);
        drawEdge(canvas, bounds, radius, dp, press, dark);
    }

    private void drawEdge(Canvas canvas, RectF bounds, float radius, float dp, float press, boolean dark) {
        if (radius <= 0 || !canvas.isHardwareAccelerated() || rimFailed) return;
        try {
            if (rim == null) {
                rim = new RuntimeShader(Refraction.HIGHLIGHT);
                rim.setFloatUniform("angle", (float) (-Math.PI / 3));
                rim.setFloatUniform("falloff", 3.5f);
            }
            rim.setFloatUniform("origin", bounds.left, bounds.top);
            rim.setFloatUniform("size", bounds.width(), bounds.height());
            rim.setFloatUniform("cornerRadii", radius, radius, radius, radius);
            float strength = Math.min(1f, edgeStrength * (1f + .24f * press));
            int alpha = Math.round((dark ? 164 : 197) * strength);
            rim.setColorUniform("color", (alpha << 24) | 0xFFFFFF);
            paint.setColor(Color.WHITE);
            paint.setShader(rim);
            paint.setStrokeWidth(.55f * dp);
            paint.setStyle(Paint.Style.STROKE);
            float inset = .29f * dp;
            float innerRadius = Math.max(0f, radius - inset);
            canvas.drawRoundRect(bounds.left + inset, bounds.top + inset,
                    bounds.right - inset, bounds.bottom - inset, innerRadius, innerRadius, paint);
        } catch (IllegalArgumentException | IllegalStateException error) {
            rimFailed = true;
            android.util.Log.w("GlassifyKyant", "Highlight shader unavailable", error);
        } finally {
            paint.setStyle(Paint.Style.FILL);
            paint.setShader(null);
        }
    }

    private void drawPressGlow(Canvas canvas, RectF bounds, float radius, float press, float touchX, float touchY) {
        if (bounds.isEmpty()) return;
        if (press > .01f) {
            float progress = Math.min(1f, press);
            paint.setBlendMode(BlendMode.PLUS);
            paint.setColor(0x00FFFFFF | Math.round(20 * progress) << 24);
            canvas.drawRoundRect(bounds, radius, radius, paint);
            paint.setColor(Color.WHITE);
            int alpha = Math.round(38 * progress);
            paint.setShader(new RadialGradient(touchX, touchY,
                    Math.min(bounds.width(), bounds.height()) * 1.5f,
                    new int[]{alpha << 24 | 0xFFFFFF, alpha << 24 | 0xFFFFFF, 0x00FFFFFF},
                    new float[]{0, .48f, 1}, Shader.TileMode.CLAMP));
            canvas.drawRoundRect(bounds, radius, radius, paint);
            paint.setShader(null);
            paint.setBlendMode(null);
        }
    }
}
