<div align="center">

# 🤖 AndroidStudio-For-Android

### The Official Google Android Studio IDE Running **100% Natively on Android Bionic ARM64**
*No PRoot. No Virtual Machines. Real Hardware Acceleration. Pure Android Native.*

[![Platform](https://img.shields.io/badge/Platform-Android%20%2F%20Termux-brightgreen.svg?style=for-the-badge&logo=android)](https://termux.dev)
[![Architecture](https://img.shields.io/badge/Arch-ARM64%20%2F%20aarch64-blue.svg?style=for-the-badge&logo=arm)](https://github.com/sirvkrm/AndroidStudio-For-Android)
[![Bionic Native](https://img.shields.io/badge/Runtime-Bionic%20Libc-orange.svg?style=for-the-badge)](https://github.com/sirvkrm/AndroidStudio-Bionic-Libs)
[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg?style=for-the-badge)](LICENSE)

---

[🚀 Quick Start](#-quick-start-1-line-installer) • [📖 The Story](#-the-story-from-the-november-grind-to-bionic-triumph) • [⚡ PRoot vs Bionic](#-why-native-bionic-over-proot) • [🧬 The 5 Pillars](#-the-5-pillars-of-bionic-android-studio) • [🔗 Ecosystem Repos](#-linked-ecosystem-repositories)

---

</div>

## 📖 The Story: From the November Grind to Bionic Triumph

> *"Everyone told me Android Studio on Android was impossible without PRoot or heavy emulation. They said Android's Bionic libc was too alien for JetBrains and Google's desktop toolchain. This project is the answer to that."* — **sirvkrm**

### Chapter 1: The November Spark 💡
The vision began in **November**: Why should developers carry heavy laptops just to build Android apps when the smartphone or tablet in their pocket already has 8, 12, or 16 GB of RAM and 8 fast ARM64 cores? 

Running Android Studio in PRoot Linux had always been a frustrating compromise: lagging redraws, broken inotify file watchers that froze the IDE every 5 minutes, non-functional terminals with `LD_PRELOAD` crashes, and agonizingly slow disk I/O. The only true solution was to run **Android Studio directly on Android's native Bionic libc**.

### Chapter 2: The Two-Month Marathon (Nov – Dec 26) 🏃‍♂️💨
From November all the way through **December 26**, the hustle was relentless:
* Tracing every single `.so` shared library the IntelliJ platform demands on startup.
* Decompiling Java bytecode to see why `jna` and `pty4j` choked on Bionic.
* Discovering that `pty4j` broke because Android Bionic doesn't ship `libutil.so` (`login_tty`), and Termux's `LD_PRELOAD` was poisoning spawned processes.
* Fighting missing SONAME tags, resolving `$ORIGIN` vs `/system/lib64` search paths, and patching `product-info.json`.

### Chapter 3: The `layoutlib` Wall & The Pause 🧱
By late December, ambitious efforts turned towards compiling **`layoutlib`** (`layoutlib_jni.so` and `libandroid_runtime.so`) from raw AOSP source trees to enable native XML design preview. 

Then reality hit hard: **low hardware resources**. Compiling gigabytes of AOSP code triggered rampant out-of-memory (OOM) killer terminations, extreme thermal throttling, and multi-day compile timeouts. On **December 26**, with burnt-out hardware and exhaustion, the active work paused.

### Chapter 4: The Resurgence & Victory 🏆
In 2026, the project was resurrected with a smarter, cleaner strategy:
1. **Forget the bloated 80 GB AOSP monorepo.** Focus strictly on what makes Android Studio's core runtime stable, snappy, and responsive.
2. **Build standalone modular Bionic libraries**: compile `fsnotifier`, `pty4j` (with custom Bionic `libutil`), `jna`, `sqlite-jdbc`, and compile **`skiko`** (Compose Desktop Skia engine) with native X11/AWT windowing.
3. Build an automated, interactive Python & Bash installer that turns a 30-day manual nightmare into a **single 2-minute command**.

Android Studio finally bowed to Bionic!

---

## ⚡ Why Native Bionic Over PRoot?

| Feature | PRoot / Linux Container | **Native Bionic (This Project)** |
| :--- | :--- | :--- |
| **I/O & Disk Performance** | Emulated `proot` syscall overhead (slow) | **Direct native filesystem access (Fast)** |
| **File Watching (`fsnotifier`)** | Desyncs / Freezes IDE constantly | **Native Bionic inotify watcher** |
| **Graphics Engine (`Skiko`/Skia)** | Software rasterization / CPU lag | **Ganesh & Vulkan hardware rendering** |
| **RAM Consumption** | High (PRoot + guest OS + IDE) | **Minimal (Only JVM + IDE processes)** |
| **Embedded Terminal (`pty4j`)** | Crashes on child process exec | **Patched `login_tty` + `unset LD_PRELOAD`** |
| **SDK & NDK Integration** | Requires glibc toolchains | **HomuHomu ARM64 native binaries** |

---

## 🧬 The 5 Pillars of Bionic Android Studio

Running a desktop IDE on Android requires replacing every glibc-linked native library with an Android Bionic ARM64 binary:

```
Android Studio (JVM Platform)
  ├── fsnotifier                 -> Native inotify file tree watcher (avoids IDE freezes)
  ├── libpty.so + libutil.so      -> Pty4j terminal emulator + POSIX login_tty
  ├── libjnidispatch.so           -> Java Native Access C bridge
  ├── libsqlitejdbc.so            -> High-performance SQLite database engine
  └── libskiko-linux-arm64.so     -> Skiko / Skia Jetpack Compose hardware rendering
```

All 5 pillars are pre-compiled, tested, and automatically downloaded from [sirvkrm/AndroidStudio-Bionic-Libs](https://github.com/sirvkrm/AndroidStudio-Bionic-Libs).

---

## 🚀 Quick Start (1-Line Installer)

Open **Termux** on your Android device and run:

```bash
curl -sSL https://raw.githubusercontent.com/sirvkrm/AndroidStudio-For-Android/main/install.sh | bash
```

### Or Clone & Run:
```bash
git clone https://github.com/sirvkrm/AndroidStudio-For-Android.git
cd AndroidStudio-For-Android
python3 setup.py
```

---

## 🎛 What the Interactive Setup Wizard Does

When you launch `setup.py` (or `install.sh`), it interactively guides you through the full setup:

```
=================================================================
 AndroidStudio-For-Android: Native Bionic ARM64 Installer
=================================================================
Platform: Termux / Android Bionic
Home Dir: /data/data/com.termux/files/home

▶ Step 1: Android Studio Acquisition
  Choose how you would like to setup Android Studio:
  1) Android Studio Ladybug (2024.2.1.12 - Recommended Stable) (default)
  2) Android Studio Meerkat (2024.3.1.13 Canary)
  3) Android Studio Koala Feature Drop (2024.1.2.12)
  4) Custom URL
  5) Skip Download (Browse Local / Existing Directory)

▶ Step 2: Native OpenJDK Setup (No PRoot needed!)
  ✔ Auto-detects OpenJDK 17 or 21 in Termux
  ✔ Symlinks Android Studio JBR -> $PREFIX/lib/jvm/openjdk-17

▶ Step 3: Inject Native Bionic ARM64 Libraries
  ✔ Downloads verified Bionic libraries bundle from GitHub Releases
  ✔ Injects fsnotifier, libpty.so, libutil.so, libjnidispatch.so, libsqlitejdbc.so, libskiko.so
  ✔ Updates internal JNA jar files (app.jar, util.jar, jna.jar)

▶ Step 4: Patch Launcher Scripts & VM Options
  ✔ Patches product-info.json (amd64 -> aarch64)
  ✔ Patches bin/studio.sh with unset LD_PRELOAD, DISPLAY, and system RUNPATH
  ✔ Appends native runtime overrides to studio64.vmoptions

▶ Step 5: Android SDK & NDK Setup
  ✔ Installs HomuHomu Build-Tools (35.0.0 & 36.0.0)
  ✔ Installs HomuHomu ARM64 NDK r29

▶ Step 6: 1-Click Launch Script
  ✔ Generates ~/start-studio.sh executable
```

---

## 🖥 How to Launch & Use with Termux:X11

1. Install the **[Termux:X11](https://github.com/termux/termux-x11/releases)** companion APK on your Android device.
2. Open Termux and start the X11 server:
   ```bash
   termux-x11 :0 &
   ```
3. Open the **Termux:X11 app** from your home screen / launcher.
4. Switch back to Termux and launch Android Studio:
   ```bash
   ~/start-studio.sh
   ```
5. Android Studio will open in Termux:X11 in full desktop UI with hardware acceleration!

---

## 💡 Pro-Tips for Android Development

### 1. Fix Gradle AAPT2 on Android
Standard Google AAPT2 distributed via Maven is compiled for x86_64 glibc. To make Gradle build your Android projects using our native ARM64 AAPT2, add this line to your project's `gradle.properties`:

```properties
android.aapt2FromMavenOverride=/data/data/com.termux/files/home/Android/Sdk/build-tools/36.0.0/aapt2
```

### 2. Termux:X11 Performance Settings
Inside the Termux:X11 app preferences:
* Set **Display resolution mode** to `Exact` or `Scaled (e.g. 1920x1080)`.
* Enable **Fullscreen on display**.
* Set **Force GPU rendering** to `ON`.

---

## 🔗 Linked Ecosystem Repositories

This project stands on the shoulders of these key repositories:

* 📦 [**sirvkrm/AndroidStudio-Bionic-Libs**](https://github.com/sirvkrm/AndroidStudio-Bionic-Libs) — Master repository building all native Bionic startup libraries (`fsnotifier`, `pty4j`, `jna`, `sqlite-jdbc`, `libutil`).
* 🎨 [**sirvkrm/skiko-android**](https://github.com/sirvkrm/skiko-android) — JetBrains Skiko fork with Bionic JNI OpenJDK compatibility and desktop AWT/X11 rendering.
* 🛠 [**HomuHomu833/android-sdk-custom**](https://github.com/HomuHomu833/android-sdk-custom) — ARM64 Linux/Musl native prebuilts for Android SDK build tools (`aapt2`, `zipalign`, `d8`).
* ⚙️ [**HomuHomu833/android-ndk-custom**](https://github.com/HomuHomu833/android-ndk-custom) — ARM64 native Android NDK (r29).

---

## 🤝 Contributing & License

Contributions, bug reports, and optimizations are welcome!
Licensed under the [Apache License 2.0](LICENSE).
