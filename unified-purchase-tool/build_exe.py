import os, sys, shutil, subprocess

# ============================================================
# 统一采购工具集 — EXE 构建脚本
# 策略：编译精简启动器 EXE，实际运行靠 pythonw.exe + 源码
# ============================================================

SRC = r"C:\Users\19811\.claude\projects\unified-purchase-tool"
PROJECT_NAME = "采购工作台"

# ── 启动器源码 ──────────────────────────────────────────────
launcher = rf'''import os, sys, subprocess
# 源码目录
project_dir = r"{SRC}"
os.chdir(project_dir)
main_py = os.path.join(project_dir, "main.py")
pythonw = r"C:\Users\19811\AppData\Local\Programs\Python\Python312\pythonw.exe"
try:
    subprocess.Popen([pythonw, main_py], cwd=project_dir)
except Exception:
    # 出错时用 python.exe 启动，可以看到控制台报错
    subprocess.Popen(
        [r"C:\Users\19811\AppData\Local\Programs\Python\Python312\python.exe", main_py],
        cwd=project_dir,
    )
'''

launcher_path = os.path.join(SRC, "_launcher.py")
with open(launcher_path, "w", encoding="utf-8") as f:
    f.write(launcher)

# ── 清理旧构建 ─────────────────────────────────────────────
for d in ["build", "dist"]:
    shutil.rmtree(os.path.join(SRC, d), ignore_errors=True)
for sub in ["unified"]:
    pycache = os.path.join(SRC, sub, "__pycache__")
    shutil.rmtree(pycache, ignore_errors=True)

# ── PyInstaller 编译 ──────────────────────────────────────
print("Building launcher EXE...")
os.chdir(SRC)

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--noconsole",
    "--name", PROJECT_NAME,
    # 排除所有重型依赖，只打包精简启动器
    "--exclude-module", "PySide6",
    "--exclude-module", "paddleocr",
    "--exclude-module", "paddle",
    "--exclude-module", "paddlepaddle",
    "--exclude-module", "PIL",
    "--exclude-module", "numpy",
    "--exclude-module", "fitz",
    "--exclude-module", "PyMuPDF",
    "--exclude-module", "dotenv",
    "--exclude-module", "python_dotenv",
    "--exclude-module", "openpyxl",
    "--exclude-module", "keyboard",
    "--exclude-module", "pywin32",
    "--exclude-module", "psutil",
    "--exclude-module", "uiautomation",
    "--exclude-module", "comtypes",
    "--exclude-module", "pdfplumber",
    "--exclude-module", "win32com",
    "--exclude-module", "pythoncom",
    "_launcher.py",
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
if result.returncode != 0:
    print("BUILD FAILED")
    err = (result.stderr or "")[-3000:] or (result.stdout or "")[-3000:]
    print(err)
    sys.exit(1)

print("Build successful!")

# ── 复制到桌面 ────────────────────────────────────────────
exe_src = os.path.join(SRC, "dist", f"{PROJECT_NAME}.exe")
desktop_exe = rf"C:\Users\19811\Desktop\{PROJECT_NAME}.exe"

# 删掉旧的 bat
old_bat = rf"C:\Users\19811\Desktop\{PROJECT_NAME}.bat"
if os.path.exists(old_bat):
    os.remove(old_bat)
    print(f"Deleted old bat: {old_bat}")

if os.path.exists(desktop_exe):
    os.remove(desktop_exe)
shutil.copy2(exe_src, desktop_exe)
print(f"EXE 已复制到桌面: {desktop_exe}")

# ── 清理构建产物 ──────────────────────────────────────────
shutil.rmtree(os.path.join(SRC, "build"), ignore_errors=True)
shutil.rmtree(os.path.join(SRC, "dist"), ignore_errors=True)
os.remove(launcher_path)
for f in os.listdir(SRC):
    if f.endswith(".spec"):
        os.remove(os.path.join(SRC, f))

print(f"\n完成！桌面上已有: {PROJECT_NAME}.exe")
