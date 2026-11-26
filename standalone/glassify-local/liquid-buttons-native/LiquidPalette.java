package glassify.kyant;

import android.graphics.Color;

final class LiquidPalette {
    private LiquidPalette() {}

    static boolean isColored(int color) {
        int r = Color.red(color), g = Color.green(color), b = Color.blue(color);
        int max = Math.max(r, Math.max(g, b));
        int min = Math.min(r, Math.min(g, b));
        return Color.alpha(color) > 0 && max >= 72 && max - min >= Math.max(26, max / 5);
    }

    static int accent(int preferred) {
        return isColored(preferred) ? preferred : 0xFF247AC3;
    }

    static int onAccent(int color) {
        return Color.luminance(color) > .179f ? Color.BLACK : Color.WHITE;
    }

    static boolean isDestructive(int color) {
        return isColored(color) && Color.red(color) > Color.green(color) * 1.55f
                && Color.red(color) > Color.blue(color) * 1.35f;
    }
}
