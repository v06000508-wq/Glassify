package glassify.kyant;

// Telegram iOS GlassBackgroundComponent/TouchEffect.swift.
final class ButtonMotion {
    record Transform(float x, float y, float scaleX, float scaleY) {}
    record Spring(float mass, float stiffness, float damping) {
        float androidStiffness() { return ButtonMotion.stiffness(mass, stiffness); }
        float androidDamping() { return ButtonMotion.damping(mass, stiffness, damping); }
    }

    static final Spring LIFT_ON = new Spring(1.36f, 568f, 39.7f);
    static final Spring LIFT_OFF = new Spring(2f, 460f, 21.8f);
    static final Transform REST = new Transform(0, 0, 1, 1);

    static Transform transform(float width, float height, float dp, float press, float dragX, float dragY) {
        if (width <= 0 || height <= 0) return REST;
        float base = 1 + 20 * dp / Math.max(width, height) * press;
        float aspect = width / height;
        float adjustedX = dragX / aspect;
        float length = (float) Math.hypot(adjustedX, dragY);
        if (length == 0f) return new Transform(0, 0, base, base);
        float x = adjustedX / length;
        float y = dragY / length;
        float k = length / (length + 5 * aspect * height);
        float stretch = 1 + 16 * dp / height * k * Math.abs(Math.abs(x) - Math.abs(y));
        return Math.abs(x) > Math.abs(y)
                ? new Transform(24 * dp * k * x, 24 * dp * k * y, base * stretch, base / stretch)
                : new Transform(24 * dp * k * x, 24 * dp * k * y, base / stretch, base * stretch);
    }

    static Transform interpolate(Transform from, Transform to, float fraction) {
        if (fraction == 0 || from == to) return from;
        if (fraction == 1) return to;
        // The iOS transform spring passes its target before settling.
        return new Transform(
                lerp(from.x, to.x, fraction), lerp(from.y, to.y, fraction),
                lerp(from.scaleX, to.scaleX, fraction), lerp(from.scaleY, to.scaleY, fraction));
    }

    static float lerp(float from, float to, float fraction) {
        return from + (to - from) * fraction;
    }

    static float stiffness(float mass, float stiffness) {
        return stiffness / mass;
    }

    static float damping(float mass, float stiffness, float damping) {
        return (float) (damping / (2 * Math.sqrt(mass * stiffness)));
    }
}
