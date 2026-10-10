# ==============================================================================
# KrishiNova - Capacitor Android APK Automated Setup Script
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  KrishiNova - Capacitor Android Environment Setup" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green

# 1. Check Node.js and npm
$nodeInstalled = Get-Command node -ErrorAction SilentlyContinue
$npmInstalled  = Get-Command npm -ErrorAction SilentlyContinue

if (-not $nodeInstalled -or -not $npmInstalled) {
    Write-Host "`n[!] Node.js and npm were not detected in your PATH." -ForegroundColor Yellow
    Write-Host "Please install Node.js (v18 or v20 LTS recommended):" -ForegroundColor Cyan
    Write-Host "  Option A (Recommended): Download installer from https://nodejs.org/" -ForegroundColor White
    Write-Host "  Option B (PowerShell):   winget install OpenJS.NodeJS.LTS" -ForegroundColor White
    Write-Host "`nAfter installing Node.js, restart your terminal and re-run this script." -ForegroundColor Yellow
    exit 1
}

Write-Host "[✓] Node.js version: $(node -v)" -ForegroundColor Green
Write-Host "[✓] npm version:     $(npm -v)" -ForegroundColor Green

# 2. Install Capacitor packages
Write-Host "`n[+] Installing Capacitor 6 dependencies..." -ForegroundColor Cyan
npm install

if ($LASTEXITCODE -ne 0) {
    Write-Host "[✗] npm install encountered an error." -ForegroundColor Red
    exit 1
}

# 3. Add Android platform if not present
if (-not (Test-Path "android")) {
    Write-Host "`n[+] Initializing native Android project with Capacitor..." -ForegroundColor Cyan
    npx cap add android
} else {
    Write-Host "`n[✓] Android platform directory already exists." -ForegroundColor Green
}

# 4. Patch AndroidManifest.xml for Camera, Microphone, and Cleartext Traffic
$manifestPath = "android\app\src\main\AndroidManifest.xml"
if (Test-Path $manifestPath) {
    Write-Host "`n[+] Configuring Android permissions (Camera, Microphone, Cleartext)..." -ForegroundColor Cyan
    $manifest = Get-Content $manifestPath -Raw

    # Permissions to add
    $permissionsToAdd = @"
    <!-- KrishiNova Permissions -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    <uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
    <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
"@

    if ($manifest -notmatch "android.permission.CAMERA") {
        $manifest = $manifest -replace "<application", ($permissionsToAdd + "`n    <application")
    }

    if ($manifest -notmatch "android:usesCleartextTraffic") {
        $manifest = $manifest -replace "<application", '<application android:usesCleartextTraffic="true"'
    }

    Set-Content -Path $manifestPath -Value $manifest -Encoding UTF8
    Write-Host "[✓] AndroidManifest.xml configured with Camera, Mic, and Cleartext permissions." -ForegroundColor Green
}

# 5. Sync web assets and plugins to Android
Write-Host "`n[+] Synchronizing web assets (www/) to native Android..." -ForegroundColor Cyan
npx cap sync android

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  KrishiNova Android Project Ready!" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "`nNext Steps to Generate Debug APK:" -ForegroundColor Cyan
Write-Host "1. Ensure Flask is running:  python app.py" -ForegroundColor White
Write-Host "2. Open in Android Studio:   npx cap open android" -ForegroundColor White
Write-Host "3. In Android Studio: Select Build > Build Bundle(s) / APK(s) > Build APK(s)" -ForegroundColor White
Write-Host "4. Generated APK location:   android/app/build/outputs/apk/debug/app-debug.apk`n" -ForegroundColor White
