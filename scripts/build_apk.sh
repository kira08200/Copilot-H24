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
    android:versionCode="1"
    android:versionName="1.0">

    <uses-sdk android:minSdkVersion="24" android:targetSdkVersion="34" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

    <application
        android:label="Copilote H24"
        android:icon="@drawable/ic_launcher"
        android:usesCleartextTraffic="true"
        android:allowBackup="true"
        android:theme="@android:style/Theme.DeviceDefault.NoActionBar">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
EOF

cat > "$WORK/src/fr/copilote/h24/MainActivity.java" << 'EOF'
package fr.copilote.h24;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.Window;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {
    private WebView webView;
    private static final String LIVE_URL = "https://kira08200.github.io/Copilot-H24/";
    private static final String LOCAL_URL = "file:///android_asset/index.html";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

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
        s.setUserAgentString(s.getUserAgentString() + " CopiloteH24APK/1.0");

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
