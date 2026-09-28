// ============================================================
// FIDA FIREBASE CONFIGURATION
// ============================================================

import { initializeApp } from
    "https://www.gstatic.com/firebasejs/12.0.0/firebase-app.js";

import {
    getAuth
} from
    "https://www.gstatic.com/firebasejs/12.0.0/firebase-auth.js";

import {
    getFirestore
} from
    "https://www.gstatic.com/firebasejs/12.0.0/firebase-firestore.js";


// ============================================================
// FIREBASE CONFIG
// ============================================================

const firebaseConfig = {

    apiKey:
        "AIzaSyCF8QMTGZ7b4mtBOzL6EKg_KAtbwWWMKVA",

    authDomain:
        "fida-ecom.firebaseapp.com",

    projectId:
        "fida-ecom",

    storageBucket:
        "fida-ecom.firebasestorage.app",

    messagingSenderId:
        "956972862913",

    appId:
        "1:956972862913:web:e6c53a16c5a8fd2fb6b340",

    measurementId:
        "G-7Y18DCNCL5"
};


// ============================================================
// INITIALIZE FIREBASE
// ============================================================

const app = initializeApp(firebaseConfig);


// ============================================================
// FIREBASE SERVICES
// ============================================================

export const auth = getAuth(app);

export const db = getFirestore(app);
