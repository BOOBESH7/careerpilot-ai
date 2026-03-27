// Firebase Auth - shows user info in navbar, NO forced redirects
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getAuth, onAuthStateChanged, signOut }
  from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";

const app = initializeApp({
  apiKey: "AIzaSyAAQ4YStcuTEp4E4qQoA3Sfms4UGyJyjbY",
  authDomain: "resume-analyzer-com.firebaseapp.com",
  projectId: "resume-analyzer-com",
  storageBucket: "resume-analyzer-com.firebasestorage.app",
  messagingSenderId: "1065048610992",
  appId: "1:1065048610992:web:3de45568615994b048c375"
});

const auth = getAuth(app);
window._fbApp  = app;
window._fbAuth = auth;

onAuthStateChanged(auth, user => {
  window._fbUser = user || null;

  const bar      = document.getElementById("user-bar");
  const loginBtn = document.getElementById("nav-login-btn");
  const nameEl   = document.getElementById("user-bar-name");
  const avatar   = document.getElementById("user-bar-avatar");

  if (user) {
    if (bar)      bar.style.display = "flex";
    if (loginBtn) loginBtn.style.display = "none";
    if (nameEl)   nameEl.textContent = user.displayName || user.email.split("@")[0];
    if (avatar && user.photoURL) {
      avatar.src = user.photoURL;
      avatar.style.display = "block";
    }
  } else {
    if (bar)      bar.style.display = "none";
    if (loginBtn) loginBtn.style.display = "flex";
  }
});

window.fbSignOut = async () => {
  await signOut(auth);
  location.reload();
};
