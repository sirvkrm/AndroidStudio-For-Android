#!/usr/bin/env bash
# ==============================================================================
# Android Studio Native Bionic ARM64 Setup & Patcher for Termux / Android
# Author: sirvkrm & Antigravity
# Repository: https://github.com/sirvkrm/AndroidStudio-Bionic-Libs
# ==============================================================================
set -euo pipefail

### ================================
###  CONFIG – EDIT IF NEEDED
### ================================
ANDROID_STUDIO_DEFAULT="$HOME/android-studio"
SDK_DEFAULT="$HOME/Android/Sdk"
TERMUX_PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"

# Prebuilt Bionic Native Libs Release
LIBS_TAG="v1.0.0"
LIBS_BASE_URL="https://github.com/sirvkrm/AndroidStudio-Bionic-Libs/releases/download/${LIBS_TAG}"
LIBS_BUNDLE_URL="${LIBS_BASE_URL}/android-studio-bionic-libs-aarch64.tar.gz"

# HomuHomu SDK / NDK URLs
SDK_35_URL="https://github.com/HomuHomu833/android-sdk-custom/releases/download/35.0.2/android-sdk-aarch64-linux-musl.tar.xz"
SDK_36_URL="https://github.com/HomuHomu833/android-sdk-custom/releases/download/36.0.0/android-sdk-aarch64-linux-musl.tar.xz"
NDK_R29_URL="https://github.com/HomuHomu833/android-ndk-custom/releases/download/r29/android-ndk-r29-beta4-aarch64-linux-android.tar.xz"
NDK_VERSION_DIR="29.0.14033849"

# Official Android Studio Linux ARM64 (Fallback download)
STUDIO_DOWNLOAD_URL="https://redirector.gvt1.com/edgedl/android/studio/ide-zips/2024.3.1.13/android-studio-2024.3.1.13-linux.tar.gz"

# Dry run flag
DRY_RUN="no"

### ================================
###  COLOR & SMALL HELPERS
### ================================
cecho() {
  local color="$1"; shift
  case "$color" in
    red)    printf '\033[0;31m%s\033[0m\n' "$*";;
    green)  printf '\033[0;32m%s\033[0m\n' "$*";;
    yellow) printf '\033[0;33m%s\033[0m\n' "$*";;
    cyan)   printf '\033[0;36m%s\033[0m\n' "$*";;
    magenta)printf '\033[0;35m%s\033[0m\n' "$*";;
    bold)   printf '\033[1m%s\033[0m\n' "$*";;
    *)      printf '%s\n' "$*";;
  esac
}

do_cmd() {
  if [[ "$DRY_RUN" == "yes" ]]; then
    cecho cyan "[dry-run] $*"
  else
    "$@"
  fi
}

ask_yes_no() {
  local prompt="$1"
  local default="${2:-n}"
  local ans def_disp

  if [[ "$default" == "y" ]]; then
    def_disp="Y/n"
  else
    def_disp="y/N"
  fi

  while true; do
    read -r -p "$prompt [$def_disp] " ans || ans=""
    ans="${ans:-$default}"
    case "$ans" in
      y|Y) return 0;;
      n|N) return 1;;
      *) cecho yellow "⚠ Please answer y or n.";;
    esac
  done
}

hr() {
  printf '\n\033[0;35m%s\033[0m\n' "============================================================"
}

### ================================
###  PATH DETECTION & VALIDATION
### ================================
detect_paths() {
  hr
  cecho magenta "🚀 Detecting paths..."

  ANDROID_STUDIO="${ANDROID_STUDIO:-$ANDROID_STUDIO_DEFAULT}"
  SDK_ROOT="${SDK_ROOT:-$SDK_DEFAULT}"

  cecho cyan "Configured paths:"
  echo "  📦 ANDROID_STUDIO = $ANDROID_STUDIO"
  echo "  📁 SDK_ROOT       = $SDK_ROOT"
  echo "  📱 TERMUX_PREFIX  = $TERMUX_PREFIX"

  if ask_yes_no "Do you want to edit any of these paths?" n; then
    local tmp
    read -r -p "ANDROID_STUDIO path [$ANDROID_STUDIO]: " tmp || true
    [[ -n "$tmp" ]] && ANDROID_STUDIO="$tmp"

    read -r -p "SDK_ROOT path [$SDK_ROOT]: " tmp || true
    [[ -n "$tmp" ]] && SDK_ROOT="$tmp"
  fi

  cecho cyan "✅ Selected paths:"
  echo "  📦 ANDROID_STUDIO = $ANDROID_STUDIO"
  echo "  📁 SDK_ROOT       = $SDK_ROOT"

  if [[ ! -d "$ANDROID_STUDIO" ]]; then
    cecho yellow "⚠ Android Studio directory not found at $ANDROID_STUDIO."
    if ask_yes_no "Download and extract official Android Studio Linux ARM64 archive now?" y; then
      download_android_studio
    else
      cecho red "❌ Android Studio directory required to proceed. Exiting."
      exit 1
    fi
  fi

  do_cmd mkdir -p "$SDK_ROOT"
}

