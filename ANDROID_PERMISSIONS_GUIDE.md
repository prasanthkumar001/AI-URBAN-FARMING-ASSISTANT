# KrishiNova Android Studio & Permissions Guide

This guide explains how Capacitor bridges the KrishiNova Python/Flask web app into a native Android APK and how native hardware capabilities (Camera, Voice Microphone, and HTTP Network access) are configured.

---

## 1. Android Permissions in `android/app/src/main/AndroidManifest.xml`

When `npx cap add android` generates the `android/` project, ensure the following tags are placed in `AndroidManifest.xml`:

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <!-- 1. Internet & Network Access (For Flask server & Open-Meteo weather) -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

    <!-- 2. Camera & Photo Access (For AI Tomato Leaf Disease Diagnosis) -->
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
    <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />

    <!-- 3. Microphone & Audio Access (For KrishiNova Voice Assistant in Gujarati, Hindi, Telugu, English) -->
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    <uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/AppTheme"
        android:usesCleartextTraffic="true"> <!-- CRITICAL: Allows local HTTP development (10.0.2.2 or local Wi-Fi) -->

        <activity
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|locale|smallestScreenSize|screenLayout|uiMode"
            android:name=".MainActivity"
            android:label="@string/title_activity_main"
            android:theme="@style/AppTheme.NoActionBarLaunch"
            android:launchMode="singleTask"
            android:exported="true">

            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>

        </activity>
    </application>
</manifest>
```

---

## 2. Server Configuration: Connecting from Android Device or Emulator

Since the KrishiNova backend is powered by Python Flask with PyTorch and SQLite:

### Option A: Testing in Android Studio Emulator
- The Android Emulator routes the host machine's `localhost` to IP `10.0.2.2`.
- When Flask runs on `http://127.0.0.1:5000` or `0.0.0.0:5000`, the emulator connects directly to `http://10.0.2.2:5000`.
- In `capacitor.config.json`, you can either set:
  ```json
  "server": {
    "url": "http://10.0.2.2:5000",
    "cleartext": true
  }
  ```
  Or use the built-in launcher in `www/index.html` which connects with 1 click.

### Option B: Testing on a Physical Phone via Wi-Fi
1. Ensure your PC and Android phone are connected to the same Wi-Fi network.
2. Find your PC's local Wi-Fi IP address:
   ```powershell
   ipconfig
   ```
   (Look for `IPv4 Address`, e.g. `192.168.1.15`).
3. Flask now runs on `0.0.0.0:5000` by default.
4. On the phone, enter `http://192.168.1.15:5000` in the app launcher or set it in `capacitor.config.json`.

### Option C: Production Deployed Server (e.g. Render / AWS / PythonAnywhere)
- Set `"url": "https://your-domain.com"` in `capacitor.config.json`.
- The app will load securely via HTTPS from any mobile network globally.

---

## 3. How to Build Debug APK in Android Studio

1. Run:
   ```bash
   npx cap open android
   ```
   *(Or launch Android Studio, click **Open**, and navigate to `c:\Users\ASUS\OneDrive\Desktop\7\android`)*.
2. Wait for Android Studio to finish the **Gradle Sync** (bottom progress bar).
3. In the top menu bar, click:
   **Build** > **Build Bundle(s) / APK(s)** > **Build APK(s)**
4. Once built, click the **locate** popup link at the bottom-right notifications tray.
   The APK is located at:
   `android/app/build/outputs/apk/debug/app-debug.apk`
5. Transfer `app-debug.apk` to your Android device via USB cable, Google Drive, or WhatsApp, and tap **Install**!
