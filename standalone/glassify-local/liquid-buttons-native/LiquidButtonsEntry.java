package glassify.kyant;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;

public final class LiquidButtonsEntry {
    private LiquidButtonsEntry() {}

    public static void onLoad(Context context, Object unused) throws ReflectiveOperationException {
        ReleaseButtons.load(context);
    }

    public static void setStrength(String value) {
        int strength = Integer.parseInt(value);
        if (Looper.myLooper() == Looper.getMainLooper()) {
            ReleaseButtons.setStrength(strength);
        } else {
            new Handler(Looper.getMainLooper()).post(() -> ReleaseButtons.setStrength(strength));
        }
    }

    public static void onUnload() {
        ReleaseButtons.unload();
    }
}