### ================================
###  DOWNLOAD ANDROID STUDIO
### ================================
download_android_studio() {
  hr
  cecho magenta "🌐 Downloading official Android Studio Linux release..."
  local parent_dir
  parent_dir="$(dirname "$ANDROID_STUDIO")"
  do_cmd mkdir -p "$parent_dir"

  local tmp_tar
  tmp_tar="$(mktemp --suffix=.tar.gz)"
  cecho cyan "Downloading from: $STUDIO_DOWNLOAD_URL"
  if [[ "$DRY_RUN" == "yes" ]]; then
    cecho cyan "[dry-run] Would download and extract to $parent_dir"
    return 0
  fi

  curl -fLC - --progress-bar "$STUDIO_DOWNLOAD_URL" -o "$tmp_tar"
  cecho cyan "📦 Extracting Android Studio into $parent_dir..."
  tar -xzf "$tmp_tar" -C "$parent_dir"
  rm -f "$tmp_tar"
  cecho green "✅ Android Studio extracted to $ANDROID_STUDIO."
}

### ================================
###  BACKUP ANDROID STUDIO
### ================================
backup_android_studio() {
  hr
  cecho magenta "🛟 Creating backup of Android Studio key components..."
  local ts backup_dir
  ts="$(date +%Y%m%d-%H%M%S)"
  backup_dir="${ANDROID_STUDIO}.bak-${ts}"

  do_cmd mkdir -p "$backup_dir"

  for item in bin lib jbr product-info.json; do
    if [[ -e "$ANDROID_STUDIO/$item" ]]; then
      cecho yellow "  ↪ Backing up $item -> $backup_dir/$item"
      do_cmd cp -a "$ANDROID_STUDIO/$item" "$backup_dir/" 2>/dev/null || true
    fi
  done

  cecho green "✅ Backup created at: $backup_dir"
}

### ================================
###  TERMUX OPENJDK DETECTION / SETUP
### ================================
SELECTED_JDK=""

