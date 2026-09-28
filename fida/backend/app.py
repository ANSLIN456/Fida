import os
import time
import uuid
import shutil
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Form,
    Header,
    Depends
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

import firebase_admin
from firebase_admin import credentials, firestore, auth


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

FIREBASE_CREDENTIALS_PATH = os.getenv(
    "FIREBASE_CREDENTIALS_PATH",
    str(BASE_DIR / "serviceAccountKey.json")
)

UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FIREBASE
# ============================================================

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="FIDA E-Commerce Backend",
    version="1.0.0",
    description="Backend for FIDA E-Commerce Website"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def current_time():
    return int(time.time() * 1000)


def calculate_stock_status(quantity, total):

    if quantity <= 0:
        return "Out of Stock"

    if total > 0 and quantity <= total / 3:
        return "Limited Time Offer"

    return "In Stock"


def convert_document(document):

    data = document.to_dict() or {}
    data["id"] = document.id

    return data

# ============================================================
# FIREBASE AUTHENTICATION
# ============================================================

def verify_firebase_token(
    authorization: str
):

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail="Authorization header is required."
        )


    if not authorization.startswith(
        "Bearer "
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header."
        )


    token = authorization.split(
        "Bearer ",
        1
    )[1].strip()


    if not token:

        raise HTTPException(
            status_code=401,
            detail="Firebase ID token is missing."
        )


    try:

        decoded_token = auth.verify_id_token(
            token
        )

        return decoded_token

    except Exception:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired Firebase token."
        )


# ============================================================
# ADMIN AUTHENTICATION
# ============================================================

def require_admin(
    authorization: str = Header(...)
):
    decoded_token = verify_firebase_token(
        authorization
    )

    if decoded_token.get("admin") is not True:
        raise HTTPException(
            status_code=403,
            detail="Administrator access required."
        )

    return decoded_token


# ============================================================
# DATA MODELS
# ============================================================

class EnquiryCreate(BaseModel):

    fullName: str = Field(min_length=1, max_length=120)

    email: Optional[EmailStr] = None

    phone: str = Field(
        min_length=3,
        max_length=30
    )

    country: str = Field(
        min_length=1,
        max_length=80
    )

    category: Optional[str] = "Other"

    product: Optional[str] = ""

    message: str = Field(
        min_length=1,
        max_length=5000
    )


class ContactCreate(BaseModel):

    fullName: str = Field(
        min_length=1,
        max_length=120
    )

    email: Optional[EmailStr] = None

    phone: str = Field(
        min_length=3,
        max_length=30
    )

    country: str = Field(
        min_length=1,
        max_length=80
    )

    subject: str = Field(
        min_length=1,
        max_length=200
    )

    message: str = Field(
        min_length=1,
        max_length=5000
    )


class UserLog(BaseModel):

    email: str

    role: Optional[str] = "user"


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "status": "online",
        "message": "FIDA Backend API is running",
        "database": "Firebase Firestore",
        "documentation": "/docs"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():

    try:

        db.collection("products").limit(1).stream()

        return {
            "status": "healthy",
            "firebase": "connected"
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Firebase connection failed: {str(e)}"
        )


# ============================================================
# PRODUCTS
# ============================================================

@app.get("/api/products")
def get_products(category: Optional[str] = None):

    products_ref = db.collection("products")

    if category and category.lower() != "all":

        documents = products_ref.where(
            "category",
            "==",
            category
        ).stream()

        products = [
            convert_document(doc)
            for doc in documents
        ]

        products.sort(
            key=lambda x: x.get("createdAt", 0),
            reverse=True
        )

    else:

        try:

            documents = products_ref.order_by(
                "createdAt",
                direction=firestore.Query.DESCENDING
            ).stream()

            products = [
                convert_document(doc)
                for doc in documents
            ]

        except Exception:

            documents = products_ref.stream()

            products = [
                convert_document(doc)
                for doc in documents
            ]

            products.sort(
                key=lambda x: x.get("createdAt", 0),
                reverse=True
            )

    for product in products:

        quantity = int(
            product.get("quantity", 0)
        )

        total = int(
            product.get("total", 0)
        )

        product["status"] = calculate_stock_status(
            quantity,
            total
        )

    return products


