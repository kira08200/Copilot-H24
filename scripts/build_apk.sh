#!/usr/bin/env bash
set -euo pipefail

SDK_ROOT="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-/usr/local/lib/android/sdk}}"
BUILD_TOOLS="$(ls -d "$SDK_ROOT/build-tools/"* | sort -V | tail -n 1)"
PLATFORM="$(ls -d "$SDK_ROOT/platforms/android-"* | sort -V | tail -n 1)"

echo "Using BUILD_TOOLS: $BUILD_TOOLS"
echo "Using PLATFORM: $PLATFORM"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="/tmp/copilote-apk-build"
rm -rf "$WORK"
mkdir -p "$WORK/res/drawable" "$WORK/assets" "$WORK/gen" "$WORK/classes" "$WORK/dex" "$WORK/src/fr/copilote/h24"

cp "$REPO_ROOT/icon-192.png" "$WORK/res/drawable/ic_launcher.png"
cp "$REPO_ROOT/index.html" "$WORK/assets/index.html"
cp "$REPO_ROOT/manifest.json" "$WORK/assets/manifest.json"
cp "$REPO_ROOT/icon-192.png" "$WORK/assets/icon-192.png"
cp "$REPO_ROOT/icon-512.png" "$WORK/assets/icon-512.png"
if [ -f "$REPO_ROOT/news.json" ]; then
  cp "$REPO_ROOT/news.json" "$WORK/assets/news.json"
fi

cat > "$WORK/AndroidManifest.xml" << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="fr.copilote.h24"
    android:versionCode="2"
    android:versionName="1.1">

    <uses-sdk android:minSdkVersion="24" android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS" />

    <application
        android:label="Copilote H24"
        android:icon="@drawable/ic_launcher"
        android:usesCleartextTraffic="true"
        android:allowBackup="true"
        android:theme="@android:style/Theme.DeviceDefault.NoActionBar">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTop"
            android:configChanges="orientation|screenSize|keyboardHidden">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        <service
            android:name=".AlertJobService"
            android:permission="android.permission.BIND_JOB_SERVICE"
            android:exported="true" />
        <receiver
            android:name=".BootAndAlarmReceiver"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
                <action android:name="android.intent.action.MY_PACKAGE_REPLACED" />
                <action android:name="fr.copilote.h24.ACTION_CHECK_NEWS" />
            </intent-filter>
        </receiver>
    </application>
</manifest>
EOF

cat > "$WORK/src/fr/copilote/h24/NotificationHelper.java" << 'EOF'
package fr.copilote.h24;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.job.JobInfo;
import android.app.job.JobScheduler;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;

public class NotificationHelper {
    public static final String CHANNEL_ID = "copilote_alerts_h24";
    public static final String PREFS_NAME = "copilote_prefs";
    public static final String KEY_BG_ENABLED = "bg_enabled";
    public static final String KEY_NOTIFIED_IDS = "notified_ids";
    public static final String KEY_SEEDED = "notified_seeded";
    public static final String ACTION_CHECK_NEWS = "fr.copilote.h24.ACTION_CHECK_NEWS";
    public static final int JOB_ID = 2401;
    public static final int NOTIF_GROUP_ID = 2402;
    public static final int ALARM_REQ_CODE = 2403;

