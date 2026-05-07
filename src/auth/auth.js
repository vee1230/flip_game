import { getAuth, signInWithPopup, GoogleAuthProvider, onAuthStateChanged, signOut } from "firebase/auth";
import { doc, getDoc, setDoc, serverTimestamp } from "firebase/firestore";
import app from "../firebase/firebase.js";
import { db } from "../firebase/firestore.js";
import { CONFIG } from '../config.js';

export const auth = getAuth(app);
const provider = new GoogleAuthProvider();

export const loginWithGoogle = async () => {
  try {
    const result = await signInWithPopup(auth, provider);
    const user = result.user;
    
    // Save user info in Firestore users collection
    const userRef = doc(db, "users", user.uid);
    const userDoc = await getDoc(userRef);
    
    if (!userDoc.exists()) {
      await setDoc(userRef, {
        name: user.displayName,
        email: user.email,
        photoURL: user.photoURL,
        highestScore: 0,
        lastScore: 0,
        createdAt: serverTimestamp()
      });
    }

    // Sync with MySQL backend
    try {
      const response = await fetch(`${CONFIG.PYTHON_API}/auth/firebase/sync`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
              uid: user.uid,
              email: user.email,
              name: user.displayName,
              avatar: user.photoURL
          })
      });
      const data = await response.json();
      if (data.success) {
          // Attach backend user data to the firebase user object for the session
          user.backendData = data.user;
      }
    } catch(err) {
      console.error("Backend sync failed:", err);
    }
    
    return user;
  } catch (error) {
    console.error("Login error:", error);
    throw error;
  }
};

export const logoutUser = () => signOut(auth);

export const initAuthListener = (callback) => {
  return onAuthStateChanged(auth, callback);
};