# ============================================================
# CREATE PRODUCT
# ============================================================

@app.post("/api/products")
async def create_product(
    name: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    quantity: int = Form(...),
    total: int = Form(...),
    packSizes: str = Form(...),
    image: UploadFile = File(...),
    authorization: str = Header(default="")
):
    require_admin(
        authorization
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if quantity < 0:

        raise HTTPException(
            status_code=400,
            detail="Quantity cannot be negative."
        )

    if total < 1:

        raise HTTPException(
            status_code=400,
            detail="Total capacity must be at least 1."
        )

    if quantity > total:

        raise HTTPException(
            status_code=400,
            detail="Available quantity cannot exceed total capacity."
        )

    if not name.strip():

        raise HTTPException(
            status_code=400,
            detail="Product name is required."
        )

    if not category.strip():

        raise HTTPException(
            status_code=400,
            detail="Product category is required."
        )

    if not description.strip():

        raise HTTPException(
            status_code=400,
            detail="Product description is required."
        )


    # --------------------------------------------------------
    # IMAGE VALIDATION
    # --------------------------------------------------------

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif"
    }

    if image.content_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, WEBP and GIF images are allowed."
        )


    # --------------------------------------------------------
    # SAVE IMAGE
    # --------------------------------------------------------

    extension = Path(
        image.filename or "image.jpg"
    ).suffix.lower()

    if not extension:

        extension = ".jpg"

    filename = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    file_path = UPLOAD_DIR / filename

    try:

        with file_path.open("wb") as buffer:

            shutil.copyfileobj(
                image.file,
                buffer
            )

    finally:

        await image.close()


    # --------------------------------------------------------
    # PACK SIZES
    # --------------------------------------------------------

    parsed_sizes = [
        size.strip()
        for size in packSizes.split(",")
        if size.strip()
    ]

    if not parsed_sizes:

        raise HTTPException(
            status_code=400,
            detail="At least one pack size is required."
        )


    # --------------------------------------------------------
    # IMAGE URL
    # --------------------------------------------------------

    image_url = (
        "http://127.0.0.1:8000"
        f"/static/uploads/{filename}"
    )


    # --------------------------------------------------------
    # FIRESTORE DATA
    # --------------------------------------------------------

    product_data = {

        "name": name.strip(),

        "category": category.strip(),

        "description": description.strip(),

        "quantity": quantity,

        "total": total,

        "packSizes": parsed_sizes,

        "image": image_url,

        "createdAt": current_time()
    }


    # --------------------------------------------------------
    # SAVE TO FIRESTORE
    # --------------------------------------------------------

    _, document_reference = (
        db.collection("products")
        .add(product_data)
    )

    product_data["id"] = document_reference.id

    product_data["status"] = calculate_stock_status(
        quantity,
        total
    )


    return product_data


# ============================================================
# DELETE PRODUCT
# ============================================================

@app.delete("/api/products/{product_id}")
def delete_product(
    product_id: str,
    authorization: str = Header(default="")
):

    require_admin(
        authorization
    )

    # keep your existing delete logic here

    document_reference = (
        db.collection("products")
        .document(product_id)
    )

    snapshot = document_reference.get()

    if not snapshot.exists:

        raise HTTPException(
            status_code=404,
            detail="Product not found."
        )


    product_data = snapshot.to_dict() or {}

    document_reference.delete()


    # --------------------------------------------------------
    # DELETE LOCAL IMAGE
    # --------------------------------------------------------

    image_url = product_data.get(
        "image",
        ""
    )

    prefix = (
        "http://127.0.0.1:8000"
        "/static/uploads/"
    )

    if image_url.startswith(prefix):

        filename = image_url[len(prefix):]

        filename = Path(filename).name

        image_path = UPLOAD_DIR / filename

        if image_path.exists():

            image_path.unlink()


    return {
        "message": "Product deleted successfully."
    }