    public static void ensureChannel(Context ctx) {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null && nm.getNotificationChannel(CHANNEL_ID) == null) {
                NotificationChannel ch = new NotificationChannel(
                    CHANNEL_ID,
                    "Alertes Copilote H24",
                    NotificationManager.IMPORTANCE_HIGH
                );
                ch.setDescription("Actualités essentielles, IPO mondiales, résultats et mouvements majeurs H24");
                ch.enableVibration(true);
                ch.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
                nm.createNotificationChannel(ch);
            }
        }
    }

    public static boolean isPermissionGranted(Context ctx) {
        if (Build.VERSION.SDK_INT < 33) return true;
        return ctx.checkSelfPermission("android.permission.POST_NOTIFICATIONS") == PackageManager.PERMISSION_GRANTED;
    }

    public static void show(Context ctx, String title, String body) {
        if (!isPermissionGranted(ctx)) return;
        ensureChannel(ctx);
        NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;

        Intent openIntent = new Intent(ctx, MainActivity.class);
        openIntent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE;
        PendingIntent pi = PendingIntent.getActivity(ctx, NOTIF_GROUP_ID, openIntent, flags);

        Notification.Builder b = (Build.VERSION.SDK_INT >= 26)
            ? new Notification.Builder(ctx, CHANNEL_ID)
            : new Notification.Builder(ctx);

        b.setSmallIcon(R.drawable.ic_launcher)
            .setContentTitle(title != null ? title : "Copilote H24")
            .setContentText(body != null ? body : "")
            .setStyle(new Notification.BigTextStyle().bigText(body != null ? body : ""))
            .setVisibility(Notification.VISIBILITY_PUBLIC)
            .setAutoCancel(true)
            .setContentIntent(pi);

        nm.notify(NOTIF_GROUP_ID, b.build());
    }

    public static boolean isBgEnabled(Context ctx) {
        SharedPreferences sp = ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        return sp.getBoolean(KEY_BG_ENABLED, false);
    }

    public static void setBgEnabled(Context ctx, boolean enabled) {
        SharedPreferences sp = ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        sp.edit().putBoolean(KEY_BG_ENABLED, enabled).apply();
        scheduleBackgroundJob(ctx, enabled);
    }

    public static void scheduleStandbyAlarm(Context ctx, boolean enabled) {
        try {
            AlarmManager am = (AlarmManager) ctx.getSystemService(Context.ALARM_SERVICE);
            if (am == null) return;
            Intent intent = new Intent(ctx, BootAndAlarmReceiver.class);
            intent.setAction(ACTION_CHECK_NEWS);
            int flags = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE;
            PendingIntent pi = PendingIntent.getBroadcast(ctx, ALARM_REQ_CODE, intent, flags);
            if (!enabled || !isPermissionGranted(ctx)) {
                am.cancel(pi);
                return;
            }
            long triggerAt = System.currentTimeMillis() + (15L * 60L * 1000L);
            if (Build.VERSION.SDK_INT >= 23) {
                am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pi);
            } else {
                am.set(AlarmManager.RTC_WAKEUP, triggerAt, pi);
            }
        } catch (Exception ignored) {}
    }

    public static void scheduleBackgroundJob(Context ctx, boolean enabled) {
        scheduleStandbyAlarm(ctx, enabled);
        JobScheduler js = (JobScheduler) ctx.getSystemService(Context.JOB_SCHEDULER_SERVICE);
        if (js == null) return;
        if (!enabled || !isPermissionGranted(ctx)) {
            js.cancel(JOB_ID);
            return;
        }
        ComponentName comp = new ComponentName(ctx, AlertJobService.class);
        JobInfo.Builder builder = new JobInfo.Builder(JOB_ID, comp)
            .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
            .setPeriodic(15L * 60L * 1000L)
            .setPersisted(true);
        js.schedule(builder.build());
    }
}
EOF

cat > "$WORK/src/fr/copilote/h24/BootAndAlarmReceiver.java" << 'EOF'
package fr.copilote.h24;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class BootAndAlarmReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(final Context context, Intent intent) {
        if (context == null) return;
        if (!NotificationHelper.isBgEnabled(context) || !NotificationHelper.isPermissionGranted(context)) {
            return;
        }
        NotificationHelper.scheduleBackgroundJob(context, true);
        final PendingResult pending = goAsync();
        AlertJobService.runCheckWithWakeLock(context.getApplicationContext(), new Runnable() {
            @Override
            public void run() {
                try {
                    pending.finish();
                } catch (Exception ignored) {}
            }
        });
    }
}
EOF

cat > "$WORK/src/fr/copilote/h24/AlertJobService.java" << 'EOF'
package fr.copilote.h24;

import android.app.job.JobParameters;
import android.app.job.JobService;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.PowerManager;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;

public class AlertJobService extends JobService {
    private static final String NEWS_URL = "https://raw.githubusercontent.com/kira08200/Copilot-H24/main/news.json?t=";
    private static final String[] KNOWN_ENTITIES = new String[]{
        "anthropic", "openai", "spacex", "databricks", "stripe", "tsmc", "asml",
        "nvidia", "air liquide", "microsoft", "alphabet", "google", "blackrock",
        "apple", "amazon", "xiaomi", "byd", "siemens", "droneshield", "microstrategy",
        "fed", "bce"
    };

