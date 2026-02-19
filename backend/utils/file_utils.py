import os
import shutil
import stat
import subprocess

def remove_readonly(func, path, _):
    """Force-delete read-only files on Windows (needed for .git dirs)."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def cleanup_directory(directory_path: str):
    """
    Ensures a directory is completely removed from the system.
    Handles read-only files and root-owned files from Docker.
    """
    if not os.path.exists(directory_path):
        return

    print(f"File Utils: Cleaning up {directory_path}...")

    # Method 1: Standard Python shutil
    try:
        shutil.rmtree(directory_path, onerror=remove_readonly)
    except Exception as e:
        print(f"File Utils: shutil.rmtree failed ({e}), trying subprocess...")

    # Method 2: Platform-specific subprocess (Force kill)
    if os.path.exists(directory_path):
        try:
            if os.name == 'nt':
                # Windows: use rmdir /s /q
                subprocess.run(["rmdir", "/s", "/q", directory_path], shell=True, check=False)
            else:
                # Linux/Docker: use sudo rm -rf
                subprocess.run(["sudo", "rm", "-rf", directory_path], check=False)
            print(f"File Utils: subprocess cleanup attempted.")
        except Exception as rm_err:
            print(f"File Utils: WARNING - Subprocess cleanup failed: {rm_err}")

    # Final Verification
    if os.path.exists(directory_path):
        print(f"CRITICAL: Failed to clean {directory_path}.")
        return False
    
    print(f"File Utils: Cleanup successful.")
    return True