# ============================================================
# ENQUIRIES
# ============================================================

@app.post("/api/enquiries")
def submit_enquiry(
    enquiry: EnquiryCreate
):

    data = enquiry.model_dump()

    data["submittedAt"] = current_time()

    _, document_reference = (
        db.collection("enquiries")
        .add(data)
    )

    return {

        "id": document_reference.id,

        "message": "Enquiry submitted successfully."
    }


# ============================================================
# GET ENQUIRIES
# ============================================================

@app.get("/api/enquiries")
def get_enquiries(
    authorization: str = Header(default="")
):

    require_admin(
        authorization
    )

    documents = (
        db.collection("enquiries")
        .order_by(
            "submittedAt",
            direction=firestore.Query.DESCENDING
        )
        .stream()
    )

    return [
        convert_document(doc)
        for doc in documents
    ]


# ============================================================
# DELETE ENQUIRY
# ============================================================

@app.delete("/api/enquiries/{enquiry_id}")
def delete_enquiry(
    enquiry_id: str,
    authorization: str = Header(default="")
):

    require_admin(
        authorization
    )

    document_reference = (
        db.collection("enquiries")
        .document(enquiry_id)
    )

    snapshot = document_reference.get()

    if not snapshot.exists:

        raise HTTPException(
            status_code=404,
            detail="Enquiry not found."
        )

    document_reference.delete()

    return {
        "message":
            "Enquiry deleted successfully."
    }


# ============================================================
# CONTACT
# ============================================================

@app.post("/api/contact")
def submit_contact(
    contact: ContactCreate
):

    data = contact.model_dump()

    data["submittedAt"] = current_time()

    _, document_reference = (
        db.collection("contacts")
        .add(data)
    )

    return {

        "id": document_reference.id,

        "message": "Message received successfully."
    }


# ============================================================
# USER LOGIN LOG
# ============================================================

@app.post("/api/users/log")
def log_user(user: UserLog):

    data = user.model_dump()

    data["loggedInAt"] = current_time()

    _, document_reference = (
        db.collection("user_logs")
        .add(data)
    )

    return {
        "id": document_reference.id
    }


# ============================================================
# GET USER LOGS
# ============================================================

@app.get("/api/users/log")
def get_user_logs():

    documents = (
        db.collection("user_logs")
        .order_by(
            "loggedInAt",
            direction=firestore.Query.DESCENDING
        )
        .stream()
    )

    return [
        convert_document(doc)
        for doc in documents
    ]

# =========================================================
# PROMOTION BANNER SETTINGS
# =========================================================

@app.get("/api/site-settings/promotion")
async def get_promotion_settings(
    user=Depends(require_admin)
):

    try:

        doc = (
            db.collection("site_settings")
            .document("promotion")
            .get()
        )

        if doc.exists:

            return doc.to_dict()

        return {
            "discount": 40,
            "target": "All Women's Wear",
            "message": "Limited Time!",
            "enabled": True
        }

    except Exception as error:

        print(
            "Promotion settings error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail="Could not load promotion settings."
        )

