// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getFirestore } from "firebase/firestore";
import { getStorage } from "firebase/storage";
import { getAuth } from "firebase/auth";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyAAQ4YStcuTEp4E4qQoA3Sfms4UGyJyjbY",
  authDomain: "resume-analyzer-com.firebaseapp.com",
  projectId: "resume-analyzer-com",
  storageBucket: "resume-analyzer-com.firebasestorage.app",
  messagingSenderId: "1065048610992",
  appId: "1:1065048610992:web:3de45568615994b048c375",
  measurementId: "G-GMMPL75FMR"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const db = getFirestore(app);
const storage = getStorage(app);
const auth = getAuth(app);

export { app, analytics, db, storage, auth };
