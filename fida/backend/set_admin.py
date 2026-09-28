import firebase_admin
from firebase_admin import credentials, auth
from pathlib import Path
import os
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


CREDENTIALS_PATH = os.getenv(
    "FIREBASE_CREDENTIALS_PATH",
    str(BASE_DIR / "serviceAccountKey.json")
)


# ============================================================
# INITIALIZE FIREBASE ADMIN
# ============================================================

if not firebase_admin._apps:

    cred = credentials.Certificate(
        CREDENTIALS_PATH
    )

    firebase_admin.initialize_app(
        cred
    )


# ============================================================
# ENTER ADMIN EMAIL
# ============================================================

ADMIN_EMAIL = "admin@fida.com"


# ============================================================
# FIND USER
# ============================================================

try:

    user = auth.get_user_by_email(
        ADMIN_EMAIL
    )

except Exception as error:

    print()
    print("ERROR: Could not find the Firebase user.")
    print()
    print("Make sure this email exists in:")
    print("Firebase Console → Authentication → Users")
    print()
    print("Error:")
    print(error)

    raise SystemExit(1)


# ============================================================
# SET ADMIN CLAIM
# ============================================================

auth.set_custom_user_claims(
    user.uid,
    {
        "admin": True
    }
)


# ============================================================
# OUTPUT
# ============================================================

print()
print("============================================")
print(" FIDA ADMIN ACCOUNT CONFIGURED")
print("============================================")
print()
print("Email :", user.email)
print("UID   :", user.uid)
print("Admin : True")
print()
print("The account is now an administrator.")
print()
print("IMPORTANT:")
print("Sign out and sign in again after setting")
print("the claim so Firebase obtains a fresh token.")
print()