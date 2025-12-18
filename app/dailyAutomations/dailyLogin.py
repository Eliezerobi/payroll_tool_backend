import os
import sys

# ✅ Get THIS script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ The real project root is TWO folders up:
# payroll-tool-backend/
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

# ✅ Add project root so "app.*" imports work everywhere (shell + cron)
sys.path.insert(0, PROJECT_ROOT)

print("PROJECT_ROOT =", PROJECT_ROOT)
print("sys.path[0] =", sys.path[0])

# ✅ Now imports work:
from app.helloNoteApi.login import hellonote_login

if __name__ == "__main__":
    token = hellonote_login()
    print("✅ Daily Login Finished")