setup_termux_jdk() {
  hr
  cecho magenta "☕ Native Termux OpenJDK Setup..."

  local jdk_candidates=()
  local search_roots=(
    "$TERMUX_PREFIX/lib/jvm"
    "/usr/lib/jvm"
  )

  for root in "${search_roots[@]}"; do
    if [[ -d "$root" ]]; then
      while IFS= read -r -d '' d; do
        if [[ -x "$d/bin/java" ]]; then
          jdk_candidates+=("$d")
        fi
      done < <(find "$root" -maxdepth 2 -type d -print0 2>/dev/null)
    fi
  done

  if [[ ${#jdk_candidates[@]} -eq 0 ]]; then
    cecho yellow "⚠ No OpenJDK detected in $TERMUX_PREFIX/lib/jvm."
    if command -v pkg >/dev/null 2>&1; then
      if ask_yes_no "Install native OpenJDK 17 now via 'pkg install openjdk-17'?" y; then
        do_cmd pkg install -y openjdk-17
        setup_termux_jdk
        return
      fi
    fi
  fi

  if [[ ${#jdk_candidates[@]} -gt 0 ]]; then
    cecho cyan "Available native JDKs:"
    local i=1
    for jdk in "${jdk_candidates[@]}"; do
      printf "  %d) %s\n" "$i" "$jdk"
      ((i++))
    done

    echo "  0) Auto-select first matching JDK (default)"
    local choice
    read -r -p "Select JDK [0-${#jdk_candidates[@]}] (Enter = auto): " choice || choice=""
    choice="${choice:-0}"

    if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#jdk_candidates[@]} )); then
      SELECTED_JDK="${jdk_candidates[$((choice-1))]}"
    else
      SELECTED_JDK="${jdk_candidates[0]}"
    fi
    cecho green "✅ Selected JDK: $SELECTED_JDK"
  else
    cecho red "❌ No native OpenJDK available. Please install one via 'pkg install openjdk-17'."
    return 1
  fi

  # Symlink or replace Studio's bundled glibc JBR
  local studio_jbr="$ANDROID_STUDIO/jbr"
  if ask_yes_no "Point Android Studio JBR ($studio_jbr) -> $SELECTED_JDK ?" y; then
    if [[ -e "$studio_jbr" ]]; then
      cecho yellow "  🧹 Removing old bundled glibc JBR: $studio_jbr"
      do_cmd rm -rf "$studio_jbr"
    fi
    do_cmd ln -s "$SELECTED_JDK" "$studio_jbr"
    cecho green "✅ Android Studio JBR symlinked to native JDK."
  fi
}

### ================================
###  DOWNLOAD & INJECT BIONIC LIBS
### ================================
patch_bionic_libs() {
  hr
  cecho magenta "🧬 Downloading & Injecting Bionic Native ARM64 Libraries..."
  cecho cyan "Source: $LIBS_BUNDLE_URL"

  local tmp_bundle
  tmp_bundle="$(mktemp --suffix=.tar.gz)"

  if [[ "$DRY_RUN" == "yes" ]]; then
    cecho cyan "[dry-run] Would download Bionic libs bundle and extract into $ANDROID_STUDIO"
  else
    cecho cyan "🌐 Downloading prebuilt Bionic libraries bundle..."
    curl -fLC - --progress-bar "$LIBS_BUNDLE_URL" -o "$tmp_bundle"

    cecho cyan "📦 Extracting into Android Studio root ($ANDROID_STUDIO)..."
    tar -xzf "$tmp_bundle" -C "$ANDROID_STUDIO"
    rm -f "$tmp_bundle"

    # Make binaries executable
    chmod +x "$ANDROID_STUDIO/bin/fsnotifier"* 2>/dev/null || true
    chmod +x "$ANDROID_STUDIO/lib/"*/*.so 2>/dev/null || true
    chmod +x "$ANDROID_STUDIO/lib/"*/*/*.so 2>/dev/null || true
    chmod +x "$ANDROID_STUDIO/lib/"*/*/*/*.so 2>/dev/null || true

    # Install libutil.so into Termux userland if accessible so JNA finds it globally
    if [[ -w "$TERMUX_PREFIX/lib" && -f "$ANDROID_STUDIO/lib/pty4j/linux/aarch64/libutil.so" ]]; then
      cecho yellow "  📌 Installing libutil.so to $TERMUX_PREFIX/lib/libutil.so"
      cp -f "$ANDROID_STUDIO/lib/pty4j/linux/aarch64/libutil.so" "$TERMUX_PREFIX/lib/libutil.so"
    fi

    # Inject libjnidispatch.so into jar files if zip/unzip or jar is available
    local jna_so="$ANDROID_STUDIO/lib/jna/linux-aarch64/libjnidispatch.so"
    if [[ -f "$jna_so" ]]; then
      cecho yellow "  📌 Updating internal JNA jars with Bionic libjnidispatch.so..."
      for jar_candidate in "$ANDROID_STUDIO/lib/util.jar" "$ANDROID_STUDIO/lib/app.jar" "$ANDROID_STUDIO/lib/jna.jar"; do
        if [[ -f "$jar_candidate" ]] && command -v zip >/dev/null 2>&1; then
          local tmp_jna_dir
          tmp_jna_dir="$(mktemp -d)"
          mkdir -p "$tmp_jna_dir/com/sun/jna/linux-aarch64"
          cp "$jna_so" "$tmp_jna_dir/com/sun/jna/linux-aarch64/libjnidispatch.so"
          (cd "$tmp_jna_dir" && zip -u "$jar_candidate" com/sun/jna/linux-aarch64/libjnidispatch.so >/dev/null 2>&1 || true)
          rm -rf "$tmp_jna_dir"
          cecho green "    ↪ Injected into $(basename "$jar_candidate")"
        fi
      done
    fi
  fi

  cecho green "✅ Bionic libraries successfully injected:"
  echo "  • fsnotifier (dynamic Bionic & static fallback)"
  echo "  • pty4j (libpty.so & libutil.so for login_tty)"
  echo "  • jna (libjnidispatch.so)"
  echo "  • sqlite-jdbc (libsqlitejdbc.so)"
  echo "  • skiko (libskiko-linux-arm64.so with Ganesh + Vulkan + X11)"
}

### ================================
###  PATCH STUDIO SCRIPTS & VMOPTIONS
### ================================
patch_scripts_and_vmoptions() {
  hr
  cecho magenta "🛠 Patching Android Studio launcher scripts and VM options..."

  local studio_sh="$ANDROID_STUDIO/bin/studio.sh"
  local vmoptions="$ANDROID_STUDIO/bin/studio64.vmoptions"
  local product_json="$ANDROID_STUDIO/product-info.json"

  # 1. Patch product-info.json
  if [[ -f "$product_json" ]]; then
    cecho yellow "  ✏ Patching product-info.json: \"amd64\" -> \"aarch64\""
    if [[ "$DRY_RUN" != "yes" ]]; then
      sed -i 's/"amd64"/"aarch64"/g' "$product_json" || true
    fi
  fi

  # 2. Patch studio.sh
  if [[ -f "$studio_sh" ]]; then
    cecho yellow "  ✏ Injecting Termux / Bionic environment headers into studio.sh..."
    if [[ "$DRY_RUN" != "yes" ]]; then
      # Make sure amd64 references are replaced
      sed -i 's/amd64/\$OS_ARCH/g' "$ANDROID_STUDIO"/bin/*.sh 2>/dev/null || true

      # Inject environment setup at line 2 if not already injected
      if ! grep -q "STUDIO_BIONIC_PATCHED" "$studio_sh"; then
        local env_header
        env_header=$(cat << 'EOF'
# >>> STUDIO_BIONIC_PATCHED >>>
export DISPLAY="${DISPLAY:-:0}"
export GDK_BACKEND=x11
unset LD_PRELOAD
if [ -z "${STUDIO_JDK:-}" ] && [ -d "/data/data/com.termux/files/usr/lib/jvm/openjdk-17" ]; then
    export STUDIO_JDK="/data/data/com.termux/files/usr/lib/jvm/openjdk-17"
elif [ -z "${STUDIO_JDK:-}" ] && [ -d "/data/data/com.termux/files/usr/lib/jvm/openjdk-21" ]; then
    export STUDIO_JDK="/data/data/com.termux/files/usr/lib/jvm/openjdk-21"
fi
export LD_LIBRARY_PATH="/system/lib64:/data/data/com.termux/files/usr/lib:$IDE_HOME/lib/skiko:$IDE_HOME/lib/sqlite/linux-aarch64:${LD_LIBRARY_PATH:-}"
# <<< STUDIO_BIONIC_PATCHED <<<
EOF
)
        sed -i "2i \\$env_header" "$studio_sh"
      fi
      chmod +x "$studio_sh"
    fi
    cecho green "  ✅ studio.sh patched."
  fi

  # 3. Patch studio64.vmoptions
  if [[ -f "$vmoptions" ]]; then
    cecho yellow "  ✏ Appending Bionic runtime JVM options to studio64.vmoptions..."
    if [[ "$DRY_RUN" != "yes" ]]; then
      if ! grep -q "jna.boot.library.path" "$vmoptions"; then
        cat << EOF >> "$vmoptions"

# Bionic & Termux Native Library Paths
-Djna.boot.library.path=$ANDROID_STUDIO/lib/jna/linux-aarch64
-Dpty4j.preferred.native.folder=$ANDROID_STUDIO/lib/pty4j
-Dorg.sqlite.lib.path=$ANDROID_STUDIO/lib/sqlite/linux-aarch64
-Dorg.sqlite.lib.name=libsqlitejdbc.so
-Dskiko.library.path=$ANDROID_STUDIO/lib/skiko
-Djava.awt.headless=false
-Dsun.awt.noerasebackground=true
EOF
      fi
    fi
    cecho green "  ✅ studio64.vmoptions patched."
  fi
}

### ================================
###  INSTALL HOMUHOMU SDK & NDK
### ================================
install_sdk_ndk() {
  hr
  cecho magenta "📦 Checking Android SDK & NDK in $SDK_ROOT..."
  do_cmd mkdir -p "$SDK_ROOT"

  # 1. Build Tools 35.0.0 (from 35.0.2 package)
  if [[ -d "$SDK_ROOT/build-tools/35.0.0" ]]; then
    cecho green "  ✅ build-tools/35.0.0 already installed."
  else
    cecho yellow "  ⚠ build-tools/35.0.0 NOT found."
    if ask_yes_no "Download and install ARM64 SDK 35.0.2 package (HomuHomu)?" y; then
      if [[ "$DRY_RUN" != "yes" ]]; then
        local tmp_sdk
        tmp_sdk="$(mktemp --suffix=.tar.xz)"
        cecho cyan "  🌐 Downloading SDK 35.0.2..."
        curl -fLC - --progress-bar "$SDK_35_URL" -o "$tmp_sdk"
        cecho cyan "  📦 Extracting SDK 35.0.2..."
        tar -xJf "$tmp_sdk" -C "$SDK_ROOT" --strip-components=1
        rm -f "$tmp_sdk"
      fi
      cecho green "  ✅ SDK 35 installed."
    fi
  fi

  # 2. Build Tools 36.0.0
  if [[ -d "$SDK_ROOT/build-tools/36.0.0" ]]; then
    cecho green "  ✅ build-tools/36.0.0 already installed."
  else
    cecho yellow "  ⚠ build-tools/36.0.0 NOT found."
    if ask_yes_no "Download and install ARM64 SDK 36.0.0 package (HomuHomu)?" y; then
      if [[ "$DRY_RUN" != "yes" ]]; then
        local tmp_sdk
        tmp_sdk="$(mktemp --suffix=.tar.xz)"
        cecho cyan "  🌐 Downloading SDK 36.0.0..."
        curl -fLC - --progress-bar "$SDK_36_URL" -o "$tmp_sdk"
        cecho cyan "  📦 Extracting SDK 36.0.0..."
        tar -xJf "$tmp_sdk" -C "$SDK_ROOT" --strip-components=1
        rm -f "$tmp_sdk"
      fi
      cecho green "  ✅ SDK 36 installed."
    fi
  fi

  # 3. NDK r29
  if [[ -d "$SDK_ROOT/ndk/$NDK_VERSION_DIR" ]]; then
    cecho green "  ✅ NDK $NDK_VERSION_DIR already installed."
  else
    cecho yellow "  ⚠ NDK $NDK_VERSION_DIR NOT found."
    if ask_yes_no "Download and install ARM64 NDK r29 (HomuHomu)?" y; then
      if [[ "$DRY_RUN" != "yes" ]]; then
        do_cmd mkdir -p "$SDK_ROOT/ndk"
        local tmp_ndk
        tmp_ndk="$(mktemp --suffix=.tar.xz)"
        cecho cyan "  🌐 Downloading NDK r29..."
        curl -fLC - --progress-bar "$NDK_R29_URL" -o "$tmp_ndk"
        cecho cyan "  📦 Extracting NDK r29..."
        tar -xJf "$tmp_ndk" -C "$SDK_ROOT/ndk"
        rm -f "$tmp_ndk"
        if [[ -d "$SDK_ROOT/ndk/android-ndk-r29-beta4" && ! -d "$SDK_ROOT/ndk/$NDK_VERSION_DIR" ]]; then
          mv "$SDK_ROOT/ndk/android-ndk-r29-beta4" "$SDK_ROOT/ndk/$NDK_VERSION_DIR"
        fi
      fi
      cecho green "  ✅ NDK r29 installed at $SDK_ROOT/ndk/$NDK_VERSION_DIR."
    fi
  fi
}

### ================================
###  GENERATE 1-CLICK LAUNCH SCRIPT
### ================================
generate_launcher() {
  hr
  cecho magenta "🚀 Generating 1-Click Launch Script..."

  local launcher_path="$HOME/start-studio.sh"
  if [[ "$DRY_RUN" != "yes" ]]; then
    cat << EOF > "$launcher_path"
#!/usr/bin/env bash
# Android Studio Native Bionic Launcher
set -e

export DISPLAY="\${DISPLAY:-:0}"
export GDK_BACKEND=x11
unset LD_PRELOAD

export ANDROID_HOME="$SDK_ROOT"
export ANDROID_SDK_ROOT="$SDK_ROOT"
export PATH="\$PATH:$SDK_ROOT/platform-tools:$SDK_ROOT/cmdline-tools/latest/bin"

STUDIO_BIN="$ANDROID_STUDIO/bin/studio.sh"
if [ ! -f "\$STUDIO_BIN" ]; then
    echo "ERROR: \$STUDIO_BIN not found!"
    exit 1
fi

echo "=========================================================="
echo " Starting Android Studio natively on Android Bionic ARM64"
echo " DISPLAY : \$DISPLAY"
echo " SDK     : \$ANDROID_HOME"
echo "=========================================================="

exec "\$STUDIO_BIN" "\$@"
EOF
    chmod +x "$launcher_path"
  fi

  cecho green "✅ 1-Click launcher generated at: $launcher_path"
}

### ================================
###  SUMMARY & HINTS
### ================================
final_summary() {
  hr
  cecho bold "🎉 Android Studio is now patched for Native Android Bionic ARM64!"
  cat << EOF

👉 To launch Android Studio:
   $HOME/start-studio.sh

👉 Or launch directly:
   $ANDROID_STUDIO/bin/studio.sh

👉 Make sure Termux:X11 is running (or VNC server at :0).

👉 Useful project gradle.properties override:
   android.aapt2FromMavenOverride=$SDK_ROOT/build-tools/36.0.0/aapt2

EOF
}

### ================================
###  MENU
### ================================
show_menu() {
  hr
  cecho bold "📋 Android Studio Native Bionic Setup Menu:"
  echo "  1) Full Setup (Backup + Native Libs + JDK + Launcher/VM + HomuHomu SDK/NDK)"
  echo "  2) Patch Studio Only (Bionic Libs + Scripts/VM Options)"
  echo "  3) Termux OpenJDK Setup Only"
  echo "  4) HomuHomu SDK & NDK Install Only"
  echo "  5) Generate 1-Click Launcher Script ($HOME/start-studio.sh)"
  echo "  6) Quit"
  echo
}

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run|-n) DRY_RUN="yes";;
      *) cecho yellow "⚠ Unknown argument: $1 (ignored)";;
    esac
    shift
  done

  hr
  cecho bold "🔥 Android Studio Native Bionic ARM64 Fixer (Termux / Android) 🔥"
  if [[ "$DRY_RUN" == "yes" ]]; then
    cecho cyan "🧪 DRY-RUN MODE ENABLED — no filesystem changes or downloads will happen."
  fi

  detect_paths

  while true; do
    show_menu
    read -r -p "👉 Your choice [1-6]: " choice || choice=""
    case "$choice" in
      1)
        cecho magenta "▶ Running: FULL SETUP"
        backup_android_studio
        setup_termux_jdk
        patch_bionic_libs
        patch_scripts_and_vmoptions
        install_sdk_ndk
        generate_launcher
        final_summary
        break
        ;;
      2)
        cecho magenta "▶ Running: PATCH STUDIO ONLY"
        backup_android_studio
        patch_bionic_libs
        patch_scripts_and_vmoptions
        generate_launcher
        final_summary
        break
        ;;
      3)
        cecho magenta "▶ Running: TERMUX OPENJDK SETUP ONLY"
        setup_termux_jdk
        break
        ;;
      4)
        cecho magenta "▶ Running: SDK / NDK INSTALL ONLY"
        install_sdk_ndk
        break
        ;;
      5)
        cecho magenta "▶ Running: GENERATE 1-CLICK LAUNCHER"
        generate_launcher
        break
        ;;
      6)
        cecho yellow "👋 Bye."
        exit 0
        ;;
      *)
        cecho yellow "⚠ Invalid choice, please select 1-6."
        ;;
    esac
  done
}

main "$@"
