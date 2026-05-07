importScripts("https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js");

// We must hardcode or inject the config here because SW does not have access to Vite import.meta.env
// In production, consider injecting these via a build script.
firebase.initializeApp({
  apiKey: "AIzaSyC6vpEw7gHHKrmCR_FxVx-r0PPI4u55c0Y",
  authDomain: "memory-match-db756.firebaseapp.com",
  projectId: "memory-match-db756",
  messagingSenderId: "422084041084",
  appId: "1:422084041084:web:12a5e21ac5195eeb25acf9"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  console.log("[firebase-messaging-sw.js] Received background message ", payload);
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: "/icons/icon-192.png" // Replace with your icon
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});
