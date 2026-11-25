package glassify.kyant;

import android.content.Context;

public final class LiquidButtonsEntry {
    private LiquidButtonsEntry() {}

    public static void onLoad(Context context, Object unused) throws ReflectiveOperationException {
        ReleaseButtons.load(context);
    }

    public static void onUnload() {
        ReleaseButtons.unload();
    }
}