@app.put("/api/site-settings/promotion")
async def update_promotion_settings(
    settings: dict,
    user=Depends(require_admin)
):

    try:

        discount = int(
            settings.get("discount", 40)
        )

        target = str(
            settings.get(
                "target",
                "All Women's Wear"
            )
        ).strip()

        message = str(
            settings.get(
                "message",
                "Limited Time!"
            )
        ).strip()

        enabled = bool(
            settings.get(
                "enabled",
                True
            )
        )


        if discount < 0 or discount > 100:

            raise HTTPException(
                status_code=400,
                detail="Discount must be between 0 and 100."
            )


        if not target:

            raise HTTPException(
                status_code=400,
                detail="Offer target cannot be empty."
            )


        if not message:

            raise HTTPException(
                status_code=400,
                detail="Offer message cannot be empty."
            )


        data = {

            "discount":
                discount,

            "target":
                target,

            "message":
                message,

            "enabled":
                enabled

        }


        (
            db.collection("site_settings")
            .document("promotion")
            .set(data)
        )


        return {

            "success":
                True,

            "message":
                "Promotion banner updated.",

            **data

        }


    except HTTPException:

        raise

    except Exception as error:

        print(
            "Update promotion error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail="Could not update promotion banner."
        )
# ============================================================
# ADMIN DASHBOARD STATISTICS
# ============================================================

@app.get("/api/admin/dashboard-stats")
def get_dashboard_stats(
    authorization: str = Header(default="")
):

    require_admin(
        authorization
    )

    product_documents = (
        db.collection("products")
        .stream()
    )

    products = [
        doc.to_dict()
        for doc in product_documents
    ]


    enquiry_documents = (
        db.collection("enquiries")
        .stream()
    )

    enquiries_count = len(
        list(enquiry_documents)
    )


    user_documents = (
        db.collection("user_logs")
        .stream()
    )

    users_count = len(
        list(user_documents)
    )


    in_stock = 0
    limited = 0
    out_of_stock = 0


    for product in products:

        quantity = int(
            product.get(
                "quantity",
                0
            )
        )

        total = int(
            product.get(
                "total",
                0
            )
        )

        status = calculate_stock_status(
            quantity,
            total
        )


        if status == "In Stock":

            in_stock += 1

        elif status == "Limited Time Offer":

            limited += 1

        else:

            out_of_stock += 1


    return {

        "totalLogins":
            users_count,

        "totalEnquiries":
            enquiries_count,

        "totalProducts":
            len(products),

        "stockBreakdown": {

            "inStock":
                in_stock,

            "limited":
                limited,

            "outOfStock":
                out_of_stock
        }
    }

# ============================================================
# PROMOTION / OFFER BANNER
# ============================================================

class OfferUpdate(BaseModel):
    discount: int
    category: str


# ------------------------------------------------------------
# GET CURRENT PROMOTION
# Used by the public website
# ------------------------------------------------------------

@app.get("/api/offer")
def get_offer():

    try:

        doc = (
            db.collection("settings")
            .document("offer")
            .get()
        )

        if doc.exists:

            data = doc.to_dict() or {}

            return {
                "discount": data.get("discount", 40),
                "category": data.get(
                    "category",
                    "All Women's Wear"
                )
            }

        # Default promotion
        return {
            "discount": 40,
            "category": "All Women's Wear"
        }

    except Exception as e:

        print("Get offer error:", e)

        raise HTTPException(
            status_code=500,
            detail="Could not load promotion."
        )


# ------------------------------------------------------------
# UPDATE PROMOTION
# Used by ADMIN PANEL
# ------------------------------------------------------------

@app.put("/api/admin/offer")
def update_offer(
    offer: OfferUpdate,
    user=Depends(require_admin)
):

    # Validate discount
    if offer.discount < 0 or offer.discount > 100:

        raise HTTPException(
            status_code=400,
            detail="Discount must be between 0 and 100."
        )


    # Validate category
    category = offer.category.strip()

    if not category:

        raise HTTPException(
            status_code=400,
            detail="Promotion category cannot be empty."
        )


    try:

        # Save to Firebase Firestore
        db.collection("settings").document("offer").set(
            {
                "discount": offer.discount,
                "category": category
            },
            merge=True
        )


        return {
            "success": True,
            "message": "Promotion updated successfully.",
            "discount": offer.discount,
            "category": category
        }


    except Exception as e:

        print("Update offer error:", e)

        raise HTTPException(
            status_code=500,
            detail="Could not update promotion."
        )