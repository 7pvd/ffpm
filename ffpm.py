#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFPM - Firefox Profile Manager
Copyright (C) 2025 Zuko <zuko.pro>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""


#              M""""""""`M            dP
#              Mmmmmm   .M            88
#              MMMMP  .MMM  dP    dP  88  .dP   .d8888b.
#              MMP  .MMMMM  88    88  88888"    88'  `88
#              M' .MMMMMMM  88.  .88  88  `8b.  88.  .88
#              M         M  `88888P'  dP   `YP  `88888P'
#              MMMMMMMMMMM    -*-  Created by Zuko  -*-
#
#              * * * * * * * * * * * * * * * * * * * * *
#              * -    - -   F.R.E.E.M.I.N.D   - -    - *
#              * -  Copyright © 2025 (Z) Programing  - *
#              *    -  -  All Rights Reserved  -  -    *
#              * * * * * * * * * * * * * * * * * * * * *
import subprocess
import sys

DEPS = ['typer[all]', None, None, 'watchdog']  # None cuz its built-in
DEP_CHECK_NAMES = ['typer', 'zipfile', 'shutil', 'watchdog']


def ensure_deps():
    for idx, dep in enumerate(DEP_CHECK_NAMES):
        if dep not in globals():
            try:
                globals()[dep] = __import__(dep)
            except ImportError:
                subprocess.check_call([sys.executable, "-m", "pip", "install", DEPS[idx]])
                __import__(dep)


ensure_deps()
import os
import shutil
import zipfile
from pathlib import Path
import typer
import time
import csv

import signal
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

app = typer.Typer(invoke_without_command=True)

FIREFOX_DIR = Path.home() / ".mozilla" / "firefox"  # Linux/macOS
PROFILES_INI = FIREFOX_DIR / "profiles.ini"
BACKUP_DIR = Path.home() / "firefox-profile-backups"


def get_profile_path(profile_name_or_path: str) -> Path:
    path = Path(profile_name_or_path).expanduser().resolve()
    if path.exists():
        return path
    profiles = get_profiles()
    if profile_name_or_path in profiles:
        return profiles[profile_name_or_path]
    backup_path = BACKUP_DIR / profile_name_or_path
    if backup_path.exists():
        return backup_path
    typer.echo(f"❌ Profile '{profile_name_or_path}' not found")
    raise typer.Exit(1)


def detect_windows_paths():
    import os
    global FIREFOX_DIR, PROFILES_INI, BACKUP_DIR
    if os.name == 'nt':
        FIREFOX_DIR = Path(os.environ['APPDATA']) / "Mozilla" / "Firefox"
        PROFILES_INI = FIREFOX_DIR / "profiles.ini"
        BACKUP_DIR = Path(os.environ['USERPROFILE']) / "firefox-profile-backups"
    else:
        print('is another system supported?')


detect_windows_paths()


