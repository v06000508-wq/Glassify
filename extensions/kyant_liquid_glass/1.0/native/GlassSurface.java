package glassify.kyant;

import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ColorMatrix;
import android.graphics.ColorMatrixColorFilter;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RadialGradient;
import android.graphics.RectF;
import android.graphics.RenderEffect;
import android.graphics.RenderNode;
import android.graphics.RuntimeShader;
import android.graphics.Shader;

final class GlassSurface {
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
    private float previousTop = Float.NaN, previousBottom;
    private boolean previousDark;
    private LinearGradient rim;

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

    void finish(Canvas canvas, RectF bounds, float radius, float dp, float press,
                float touchX, float touchY, boolean dark) {
        if (bounds.isEmpty()) return;
        if (press > .01f) {
            int alpha = (int) (Math.min(1f, press) * (dark ? 99 : 72));
            paint.setColor(Color.WHITE);
            paint.setShader(new RadialGradient(touchX, touchY,
                    Math.max(bounds.width() * .5f, bounds.height()), alpha << 24 | 0xFFFFFF,
                    0x00FFFFFF, Shader.TileMode.CLAMP));
            canvas.drawRoundRect(bounds, radius, radius, paint);
            paint.setShader(null);
        }

        if (rim == null || previousTop != bounds.top || previousBottom != bounds.bottom
                || previousDark != dark) {
            previousTop = bounds.top;
            previousBottom = bounds.bottom;
            previousDark = dark;
            rim = new LinearGradient(0, bounds.top, 0, bounds.bottom,
                    dark ? new int[]{0xA9FFFFFF, 0x1AFFFFFF, 0x62D0E2FF}
                         : new int[]{0xE7FFFFFF, 0x2AFFFFFF, 0x4E516E9D},
                    new float[]{0, .52f, 1}, Shader.TileMode.CLAMP);
        }
        paint.setColor(Color.WHITE);
        paint.setShader(rim);
        paint.setStrokeWidth(.8f * dp);
        paint.setStyle(Paint.Style.STROKE);
        float inset = .6f * dp;
        canvas.drawRoundRect(bounds.left + inset, bounds.top + inset,
                bounds.right - inset, bounds.bottom - inset,
                Math.max(0, radius - inset), Math.max(0, radius - inset), paint);
        paint.setStyle(Paint.Style.FILL);
        paint.setShader(null);
    }
}
