package glassify.kyant;

// Geometry based on Telegram iOS GlassBackgroundComponent/TouchEffect.swift.
final class ButtonMotion {
    record Transform(float x, float y, float scaleX, float scaleY) {}

    static Transform transform(float width, float height, float dp, float press, float dragX, float dragY) {
        if (width <= 0 || height <= 0) return new Transform(0, 0, 1, 1);
        float base = 1 + 20 * dp / Math.max(width, height) * press;
        float aspect = width / height;
        float adjustedX = dragX / aspect;
        float length = (float) Math.hypot(adjustedX, dragY);
        if (length < .01f) return new Transform(0, 0, base, base);
        float x = adjustedX / length;
        float y = dragY / length;
        float k = length / (length + 5 * aspect * height);
        float stretch = 1 + 16 * dp / height * k * Math.abs(Math.abs(x) - Math.abs(y));
        return Math.abs(x) > Math.abs(y)
                ? new Transform(24 * dp * k * x, 24 * dp * k * y, base * stretch, base / stretch)
                : new Transform(24 * dp * k * x, 24 * dp * k * y, base / stretch, base * stretch);
    }

    static float stiffness(float mass, float stiffness) {
        return stiffness / mass;
    }

    static float damping(float mass, float stiffness, float damping) {
        return (float) (damping / (2 * Math.sqrt(mass * stiffness)));
    }
}