class WatcherHandler(FileSystemEventHandler):
    def __init__(self, csv_path: Path, exclude_dirs = None):
        self.log_path = csv_path
        self.exclude_dirs = exclude_dirs or []
        self.events = {}
        
        if not self.log_path.exists():
            with self.log_path.open('w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "event_type", "file_path", "change_count"])
    
    def _log(self, event_type, path):
        now = datetime.now().isoformat(timespec='seconds')
        key = (event_type, path)
        if key in self.events:
            self.events[key]["count"] += 1
        else:
            self.events[key] = {"timestamp": now, "count": 1}
        
        # write/update line in csv
        with self.log_path.open('a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([now, event_type, path, self.events[key]["count"]])
    
    def on_any_event(self, event):
        if any(ex in event.src_path for ex in self.exclude_dirs):
            return
        if event.is_directory:
            return
        self._log(event.event_type, event.src_path)
        print(f"[{event.event_type.upper()}] {event.src_path}")


class Watcher:
    def __init__(self, watch_path: Path, csv_output: Path):
        self.watch_path = watch_path
        self.csv_output = csv_output
        self.event_handler = WatcherHandler(csv_output, exclude_dirs=["cache2", "startupCache", "minidumps"])
        self.observer = Observer()
    
    def start(self):
        print(f"👀 Starting watcher on: {self.watch_path}")
        self.observer.schedule(self.event_handler, str(self.watch_path), recursive=True)
        self.observer.start()
        
        def stop_handler(sig, frame):
            self.stop()
        
        signal.signal(signal.SIGINT, stop_handler)
        signal.signal(signal.SIGTERM, stop_handler)
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        print("🛑 Stopping watcher...")
        self.observer.stop()
        self.observer.join()
        print("✅ Watcher stopped cleanly.")
        sys.exit(0)


def get_profiles():
    profiles = {}
    if PROFILES_INI.exists():
        with PROFILES_INI.open() as f:
            current = {}
            for line in f:
                line = line.strip()
                if line.startswith("[Profile"):
                    if "Path" in current:
                        profiles[current["Name"]] = FIREFOX_DIR / current["Path"]
                    current = {}
                elif "=" in line:
                    k, v = line.split("=", 1)
                    current[k.strip()] = v.strip()
            if "Path" in current:
                profiles[current["Name"]] = FIREFOX_DIR / current["Path"]
    return profiles


@app.command()
def build(
        builder: str = typer.Option(..., "--builder", "-b",
                                    help="Build system to use: pyinstaller, briefcase, or nuitka")
):
    """
    Build a standalone executable using the selected builder.
    """
    # Skip build command if running from built executable
    if getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS'):
        typer.echo("❌ Build command not available in built executable")
        raise typer.Exit(1)
    
    # Activate virtual environment if exists
    venv_path = Path(".venv")
    env = os.environ.copy()
    if venv_path.exists():
        if os.name == 'nt':  # Windows
            venv_bin = venv_path / "Scripts"
            venv_site_packages = venv_path / "Lib" / "site-packages"
        else:  # Linux/macOS
            venv_bin = venv_path / "bin"
            # Find Python version dynamically
            python_dirs = list((venv_path / "lib").glob("python*"))
            if python_dirs:
                venv_site_packages = python_dirs[0] / "site-packages"
            else:
                venv_site_packages = venv_path / "lib" / "python3.11" / "site-packages"  # fallback
        
        # Prepend venv to PATH and PYTHONPATH
        env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")
        env["PYTHONPATH"] = str(venv_site_packages) + os.pathsep + env.get("PYTHONPATH", "")
        typer.echo(f"🐍 Using virtual environment: {venv_bin}")
        typer.echo(f"📦 Python packages from: {venv_site_packages}")
    
    builder = builder.lower()
    script_file = Path(sys.argv[0]).resolve()
    
    if builder == "pyinstaller":
        typer.echo("🔧 Building with PyInstaller...")
        try:
            subprocess.run(["pyinstaller", "--onefile", '--strip', '--icon=assets/ffpm_mac.ico', "--name", "ffpm",
                            str(script_file), "--clean"], check=True, env=env)
            typer.echo("✅ Build complete: ./dist/ffpm(.exe)")
        except subprocess.CalledProcessError:
            typer.echo("❌ Build failed with PyInstaller")
            raise typer.Exit(1)
    
    elif builder == "nuitka":
        typer.echo("🔧 Building with Nuitka...")
        try:
            # Use venv Python if available
            if venv_path.exists():
                if os.name == 'nt':
                    python_exe = venv_path / "Scripts" / "python.exe"
                else:
                    python_exe = venv_path / "bin" / "python"
            else:
                python_exe = "python"
            
            cmd = [
                str(python_exe), "-m", "nuitka",
                "--onefile",
                "--standalone",
                "--output-dir=dist",
                "--output-filename=ffpm",
                "--remove-output"
            ]
            
            # Add icon if exists
            if Path("assets/ffpm_mac.ico").exists():
                cmd.extend(["--windows-icon-from-ico=assets/ffpm_mac.ico"])
            elif Path("assets/ffpm.png").exists():
                cmd.extend(["--linux-icon=assets/ffpm.png"])
            
            cmd.append(str(script_file))
            typer.echo(f"command line (for debugging):\n {' '.join(cmd)}")
            
            subprocess.run(cmd, check=True, env=env)
            typer.echo("✅ Nuitka build complete: ./dist/ffpm(.exe)")
        except subprocess.CalledProcessError:
            typer.echo("❌ Build failed with Nuitka")
            raise typer.Exit(1)
    
    elif builder == "briefcase":
        typer.echo("🔧 Building with Briefcase...")
        try:
            # Ensure template project structure exists
            # do the following:
            # Remove-Item -Path ./build -Recurse -Force
            # Remove-Item -Path ./ffpm -Recurse -Force
            # Remove-Item -Path ./dist -Recurse -Force
            # mkdir ffpm
            # cp ffpm.py ffpm/__main__.py
            # run convert (it's long long command, so it's multiple lines below)
            # briefcase convert -Q formal_name="FFPM - Firefox Profile Manager - Zuko"
            # -Q description = "Simple Firefox profile manager, including import/export. Specially, you can use this tool to monitor a directory changes before/after action(s)."
            # -Q long_description = "Simple Firefox profile manager, including import/export. Specially, you can use this tool to monitor a directory changes before/after action(s)."
            # -Q author = "Zuko"
            # -Q author_email = "tansautn@gmail.com"
            # -Q url = "https://github.com/7pvd/ffpm"
            # -Q license = "GPL-3.0"
            # -Q version = "1.0.0"
            # -Q icon = "assets/ffpm_mac"
            # -Q bundle = "pro.zuko.ffpm"
            # -Q console_app = true
            # -Q license.file = "LICENSE.txt"
            # -Q sources = ["ffpm"]
            subprocess.run(["briefcase", "create"], check=True)
            subprocess.run(["briefcase", "build"], check=True)
            subprocess.run(["briefcase", "package"], check=True)
            typer.echo("✅ Briefcase build/package complete.")
        except subprocess.CalledProcessError:
            typer.echo("❌ Build failed with Briefcase")
            raise typer.Exit(1)
    
    else:
        typer.echo("❌ Unsupported builder. Use 'pyinstaller', 'nuitka', or 'briefcase'.")
        raise typer.Exit(1)


@app.command()
def watch(profile_name: str = typer.Argument(...), out: str = "watch-log.csv"):
    """Watch a Firefox profile for real-time changes and log to CSV"""
    # Load your profile path from mapping or config
    if Path(profile_name).exists():
        profile_path = Path(profile_name)
        typer.echo(f"Using direct path: {profile_path}")
    else:
        profile_path = get_profile_path(profile_name)
    if not profile_path.exists():
        typer.echo(f"❌ Profile {profile_name} not found")
        raise typer.Exit(1)
    
    log_file = Path(out)
    watcher = Watcher(profile_path, log_file)
    watcher.start()


@app.command()
def list():
    profiles = get_profiles()
    for name, path in profiles.items():
        typer.echo(f"{name}: {path}")


@app.command()
def export_profile(name: str, output: Path):
    if not output.endswith(".zip"):
        output = output.with_suffix(".zip")
    profiles = get_profiles()
    path = profiles.get(name)
    if not path or not path.exists():
        typer.echo("Profile not found.")
        raise typer.Exit(1)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(path):
            for file in files:
                full_path = os.path.join(root, file)
                zipf.write(full_path, os.path.relpath(full_path, start=path))
    typer.echo(f"Exported to {output}")


@app.command()
def import_profile(zip_path, name: str):
    if not (str(zip_path).index('/') == -1) or not (str(zip_path).index('/1') != -1):
        zip_path = get_profile_path(name)
        if not zip_path.exists():
            typer.echo("Profile not found.")
    dest_dir = FIREFOX_DIR / f"{name}"
    if dest_dir.exists():
        typer.confirm("Profile exists. Overwrite?", abort=True)
        shutil.rmtree(dest_dir)
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        zipf.extractall(dest_dir)
    typer.echo(f"Imported profile as '{name}' at {dest_dir}")


@app.command()
def clean(name: str):
    profiles = get_profiles()
    path = profiles.get(name)
    if not path:
        typer.echo("Profile not found.")
        raise typer.Exit(1)
    cache_dirs = ["cache2", "storage", "startupCache", "minidumps"]
    for cd in cache_dirs:
        target = path / cd
        if target.exists():
            shutil.rmtree(target)
            typer.echo(f"Removed: {target}")
    typer.echo("Clean completed.")


def main():
    exec = sys.executable
    
    if len(sys.argv) == 1:
        
        # Run help via subprocess (safe for both .py and .exe)
        args = []
        if 'py' in str(exec):
            args.append(sys.argv[0])
        subprocess.run([exec, *args, "--help"])
        return 0
    app(prog_name="ffpm")


if __name__ == "__main__":
    main()