    @Override
    public boolean onStartJob(final JobParameters params) {
        if (!NotificationHelper.isBgEnabled(this) || !NotificationHelper.isPermissionGranted(this)) {
            return false;
        }
        NotificationHelper.scheduleStandbyAlarm(this, true);
        runCheckWithWakeLock(getApplicationContext(), new Runnable() {
            @Override
            public void run() {
                jobFinished(params, false);
            }
        });
        return true;
    }

    @Override
    public boolean onStopJob(JobParameters params) {
        return true;
    }

    public static void runCheckWithWakeLock(final Context ctx, final Runnable onDone) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                PowerManager.WakeLock wl = null;
                try {
                    PowerManager pm = (PowerManager) ctx.getSystemService(Context.POWER_SERVICE);
                    if (pm != null) {
                        wl = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "CopiloteH24:AlertCheckWakeLock");
                        wl.acquire(20000L);
                    }
                    checkNewsStatic(ctx);
                } catch (Exception ignored) {
                } finally {
                    if (wl != null && wl.isHeld()) {
                        try { wl.release(); } catch (Exception ignored) {}
                    }
                    if (onDone != null) {
                        try { onDone.run(); } catch (Exception ignored) {}
                    }
                }
            }
        }).start();
    }

    private static String detectEntity(String title) {
        if (title == null) return "";
        String low = title.toLowerCase(Locale.ROOT);
        for (String ent : KNOWN_ENTITIES) {
            if (low.contains(ent)) {
                return "google".equals(ent) ? "alphabet" : ent;
            }
        }
        return "";
    }

    public static synchronized void checkNewsStatic(Context ctx) throws Exception {
        URL url = new URL(NEWS_URL + System.currentTimeMillis());
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setConnectTimeout(10000);
        conn.setReadTimeout(10000);
        conn.setUseCaches(false);
        conn.setRequestProperty("User-Agent", "CopiloteH24APK/1.2");
        if (conn.getResponseCode() != 200) return;

        StringBuilder sb = new StringBuilder();
        BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8));
        String line;
        while ((line = br.readLine()) != null) {
            sb.append(line);
        }
        br.close();
        conn.disconnect();

        JSONObject root = new JSONObject(sb.toString());
        SharedPreferences sp = ctx.getSharedPreferences(NotificationHelper.PREFS_NAME, Context.MODE_PRIVATE);
        boolean seeded = sp.getBoolean(NotificationHelper.KEY_SEEDED, false);
        String savedRaw = sp.getString(NotificationHelper.KEY_NOTIFIED_IDS, "");

        List<String> idList = new ArrayList<String>();
        Set<String> idSet = new HashSet<String>();
        if (savedRaw != null && savedRaw.length() > 0) {
            String[] parts = savedRaw.split(",");
            for (String p : parts) {
                if (p.length() > 0 && idSet.add(p)) {
                    idList.add(p);
                }
            }
        }

        List<String> alertTitles = new ArrayList<String>();
        List<String> alertBodies = new ArrayList<String>();

        JSONArray moves = root.optJSONArray("majorMoves");
        if (moves != null) {
            for (int i = 0; i < moves.length(); i++) {
                JSONObject mv = moves.optJSONObject(i);
                if (mv == null) continue;
                String id = "mv_" + mv.optString("id", "");
                if (id.length() <= 3 || idSet.contains(id)) continue;
                idSet.add(id);
                idList.add(id);
                if (seeded) {
                    String name = mv.optString("name", "Ligne");
                    double chg = mv.optDouble("changePct", 0.0);
                    String prefix = "drop".equals(mv.optString("kind")) ? "📉 Chute : " : "🚀 Hausse : ";
                    alertTitles.add(prefix + name + " (" + String.format(Locale.US, "%+.1f %%", chg) + ")");
                    alertBodies.add("Mouvement majeur sur votre portefeuille (" + mv.optString("weight", "") + ").");
                }
            }
        }

        JSONArray earnings = root.optJSONArray("upcomingEarnings");
        if (earnings != null) {
            for (int i = 0; i < earnings.length(); i++) {
                JSONObject er = earnings.optJSONObject(i);
                if (er == null) continue;
                int daysLeft = er.optInt("daysLeft", 99);
                if (daysLeft > 2) continue;
                String id = "er_" + er.optString("id", "");
                if (id.length() <= 3 || idSet.contains(id)) continue;
                idSet.add(id);
                idList.add(id);
                if (seeded) {
                    alertTitles.add("📊 Chiffres : " + er.optString("name", ""));
                    alertBodies.add("Publication prévue le " + er.optString("dateStr", "") + " (" + er.optString("weight", "") + ").");
                }
            }
        }

        JSONArray items = root.optJSONArray("items");
        Set<String> seenCycleEntities = new HashSet<String>();
        if (items != null) {
            for (int i = 0; i < items.length(); i++) {
                JSONObject it = items.optJSONObject(i);
                if (it == null) continue;
                String id = "nw_" + it.optString("id", "");
                if (id.length() <= 3 || idSet.contains(id)) continue;
                idSet.add(id);
                idList.add(id);
                String headline = it.optString("title", "");
                String entity = detectEntity(headline);
                if (entity.length() > 0 && !seenCycleEntities.add(entity)) {
                    continue;
                }
                if (seeded) {
                    alertTitles.add("⚡ " + it.optString("theme", "Marchés"));
                    alertBodies.add(headline);
                }
            }
        }

        if (seeded && alertTitles.size() == 1) {
            NotificationHelper.show(ctx, alertTitles.get(0), alertBodies.get(0));
        } else if (seeded && alertTitles.size() > 1) {
            StringBuilder digest = new StringBuilder();
            int limit = Math.min(alertTitles.size(), 4);
            for (int i = 0; i < limit; i++) {
                if (i > 0) digest.append("\n");
                digest.append("• ").append(alertTitles.get(i)).append(" : ").append(alertBodies.get(i));
            }
            if (alertTitles.size() > limit) {
                digest.append("\n• +").append(alertTitles.size() - limit).append(" autre(s) alerte(s)");
            }
            NotificationHelper.show(
                ctx,
                "🔔 Copilote H24 • " + alertTitles.size() + " nouveautés",
                digest.toString()
            );
        }

        if (idList.size() > 180) {
            idList = idList.subList(idList.size() - 180, idList.size());
        }
        StringBuilder joined = new StringBuilder();
        for (int i = 0; i < idList.size(); i++) {
            if (i > 0) joined.append(",");
            joined.append(idList.get(i));
        }
        sp.edit()
            .putBoolean(NotificationHelper.KEY_SEEDED, true)
            .putString(NotificationHelper.KEY_NOTIFIED_IDS, joined.toString())
            .apply();
    }
}
EOF

