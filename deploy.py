import subprocess
import shutil
import os
import sys

print("=== Step 1: Syncing Python dependencies (pywrangler sync) ===")
# Sync dependencies into python_modules
res_sync = subprocess.run(["pywrangler", "sync"], capture_output=True, text=True)
if res_sync.returncode != 0:
    print(f"CRITICAL: pywrangler sync failed with code {res_sync.returncode}")
    if res_sync.stderr:
        print("--- STDERR ---")
        print(res_sync.stderr)
    print("--- STDOUT ---")
    print(res_sync.stdout[-1500:])
    sys.exit(res_sync.returncode)
print("Dependencies successfully synced into python_modules.")

print("=== Step 2: Optimizing bundle size to fit within Cloudflare limits ===")
# Remove .venv-workers staging environment (16+ MB duplicate of python_modules)
if os.path.exists(".venv-workers"):
    shutil.rmtree(".venv-workers", ignore_errors=True)
    print("✓ Removed duplicate .venv-workers staging directory.")

# Prune unused GIS and database backends from python_modules
prune_targets = [
    os.path.join("python_modules", "django", "contrib", "gis"),
    os.path.join("python_modules", "django", "contrib", "postgres"),
    os.path.join("python_modules", "django", "contrib", "oracle"),
]

for target in prune_targets:
    if os.path.exists(target):
        shutil.rmtree(target, ignore_errors=True)
        print(f"✓ Pruned unused bundle bloat: {target}")

# Prune foreign translation directories inside django/conf/locale while preserving __init__.py for LANG_INFO
locale_dir = os.path.join("python_modules", "django", "conf", "locale")
if os.path.exists(locale_dir):
    for entry in os.listdir(locale_dir):
        if entry not in ("__init__.py", "en"):
            entry_path = os.path.join(locale_dir, entry)
            if os.path.isdir(entry_path):
                shutil.rmtree(entry_path, ignore_errors=True)
    print("✓ Pruned foreign locale directories while preserving LANG_INFO.")


# Remove all __pycache__ and .pyc files
for root, dirs, files in os.walk("python_modules", topdown=False):
    for d in dirs:
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d), ignore_errors=True)
print("✓ Cleaned bytecode caches.")

print("=== Step 2.5: Preparing static assets in public/ directory ===")
public_dir = "public"
if os.path.exists(public_dir):
    shutil.rmtree(public_dir, ignore_errors=True)
os.makedirs(public_dir, exist_ok=True)

# 1. Copy static/ to public/static/ so /static/... URLs work
static_dest = os.path.join(public_dir, "static")
shutil.copytree("static", static_dest)

# 2. Also copy top-level static items directly to public/ so /css/..., /js/... root URLs also work
for entry in os.listdir("static"):
    src_entry = os.path.join("static", entry)
    dst_entry = os.path.join(public_dir, entry)
    if os.path.isdir(src_entry):
        shutil.copytree(src_entry, dst_entry)
    else:
        shutil.copy2(src_entry, dst_entry)

print("✓ Successfully prepared static assets in public/ (supporting both /static/... and root paths).")

print("=== Step 3: Deploying optimized Worker to Cloudflare ===")
res = subprocess.run(["npx", "--yes", "wrangler", "deploy"], capture_output=True, text=True)

if res.returncode == 0:
    print("\n==========================================")
    print("=== SUCCESS: Cloudflare Worker Deployed! ===")
    print("==========================================")
    lines = res.stdout.splitlines()
    print("\n".join(lines[-25:]))
    sys.exit(0)
else:
    print(f"\n==========================================")
    print(f"FAILED: wrangler deploy exited with code {res.returncode}")
    print(f"==========================================")
    if res.stderr and res.stderr.strip():
        print("--- STDERR ---")
        print(res.stderr)
    print("--- LAST 40 LINES OF STDOUT ---")
    lines = res.stdout.splitlines()
    print("\n".join(lines[-40:]))
    sys.exit(res.returncode)
