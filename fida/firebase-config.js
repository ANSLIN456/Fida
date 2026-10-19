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

    apiKey: "AIzaSyCII5JfYp_5-hik4kpzttFJqgjUECjrQR4",
    authDomain: "fida-ecom-93e0a.firebaseapp.com",
    projectId: "fida-ecom-93e0a",
    storageBucket: "fida-ecom-93e0a.firebasestorage.app",
    messagingSenderId: "204680021448",
    appId: "1:204680021448:web:012b9d10bfa0ff244b2cfd",
    measurementId: "G-XJCJVXBZNK"
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
