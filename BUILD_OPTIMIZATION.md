# Build Speed Optimization

## Current Issue

Builds take 10+ minutes because ESPHome in WSL is accessing files on the Windows filesystem (`/mnt/c/`), which is extremely slow.

## Solutions (Best to Worst)

### 1. **Move Project to WSL Filesystem** (10x faster)

Move the entire project into WSL's native filesystem:

```bash
# In WSL
cd ~
mkdir -p esphome-projects
cp -r /mnt/c/Users/monro/Codex/clawd-pager ~/esphome-projects/
cd ~/esphome-projects/clawd-pager

# Flash from WSL
source ~/esphome-venv/bin/activate
esphome run clawd-pager.yaml
```

**Pros:** Builds in 1-3 minutes instead of 10+  
**Cons:** Files are in WSL, harder to edit from Windows (but VSCode can open WSL folders)

### 2. **Use OTA Updates After First Flash** (Fastest for iterations)

After the first USB flash, use WiFi OTA updates:

```powershell
# From PowerShell (no USB needed)
wsl bash -c "source ~/esphome-venv/bin/activate && esphome run /mnt/c/Users/monro/Codex/clawd-pager/clawd-pager.yaml --device 192.168.50.85"
```

**Pros:** No USB cable, faster upload  
**Cons:** Requires WiFi, device must be running

### 3. **Optimize WSL PATH** (Moderate improvement)

Remove Windows paths from WSL to speed up CMake:

```bash
# In WSL, edit ~/.bashrc
nano ~/.bashrc

# Add at the end:
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Reload
source ~/.bashrc
```

**Pros:** 20-30% faster builds  
**Cons:** Loses access to Windows commands in WSL

### 4. **Use compile-only for testing** (Skip upload)

Test YAML changes without flashing:

```powershell
.\compile.ps1
```

**Pros:** Validates config without waiting for upload  
**Cons:** Still slow, doesn't test on device

## Recommended Workflow

1. **First flash:** Use USB (slow but necessary)
2. **Iterations:** Use OTA updates over WiFi
3. **Major changes:** Move project to WSL filesystem

## Current Build Time

- **USB Flash (Windows filesystem):** ~10-15 minutes
- **OTA Update (WiFi):** ~3-5 minutes
- **WSL Filesystem:** ~1-3 minutes
