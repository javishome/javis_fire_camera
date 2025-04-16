import os
import shutil
import json
import subprocess
from datetime import datetime

# Cấu hình phiên bản cần release
VERSION = "2024_4_4"
PYTHON_VERSION = "python_12"  # hoặc python13 tùy version
ROOT_DIR = os.getcwd()
BUILD_DIR = os.path.join(ROOT_DIR, "build", VERSION)
MAIN_CODE_DIR = os.path.join(ROOT_DIR, "main_code", VERSION)

def remove_old_build():
    if os.path.exists(BUILD_DIR):
        print(f"🧹 Removing old build folder: {BUILD_DIR}")
        shutil.rmtree(BUILD_DIR)
    else:
        print("✅ No previous build to remove.")

def update_manifest_version():
    manifest_path = os.path.join(MAIN_CODE_DIR, "manifest.json")
    if not os.path.exists(manifest_path):
        print(f"❌ manifest.json not found in {MAIN_CODE_DIR}")
        return
    with open(manifest_path, "r+", encoding="utf-8") as f:
        data = json.load(f)
        data["version"] = VERSION.replace("_", ".")
        f.seek(0)
        json.dump(data, f, indent=4)
        f.truncate()
    print(f"📝 Updated manifest.json version to {data['version']}")

def copy_main_code_to_build():
    print(f"📁 Copying from {MAIN_CODE_DIR} to {BUILD_DIR}")
    shutil.copytree(MAIN_CODE_DIR, BUILD_DIR)

def encode_py_files():
    print("🚀 Encoding .py files to .pyc")
    os.chdir(BUILD_DIR)
    result = subprocess.run(["python", "encode.py"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Encode failed: {result.stderr}")
    else:
        print(f"✅ Encode successful: {result.stdout}")

def check_encoded_files():
    expected_files = ["websocket_client.pyc", "api.pyc"]
    for file in expected_files:
        if os.path.exists(file):
            print(f"✅ Found encoded file: {file}")
        else:
            print(f"❌ Missing encoded file: {file}")

def git_commit_and_push():
    os.chdir(ROOT_DIR)
    print("📦 Committing and pushing to Git")
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", f"Release version {VERSION}"], check=True)
    subprocess.run(["git", "push"], check=True)

def main():
    print(f"🔁 Starting release process for version {VERSION}")
    remove_old_build()
    update_manifest_version()
    copy_main_code_to_build()

    print(f"🔧 Now activate conda env manually: conda activate {PYTHON_VERSION}")
    input("⏸ After activating conda environment, press ENTER to continue...")

    encode_py_files()
    check_encoded_files()
    git_commit_and_push()
    print("🎉 Release process completed!")

if __name__ == "__main__":
    main()
