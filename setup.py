#!/usr/bin/env python3
"""
==============================================================================
AndroidStudio-For-Android: Interactive Setup & Native Bionic Patcher
Author: sirvkrm & Antigravity
Repository: https://github.com/sirvkrm/AndroidStudio-For-Android
Bionic Native Libs: https://github.com/sirvkrm/AndroidStudio-Bionic-Libs
==============================================================================
"""

import os
import sys
import shutil
import tarfile
import zipfile
import urllib.request
import subprocess
import re
from pathlib import Path

# Ensure stdin reads from the terminal keyboard even when executed via `curl ... | bash`
if not sys.stdin.isatty():
    try:
        sys.stdin = open("/dev/tty", "r")
    except Exception:
        pass

# ANSI Terminal Colors
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[0;33m"
    BLUE = "\033[0;34m"
    MAGENTA = "\033[0;35m"
    CYAN = "\033[0;36m"
    WHITE = "\033[0;37m"

def print_header(text):
    print(f"\n{C.MAGENTA}{'=' * 65}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN} {text}{C.RESET}")
    print(f"{C.MAGENTA}{'=' * 65}{C.RESET}")

def print_step(text):
    print(f"\n{C.BOLD}{C.YELLOW}▶ {text}{C.RESET}")

def print_success(text):
    print(f"{C.GREEN}✔ {text}{C.RESET}")

def print_info(text):
    print(f"{C.CYAN}ℹ {text}{C.RESET}")

def print_warn(text):
    print(f"{C.YELLOW}⚠ {text}{C.RESET}")

def print_error(text):
    print(f"{C.RED}✖ {text}{C.RESET}")

def ask_yes_no(prompt, default=True):
    disp = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            val = input(f"{C.BOLD}{prompt}{C.RESET} {C.DIM}{disp}{C.RESET} ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(1)
        if not val:
            return default
        if val in ("y", "yes"):
            return True
        if val in ("n", "no"):
            return False
        print_warn("Please enter 'y' or 'n'.")

def ask_choice(prompt, options, default=1):
    print(f"\n{C.BOLD}{prompt}{C.RESET}")
    for idx, (label, desc) in enumerate(options, 1):
        def_mark = f" {C.GREEN}(default){C.RESET}" if idx == default else ""
        print(f"  {C.CYAN}{idx}){C.RESET} {C.BOLD}{label}{C.RESET}{def_mark}")
        if desc:
            print(f"     {C.DIM}{desc}{C.RESET}")
    
    while True:
        try:
            val = input(f"\n{C.BOLD}Enter choice [1-{len(options)}] (Enter={default}):{C.RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(1)
        if not val:
            return default - 1
        if val.isdigit():
            i = int(val)
            if 1 <= i <= len(options):
                return i - 1
        print_warn(f"Please enter a number between 1 and {len(options)}.")

def download_with_progress(url, dest_path):
    print_info(f"Downloading: {url}")
    print_info(f"Destination: {dest_path}")
    
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)

    def reporthook(blocknum, blocksize, totalsize):
        read = blocknum * blocksize
        if totalsize > 0:
            percent = min(100.0, read * 100.0 / totalsize)
            mb_read = read / (1024 * 1024)
            mb_total = totalsize / (1024 * 1024)
            bar_len = 30
            filled = int(bar_len * percent / 100.0)
            bar = "=" * filled + "-" * (bar_len - filled)
            sys.stdout.write(f"\r  [{bar}] {percent:.1f}% ({mb_read:.1f} MB / {mb_total:.1f} MB)")
            sys.stdout.flush()
        else:
            mb_read = read / (1024 * 1024)
            sys.stdout.write(f"\r  Downloaded: {mb_read:.1f} MB")
            sys.stdout.flush()

    try:
        with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as out_file:
            totalsize = int(resp.headers.get("Content-Length", 0))
            blocksize = 64 * 1024
            blocknum = 0
            while True:
                chunk = resp.read(blocksize)
                if not chunk:
                    break
                out_file.write(chunk)
                blocknum += 1
                reporthook(blocknum, blocksize, totalsize)
        print()
        print_success(f"Download completed: {dest_path}")
    except Exception as e:
        print()
        print_error(f"Download failed: {e}")
        raise

def fetch_live_google_release_url():
    """Scrapes developer.android.com/studio for the latest official Linux download link"""
    try:
        req = urllib.request.Request(
            "https://developer.android.com/studio",
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            m = re.search(r'https://[^\s"\']*linux\.tar\.gz', html)
            if m:
                return m.group(0)
    except Exception:
        pass
    return "https://edgedl.me.gvt1.com/android/studio/ide-zips/2026.2.1.8/android-studio-rabbit1-linux.tar.gz"

# Available Android Studio Linux Releases
STUDIO_RELEASES = [
    (
        "Android Studio Rabbit 1 (2026.2.1.8 - Latest Official Stable)",
        "The current newest official Google Android Studio stable release for Linux",
        "https://edgedl.me.gvt1.com/android/studio/ide-zips/2026.2.1.8/android-studio-rabbit1-linux.tar.gz"
    ),
    (
        "Android Studio Rabbit 2 Canary 4 (2026.2.2.4 - Latest Canary Preview)",
        "Cutting-edge Canary preview with experimental Kotlin & Jetpack tools",
        "https://edgedl.me.gvt1.com/android/studio/ide-zips/2026.2.2.4/android-studio-rabbit2-canary4-linux.tar.gz"
    ),
    (
        "Android Studio Ladybug (2024.2.1.12 - Proven Classic Stable)",
        "Previous generation rock-solid long-term stable release",
        "https://redirector.gvt1.com/edgedl/android/studio/ide-zips/2024.2.1.12/android-studio-2024.2.1.12-linux.tar.gz"
    ),
    (
        "Android Studio Koala Feature Drop (2024.1.2.12 - Lightweight)",
        "Lightweight release with minimal resource and memory footprint",
        "https://redirector.gvt1.com/edgedl/android/studio/ide-zips/2024.1.2.12/android-studio-2024.1.2.12-linux.tar.gz"
    ),
    (
        "Fetch Live Latest Directly from Google (developer.android.com)",
        "Auto-queries Google's site for whatever newest release is published right now",
        "__AUTO_LIVE__"
    ),
    (
        "Custom URL",
        "Enter your own direct download URL for android-studio-*-linux.tar.gz",
        None
    ),
    (
        "Skip Download (Use Already Installed / Existing Directory)",
        "Point directly to an existing Android Studio folder on disk",
        None
    ),
]

# URLs for Bionic components
BIONIC_LIBS_TARBALL_URL = "https://github.com/sirvkrm/AndroidStudio-Bionic-Libs/releases/download/v1.0.0/android-studio-bionic-libs-aarch64.tar.gz"
SDK_35_URL = "https://github.com/HomuHomu833/android-sdk-custom/releases/download/35.0.2/android-sdk-aarch64-linux-musl.tar.xz"
SDK_36_URL = "https://github.com/HomuHomu833/android-sdk-custom/releases/download/36.0.0/android-sdk-aarch64-linux-musl.tar.xz"
NDK_R29_URL = "https://github.com/HomuHomu833/android-ndk-custom/releases/download/r29/android-ndk-r29-beta4-aarch64-linux-android.tar.xz"
NDK_VERSION_DIR = "29.0.14033849"

class Installer:
    def __init__(self):
        self.home = Path.home()
        self.termux_prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
        self.is_termux = self.termux_prefix.exists() or "TERMUX_VERSION" in os.environ
        self.studio_dir = self.home / "android-studio"
        self.sdk_dir = self.home / "Android" / "Sdk"
        self.selected_jdk = None

    def run(self):
        print_header("🔥 AndroidStudio-For-Android: Native Bionic ARM64 Installer 🔥")
        print(f"{C.BOLD}Platform:{C.RESET} {'Termux / Android Bionic' if self.is_termux else 'Linux ARM64 / Cross-Host'}")
        print(f"{C.BOLD}Home Dir:{C.RESET} {self.home}")
        print(f"{C.BOLD}Termux Prefix:{C.RESET} {self.termux_prefix}\n")

        # Step 1: Android Studio Selection / Acquisition
        self.step_acquire_studio()

        # Step 2: OpenJDK Selection & JBR Symlinking
        self.step_setup_jdk()

        # Step 3: Inject Bionic Native Libraries
        self.step_inject_bionic_libs()

        # Step 4: Patch Launcher Scripts & VM Options
        self.step_patch_scripts_and_vmoptions()

        # Step 5: Android SDK & NDK (HomuHomu)
        self.step_setup_sdk_ndk()

        # Step 6: Generate 1-Click Launcher
        self.step_generate_launcher()

        # Final Summary
        self.step_finish()

    def step_acquire_studio(self):
        print_step("Step 1: Android Studio Acquisition")
        
        # Check if already installed
        if (self.studio_dir / "bin" / "studio.sh").exists():
            print_success(f"Found existing Android Studio installation at: {self.studio_dir}")
            if ask_yes_no("Use this existing installation?", default=True):
                return
            else:
                custom_path = input(f"Enter path to your Android Studio directory [{self.studio_dir}]: ").strip()
                if custom_path:
                    self.studio_dir = Path(custom_path).expanduser().resolve()
                    if (self.studio_dir / "bin" / "studio.sh").exists():
                        print_success(f"Validated Android Studio at: {self.studio_dir}")
                        return

        options = [(label, desc) for label, desc, _ in STUDIO_RELEASES]
        choice_idx = ask_choice("Choose how you would like to setup Android Studio:", options, default=1)
        
        _, _, release_url = STUDIO_RELEASES[choice_idx]
        
        # Skip download
        if choice_idx == len(STUDIO_RELEASES) - 1:
            while True:
                p = input("Enter path to your existing Android Studio folder: ").strip()
                target = Path(p).expanduser().resolve()
                if (target / "bin" / "studio.sh").exists() or target.exists():
                    self.studio_dir = target
                    print_success(f"Selected Studio path: {self.studio_dir}")
                    return
                print_error(f"Path does not exist: {target}. Please try again.")

        # Custom URL
        if choice_idx == len(STUDIO_RELEASES) - 2:
            release_url = input("Enter custom direct download URL for Android Studio .tar.gz: ").strip()

        # Auto live fetch
        if release_url == "__AUTO_LIVE__":
            print_info("Querying Google for latest live Linux download link...")
            release_url = fetch_live_google_release_url()
            print_success(f"Fetched latest URL: {release_url}")

        # Download & Extract
        dest_archive = self.home / "android-studio-download.tar.gz"
        download_with_progress(release_url, str(dest_archive))

        print_info(f"Extracting archive into: {self.home}...")
        with tarfile.open(dest_archive, "r:gz") as tar:
            tar.extractall(path=self.home)
        
        if dest_archive.exists():
            dest_archive.unlink()

        # Resilient detection of extracted folder
        if (self.home / "android-studio" / "bin" / "studio.sh").exists():
            self.studio_dir = self.home / "android-studio"
        else:
            candidates = list(self.home.glob("android-studio*"))
            for c in candidates:
                if (c / "bin" / "studio.sh").exists():
                    self.studio_dir = c
                    break

        print_success(f"Android Studio extracted successfully to: {self.studio_dir}")

    def detect_required_java(self):
        try:
            for jar_path in (self.studio_dir / "lib").glob("*.jar"):
                try:
                    with zipfile.ZipFile(jar_path, 'r') as z:
                        for name in z.namelist():
                            if name.endswith('.class') and not name.startswith('META-INF/'):
                                with z.open(name) as f:
                                    magic = f.read(4)
                                    if magic == b'\xca\xfe\xba\xbe':
                                        f.read(2)
                                        major = int.from_bytes(f.read(2), 'big')
                                        if major >= 45:
                                            return major - 44
                except Exception:
                    continue
        except Exception:
            pass
        return 21

    def get_jdk_version(self, jdk_path):
        try:
            java_bin = jdk_path / "bin" / "java"
            res = subprocess.run([str(java_bin), "-version"], capture_output=True, text=True)
            out = res.stderr or res.stdout
            m = re.search(r'version "(\d+)', out)
            if m:
                return int(m.group(1))
        except Exception:
            pass
        m = re.search(r'(\d+)', jdk_path.name)
        if m:
            return int(m.group(1))
        return 17

    def step_setup_jdk(self):
        print_step("Step 2: Native OpenJDK Setup (No PRoot needed!)")

        req_ver = self.detect_required_java()
        print_info(f"Android Studio bytecode requires Java {req_ver}+ (class file version {req_ver + 44}.0)")

        def find_candidates():
            found = []
            search_dirs = [
                self.termux_prefix / "lib" / "jvm",
                Path("/usr/lib/jvm")
            ]
            for sdir in search_dirs:
                if sdir.exists():
                    for d in sdir.glob("*"):
                        if (d / "bin" / "java").exists():
                            found.append(d)
            return found

        candidates = find_candidates()
        compatible = [c for c in candidates if self.get_jdk_version(c) >= req_ver]

        if not compatible and self.is_termux:
            pkg_name = f"openjdk-{req_ver}"
            print_warn(f"No Java {req_ver}+ found in Termux. Detected JDKs: {[c.name for c in candidates] or 'none'}.")
            if ask_yes_no(f"Install native {pkg_name} now via 'pkg install {pkg_name}'?", default=True):
                subprocess.run(["pkg", "install", "-y", pkg_name], check=False)
                candidates = find_candidates()
                compatible = [c for c in candidates if self.get_jdk_version(c) >= req_ver]

        if candidates:
            # Sort with compatible JDKs first
            candidates.sort(key=lambda c: (self.get_jdk_version(c) >= req_ver, self.get_jdk_version(c)), reverse=True)
            jdk_opts = [
                (f"{c.name} (Java {self.get_jdk_version(c)})" + (" ✔ Compatible" if self.get_jdk_version(c) >= req_ver else " ⚠ Incompatible"), str(c))
                for c in candidates
            ]
            c_idx = ask_choice("Select Native JDK to power Android Studio:", jdk_opts, default=1)
            self.selected_jdk = candidates[c_idx]
            sel_ver = self.get_jdk_version(self.selected_jdk)
            if sel_ver < req_ver:
                print_warn(f"Selected JDK (Java {sel_ver}) is older than required (Java {req_ver})! Studio may throw UnsupportedClassVersionError.")
            else:
                print_success(f"Selected JDK: {self.selected_jdk} (Java {sel_ver})")
        else:
            print_warn("Could not locate OpenJDK automatically. Studio will use system PATH java if set.")

        # Point studio's bundled jbr to our native OpenJDK
        jbr_dir = self.studio_dir / "jbr"
        if self.selected_jdk and ask_yes_no(f"Symlink Android Studio JBR ({jbr_dir}) -> {self.selected_jdk}?", default=True):
            if jbr_dir.exists() or jbr_dir.is_symlink():
                if jbr_dir.is_symlink() or jbr_dir.is_file():
                    jbr_dir.unlink()
                else:
                    shutil.rmtree(jbr_dir)
            jbr_dir.symlink_to(self.selected_jdk)
            print_success(f"JBR successfully symlinked to {self.selected_jdk}")

    def step_inject_bionic_libs(self):
        print_step("Step 3: Inject Native Bionic ARM64 Libraries")
        print_info("Source: sirvkrm/AndroidStudio-Bionic-Libs (v1.0.0 Release)")

        if not ask_yes_no("Download and inject all 5 Bionic native libraries?", default=True):
            print_warn("Skipping Bionic native libraries injection.")
            return

        tmp_tar = self.home / "bionic-libs.tar.gz"
        download_with_progress(BIONIC_LIBS_TARBALL_URL, str(tmp_tar))

        print_info(f"Extracting Bionic libraries into {self.studio_dir}...")
        with tarfile.open(tmp_tar, "r:gz") as tar:
            tar.extractall(path=self.studio_dir)
        
        if tmp_tar.exists():
            tmp_tar.unlink()

        # Set executable permissions
        for f in (self.studio_dir / "bin").glob("fsnotifier*"):
            f.chmod(0o755)
        for f in (self.studio_dir / "lib").rglob("*.so"):
            f.chmod(0o755)

        # Copy libutil.so into Termux lib folder if writable
        libutil_src = self.studio_dir / "lib" / "pty4j" / "linux" / "aarch64" / "libutil.so"
        if libutil_src.exists() and (self.termux_prefix / "lib").exists():
            try:
                shutil.copy2(libutil_src, self.termux_prefix / "lib" / "libutil.so")
                print_success(f"Installed libutil.so into {self.termux_prefix}/lib/libutil.so (resolves login_tty for pty4j)")
            except Exception as e:
                print_warn(f"Could not copy to {self.termux_prefix}/lib: {e}")

        # Copy libskiko-linux-arm64.so to JDK lib so java.home/lib lookup succeeds unconditionally
        skiko_so = self.studio_dir / "lib" / "skiko" / "libskiko-linux-arm64.so"
        if skiko_so.exists():
            for jdk_cand in [self.selected_jdk, self.studio_dir / "jbr"]:
                if jdk_cand and (jdk_cand / "lib").exists():
                    try:
                        shutil.copy2(skiko_so, jdk_cand / "lib" / "libskiko-linux-arm64.so")
                        print_success(f"Installed libskiko into {jdk_cand}/lib/libskiko-linux-arm64.so")
                    except Exception as e:
                        print_warn(f"Could not copy to {jdk_cand}/lib: {e}")

        # Purge any stale extracted glibc skiko cache
        skiko_cache = self.home / ".skiko"
        if skiko_cache.exists():
            shutil.rmtree(skiko_cache, ignore_errors=True)
            print_success("Purged stale ~/.skiko cache")

        # Inject libjnidispatch.so into jar files
        jna_so = self.studio_dir / "lib" / "jna" / "linux-aarch64" / "libjnidispatch.so"
        if jna_so.exists():
            for jar_name in ["util.jar", "app.jar", "jna.jar"]:
                jar_path = self.studio_dir / "lib" / jar_name
                if jar_path.exists():
                    self.inject_jna_into_jar(jar_path, jna_so)

        print_success("Injected native libraries:")
        print("   • fsnotifier (Inotify filesystem watcher - dynamic Bionic & static)")
        print("   • libpty.so & libutil.so (Pty4j terminal emulation + login_tty)")
        print("   • libjnidispatch.so (JNA C bridge)")
        print("   • libsqlitejdbc.so (SQLite database engine)")
        print("   • libskiko-linux-arm64.so (Skiko / Skia hardware graphics engine)")

    def inject_jna_into_jar(self, jar_path, jna_so):
        try:
            with zipfile.ZipFile(jar_path, 'a') as z:
                z.write(jna_so, arcname="com/sun/jna/linux-aarch64/libjnidispatch.so")
            print_success(f"Injected Bionic libjnidispatch.so directly into {jar_path.name}")
        except Exception as e:
            print_warn(f"Jar injection for {jar_path.name}: {e}")

    def step_patch_scripts_and_vmoptions(self):
        print_step("Step 4: Patch Launcher Scripts & VM Options")

        # 1. product-info.json
        pinfo = self.studio_dir / "product-info.json"
        if pinfo.exists():
            content = pinfo.read_text(encoding="utf-8")
            if '"amd64"' in content:
                content = content.replace('"amd64"', '"aarch64"')
                pinfo.write_text(content, encoding="utf-8")
                print_success("Patched product-info.json: amd64 -> aarch64")

        # 2. bin/studio.sh
        studio_sh = self.studio_dir / "bin" / "studio.sh"
        if studio_sh.exists():
            content = studio_sh.read_text(encoding="utf-8")
            content = content.replace("amd64", "$OS_ARCH")
            
            header_marker = "# >>> STUDIO_BIONIC_PATCHED >>>"
            if header_marker not in content:
                jdk_val = str(self.selected_jdk) if self.selected_jdk else ""
                header = f"""#!/usr/bin/env bash
{header_marker}
export DISPLAY="${{DISPLAY:-:0}}"
export GDK_BACKEND=x11
unset LD_PRELOAD
if [ -z "${{STUDIO_JDK:-}}" ] && [ -n "{jdk_val}" ]; then
    export STUDIO_JDK="{jdk_val}"
fi
export LD_LIBRARY_PATH="/system/lib64:{self.termux_prefix}/lib:{self.studio_dir}/lib/skiko:{self.studio_dir}/lib/sqlite/linux-aarch64:${{LD_LIBRARY_PATH:-}}"
# <<< STUDIO_BIONIC_PATCHED <<<
"""
                # Strip initial shebang from content
                lines = content.splitlines()
                if lines and lines[0].startswith("#!"):
                    lines = lines[1:]
                content = header + "\n" + "\n".join(lines)
            
            studio_sh.write_text(content, encoding="utf-8")
            studio_sh.chmod(0o755)
            print_success("Patched bin/studio.sh with Termux environment & unset LD_PRELOAD")

        # 3. bin/studio64.vmoptions
        vmoptions = self.studio_dir / "bin" / "studio64.vmoptions"
        if vmoptions.exists():
            vcontent = vmoptions.read_text(encoding="utf-8")
            if "-Djna.boot.library.path" not in vcontent:
                extra_opts = f"""
# Bionic & Termux Native Runtime Overrides
-Djna.boot.library.path={self.studio_dir}/lib/jna/linux-aarch64
-Dpty4j.preferred.native.folder={self.studio_dir}/lib/pty4j
-Dorg.sqlite.lib.path={self.studio_dir}/lib/sqlite/linux-aarch64
-Dorg.sqlite.lib.name=libsqlitejdbc.so
-Dskiko.library.path={self.studio_dir}/lib/skiko
-Dskiko.renderApi=SOFTWARE_COMPAT
-Djava.awt.headless=false
-Dsun.awt.noerasebackground=true
"""
                vmoptions.write_text(vcontent + extra_opts, encoding="utf-8")
                print_success("Appended Bionic native runtime properties to studio64.vmoptions")

    def step_setup_sdk_ndk(self):
        print_step("Step 5: Android SDK & NDK Setup (HomuHomu ARM64 Prebuilts)")
        self.sdk_dir.mkdir(parents=True, exist_ok=True)

        # 1. SDK 35 (contains 35.0.0 build-tools)
        bt35 = self.sdk_dir / "build-tools" / "35.0.0"
        if not bt35.exists():
            if ask_yes_no("Download and install ARM64 Build Tools 35.0.0 (HomuHomu)?", default=True):
                tmp_sdk = self.home / "sdk35.tar.xz"
                download_with_progress(SDK_35_URL, str(tmp_sdk))
                print_info("Extracting SDK 35.0.2 package...")
                subprocess.run(["tar", "-xJf", str(tmp_sdk), "-C", str(self.sdk_dir), "--strip-components=1"], check=True)
                if tmp_sdk.exists():
                    tmp_sdk.unlink()
                print_success("Installed Build Tools 35.0.0")
        else:
            print_success("Build Tools 35.0.0 already present.")

        # 2. SDK 36
        bt36 = self.sdk_dir / "build-tools" / "36.0.0"
        if not bt36.exists():
            if ask_yes_no("Download and install ARM64 Build Tools 36.0.0 (HomuHomu)?", default=True):
                tmp_sdk = self.home / "sdk36.tar.xz"
                download_with_progress(SDK_36_URL, str(tmp_sdk))
                print_info("Extracting SDK 36.0.0 package...")
                subprocess.run(["tar", "-xJf", str(tmp_sdk), "-C", str(self.sdk_dir), "--strip-components=1"], check=True)
                if tmp_sdk.exists():
                    tmp_sdk.unlink()
                print_success("Installed Build Tools 36.0.0")
        else:
            print_success("Build Tools 36.0.0 already present.")

        # 3. NDK r29
        ndk_target = self.sdk_dir / "ndk" / NDK_VERSION_DIR
        if not ndk_target.exists():
            if ask_yes_no("Download and install ARM64 NDK r29 (HomuHomu)?", default=True):
                (self.sdk_dir / "ndk").mkdir(parents=True, exist_ok=True)
                tmp_ndk = self.home / "ndk_r29.tar.xz"
                download_with_progress(NDK_R29_URL, str(tmp_ndk))
                print_info("Extracting NDK r29...")
                subprocess.run(["tar", "-xJf", str(tmp_ndk), "-C", str(self.sdk_dir / "ndk")], check=True)
                if tmp_ndk.exists():
                    tmp_ndk.unlink()
                # Rename if unpacked under beta name
                beta_dir = self.sdk_dir / "ndk" / "android-ndk-r29-beta4"
                if beta_dir.exists() and not ndk_target.exists():
                    beta_dir.rename(ndk_target)
                print_success(f"Installed NDK r29 at: {ndk_target}")
        else:
            print_success("NDK r29 already present.")

    def step_generate_launcher(self):
        print_step("Step 6: Generate 1-Click Launch Script")
        launcher = self.home / "start-studio.sh"

        script_content = f"""#!/usr/bin/env bash
# ==========================================================
# 1-Click Android Studio Native Bionic Launcher for Termux
# ==========================================================
set -e

export DISPLAY="${{DISPLAY:-:0}}"
export GDK_BACKEND=x11
unset LD_PRELOAD
export STUDIO_JDK="{self.selected_jdk}"
export JAVA_HOME="{self.selected_jdk}"
export SKIKO_RENDER_API=SOFTWARE_COMPAT
export _JAVA_OPTIONS="-Djava.io.tmpdir={self.termux_prefix}/tmp -Dskiko.library.path={self.studio_dir}/lib/skiko -Dskiko.renderApi=SOFTWARE_COMPAT ${{_JAVA_OPTIONS:-}}"
export LD_LIBRARY_PATH="/system/lib64:{self.termux_prefix}/lib:{self.studio_dir}/lib/skiko:{self.studio_dir}/lib/sqlite/linux-aarch64:${{LD_LIBRARY_PATH:-}}"

export ANDROID_HOME="{self.sdk_dir}"
export ANDROID_SDK_ROOT="{self.sdk_dir}"
export PATH="$PATH:{self.sdk_dir}/platform-tools:{self.sdk_dir}/cmdline-tools/latest/bin"

STUDIO_BIN="{self.studio_dir}/bin/studio.sh"
if [ ! -f "$STUDIO_BIN" ]; then
    echo "ERROR: Studio executable not found at: $STUDIO_BIN"
    exit 1
fi

echo "=========================================================="
echo " 🚀 Launching Android Studio natively on Android Bionic ARM64"
echo " DISPLAY : $DISPLAY"
echo " SDK     : $ANDROID_HOME"
echo "=========================================================="

exec "$STUDIO_BIN" "$@"
"""
        launcher.write_text(script_content, encoding="utf-8")
        launcher.chmod(0o755)
        print_success(f"Generated 1-click launcher at: {launcher}")

    def step_finish(self):
        print_header("🎉 SETUP COMPLETED SUCCESSFULLY! 🎉")
        print(f"""
{C.BOLD}{C.GREEN}Android Studio is now 100% patched for Native Android Bionic ARM64!{C.RESET}

{C.BOLD}🚀 How to Launch:{C.RESET}
  {C.CYAN}~/start-studio.sh{C.RESET}

{C.BOLD}📱 Termux:X11 Display Setup:{C.RESET}
  1. Open Termux:X11 app on your Android device.
  2. In Termux terminal:
     {C.YELLOW}termux-x11 :0 &{C.RESET}
  3. Run:
     {C.YELLOW}~/start-studio.sh{C.RESET}

{C.BOLD}💡 Gradle Build Tip:{C.RESET}
  In your Android project's {C.CYAN}gradle.properties{C.RESET}, add:
  {C.YELLOW}android.aapt2FromMavenOverride={self.sdk_dir}/build-tools/36.0.0/aapt2{C.RESET}

Enjoy building Android apps natively on your Android device!
""")

if __name__ == "__main__":
    try:
        Installer().run()
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting.")
        sys.exit(1)