cat > "$WORK/src/fr/copilote/h24/MainActivity.java" << 'EOF'
package fr.copilote.h24;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.PowerManager;
import android.provider.Settings;
import android.view.Window;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {
    private WebView webView;
    private static final int REQ_NOTIF_PERM = 9001;
    private static final String LIVE_URL = "https://kira08200.github.io/Copilot-H24/";
    private static final String LOCAL_URL = "file:///android_asset/index.html";

    private void requestBatteryExemptionIfNeeded() {
        if (Build.VERSION.SDK_INT >= 23) {
            try {
                PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
                String pkg = getPackageName();
                if (pm != null && !pm.isIgnoringBatteryOptimizations(pkg)) {
                    Intent intent = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
                    intent.setData(Uri.parse("package:" + pkg));
                    startActivity(intent);
                }
            } catch (Exception ignored) {}
        }
    }

    private class AndroidBridge {
        @JavascriptInterface
        public boolean isAvailable() {
            return true;
        }

        @JavascriptInterface
        public boolean isGranted() {
            return NotificationHelper.isPermissionGranted(MainActivity.this);
        }

        @JavascriptInterface
        public boolean isBgEnabled() {
            return NotificationHelper.isBgEnabled(MainActivity.this);
        }

        @JavascriptInterface
        public void requestPermission() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if (Build.VERSION.SDK_INT >= 33 && !NotificationHelper.isPermissionGranted(MainActivity.this)) {
                        requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"}, REQ_NOTIF_PERM);
                    } else {
                        NotificationHelper.setBgEnabled(MainActivity.this, true);
                        requestBatteryExemptionIfNeeded();
                        notifyJsPerm(true);
                    }
                }
            });
        }

        @JavascriptInterface
        public void setBgEnabled(final boolean enabled) {
            NotificationHelper.setBgEnabled(MainActivity.this, enabled);
        }

        @JavascriptInterface
        public void notify(final String title, final String body) {
            NotificationHelper.show(MainActivity.this, title, body);
        }
    }

    private void notifyJsPerm(final boolean granted) {
        if (webView == null) return;
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                webView.evaluateJavascript(
                    "if(window.__onAndroidNotifPerm){window.__onAndroidNotifPerm(" + (granted ? "true" : "false") + ");}",
                    null
                );
            }
        });
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQ_NOTIF_PERM) {
            boolean granted = grantResults != null && grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED;
            NotificationHelper.setBgEnabled(this, granted);
            if (granted) {
                requestBatteryExemptionIfNeeded();
            }
            notifyJsPerm(granted);
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        NotificationHelper.ensureChannel(this);
        if (NotificationHelper.isBgEnabled(this) && NotificationHelper.isPermissionGranted(this)) {
            NotificationHelper.scheduleBackgroundJob(this, true);
        }

        Window window = getWindow();
        if (window != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            int darkBg = Color.parseColor("#0b0f17");
            window.setStatusBarColor(darkBg);
            window.setNavigationBarColor(darkBg);
        }

        webView = new WebView(this);
        webView.setBackgroundColor(Color.parseColor("#0b0f17"));

        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setAllowFileAccessFromFileURLs(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setUserAgentString(s.getUserAgentString() + " CopiloteH24APK/1.2");

        webView.addJavascriptInterface(new AndroidBridge(), "CopiloteAndroid");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String url = uri.toString();
                if (url.startsWith("https://kira08200.github.io") || url.startsWith("file:///android_asset")) {
                    return false;
                }
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, uri);
                    startActivity(intent);
                } catch (Exception ignored) {}
                return true;
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    String failing = request.getUrl().toString();
                    if (!failing.startsWith("file:///android_asset")) {
                        view.loadUrl(LOCAL_URL);
                    }
                }
            }
        });

        setContentView(webView);
        webView.loadUrl(LIVE_URL);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
