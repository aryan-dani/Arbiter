"""
Creates a minimal GitHub-ready test repo with intentional Python bugs.
Run this once to create the repo structure, then push it to GitHub.

Usage:
    python create_test_repo.py
    
Then push to GitHub and use that URL when testing the healing agent.
"""
import os
import subprocess
import tempfile
import shutil

REPO_NAME = "rift-test-buggy-repo"
OUTPUT_DIR = os.path.join(os.getcwd(), REPO_NAME)


def create():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # requirements.txt
    with open(os.path.join(OUTPUT_DIR, "requirements.txt"), "w") as f:
        f.write("pytest\n")

    # Buggy source file: calc.py (intentional bugs)
    with open(os.path.join(OUTPUT_DIR, "calc.py"), "w") as f:
        f.write("""# Calculator utility module

def add(a, b):
    return a + b

def subtract(a, b)    # SYNTAX: missing colon
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    return a / b  # LOGIC: does not handle division by zero
""")

    # Test file
    with open(os.path.join(OUTPUT_DIR, "test_calc.py"), "w") as f:
        f.write("""import pytest
from calc import add, subtract, multiply, divide

def test_add():
    assert add(1, 2) == 3

def test_subtract():
    assert subtract(5, 3) == 2

def test_multiply():
    assert multiply(3, 4) == 12

def test_divide():
    assert divide(10, 2) == 5.0

def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(5, 0)
""")

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=OUTPUT_DIR, check=True)
    subprocess.run(["git", "add", "."], cwd=OUTPUT_DIR, check=True)
    subprocess.run(["git", "commit", "-m", "Initial buggy code"], cwd=OUTPUT_DIR, check=True)

    print(f"\n✅ Test repo created at: {OUTPUT_DIR}")
    print("\nNext steps:")
    print("1. Create a new GitHub repo named 'rift-test-buggy-repo' (empty, no README)")
    print("2. Run:")
    print(f"   cd {OUTPUT_DIR}")
    print("   git remote add origin https://github.com/YOUR_USERNAME/rift-test-buggy-repo.git")
    print("   git push -u origin main")
    print("3. Add GITHUB_TOKEN to backend/.env:")
    print("   GITHUB_TOKEN=ghp_yourtokenhere")
    print("4. Test the agent with: https://github.com/YOUR_USERNAME/rift-test-buggy-repo")


if __name__ == "__main__":
    create()
