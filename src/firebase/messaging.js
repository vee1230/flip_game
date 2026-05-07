import { getMessaging, getToken, onMessage } from "firebase/messaging";
import { doc, updateDoc } from "firebase/firestore";
import app from "./firebase.js";
import { db } from "./firestore.js";

let messaging = null;

export const requestNotificationPermission = async (uid) => {
  if (!("Notification" in window)) {
    console.log("This browser does not support notifications.");
    return false;
  }
  
  if (Notification.permission === "granted") {
    return await setupFCM(uid);
  }
  
  const permission = await Notification.requestPermission();
  if (permission === "granted") {
    return await setupFCM(uid);
  }
  
  console.log("Notification permission denied");
  return false;
};

const setupFCM = async (uid) => {
  try {
    messaging = getMessaging(app);
    // Remember to replace the VAPID key in the .env file
    const currToken = await getToken(messaging, {
      vapidKey: import.meta.env.VITE_FIREBASE_VAPID_KEY
    });
    
    if (currToken) {
      console.log("FCM Token Generated!");
      // Save token to users collection
      const userRef = doc(db, "users", uid);
      await updateDoc(userRef, {
        fcmToken: currToken
      });
      return true;
    } else {
      console.warn("No registration token available. Request permission to generate one.");
      return false;
    }
  } catch (error) {
    console.error("An error occurred while retrieving token:", error);
    return false;
  }
};

export const onForegroundMessage = (callback) => {
  if (!messaging) return;
  onMessage(messaging, (payload) => {
    callback(payload);
  });
};

export const triggerLocalHighScoreNotification = () => {
    if (Notification.permission === "granted") {
        new Notification("New High Score! \ud83c\udf89", {
            body: "You just beat your personal best!"
        });
    }
};