EOF

"$BUILD_TOOLS/aapt2" compile --dir "$WORK/res" -o "$WORK/compiled_res.zip"

"$BUILD_TOOLS/aapt2" link \
  -o "$WORK/unsigned.apk" \
  -I "$PLATFORM/android.jar" \
  --manifest "$WORK/AndroidManifest.xml" \
  -A "$WORK/assets" \
  --java "$WORK/gen" \
  "$WORK/compiled_res.zip" \
  --auto-add-overlay

javac --release 8 \
  -cp "$PLATFORM/android.jar" \
  -d "$WORK/classes" \
  "$WORK/gen/fr/copilote/h24/R.java" \
  "$WORK/src/fr/copilote/h24/NotificationHelper.java" \
  "$WORK/src/fr/copilote/h24/BootAndAlarmReceiver.java" \
  "$WORK/src/fr/copilote/h24/AlertJobService.java" \
  "$WORK/src/fr/copilote/h24/MainActivity.java"

"$BUILD_TOOLS/d8" \
  --lib "$PLATFORM/android.jar" \
  --output "$WORK/dex" \
  $(find "$WORK/classes" -name "*.class")

(
  cd "$WORK/dex"
  zip -uj "$WORK/unsigned.apk" classes.dex
)

"$BUILD_TOOLS/zipalign" -f -p 4 "$WORK/unsigned.apk" "$WORK/aligned.apk"

keytool -genkeypair -v \
  -keystore "$WORK/release.keystore" \
  -alias copilote \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass copilote123 -keypass copilote123 \
  -dname "CN=Copilote H24, OU=Mobile, O=Copilote, L=Paris, S=IDF, C=FR"

"$BUILD_TOOLS/apksigner" sign \
  --ks "$WORK/release.keystore" \
  --ks-key-alias copilote \
  --ks-pass pass:copilote123 \
  --key-pass pass:copilote123 \
  --out "$REPO_ROOT/Copilote-H24.apk" \
  "$WORK/aligned.apk"

ls -lh "$REPO_ROOT/Copilote-H24.apk"
echo "APK successfully built at $REPO_ROOT/Copilote-H24.apk"
