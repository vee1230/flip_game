# Firebase Leaderboard & Notifications Setup Guide

I have successfully created a modular Firebase setup in your project's `src/` directory to manage authentication, a Firestore leaderboard, and Cloud Messaging (FCM). 

Here is a comprehensive guide to understanding, configuring, and running your newly architected app.

## 1. Environment & Vite Setup

Since you'll be using environment variables to keep your API keys secure instead of hardcoding them, it is highly recommended to use a bundler like **Vite**.

1. **Initialize Vite**: Run the following in your terminal:
   ```bash
   npm init -y
   npm install vite --save-dev
   npm install firebase dotenv
   ```
2. **Setup package.json Scripts**:
   Update your `package.json` to include Vite scripts:
   ```json
   "scripts": {
     "dev": "vite",
     "build": "vite build",
     "preview": "vite preview"
   }
   ```
3. **Using Env Variables**: 
   Inside Vite, you can access your `.env` variables securely via `import.meta.env.VITE_VARIABLE_NAME`. See `src/firebase.js` for an example.
4. **Gitignore**:
   Ensure that your `.env` file is hidden from Git. Create a `.gitignore` file and add:
   ```text
   node_modules/
   .env
   dist/
   ```

## 2. Firebase Console Setup

### Get your VAPID Key for Push Notifications
1. Go to the [Firebase Console](https://console.firebase.google.com/).
2. Select your project (`memory-match-db756`).
3. Navigate to **Project Settings** (the gear icon) > **Cloud Messaging**.
4. Scroll down to the **Web configuration** section.
5. Under **Web Push certificates**, click **Generate key pair**.
6. Copy the newly generated key pair.
7. Paste this key into your local `.env` file as `VITE_FIREBASE_VAPID_KEY=YourKeyHere`.

### Set up Firestore Database Rules
Make sure you initialize Firestore in the Firebase Console and configure the rules so only authenticated users can write scores.
```text
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId} {
      allow read: if true;
      allow write: if request.auth != null && request.auth.uid == userId;
    }
    match /scores/{scoreId} {
      allow read: if true;
      allow create: if request.auth != null;
    }
  }
}
```

## 3. Integrating with `index.html`

Currently, your `index.html` relies on Firebase's App Compat CDN versions. With Vite and ES Modules, you must link your modular JS script as a `type="module"`.

**Remove the old CDNs at the end of `index.html`:**
```html
<!-- REMOVE THESE LINES -->
<!-- <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js"></script> -->
<!-- <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-auth-compat.js"></script> -->
```

**Inject your module instead:**
```html
<script type="module">
  import { initGameFirebase } from './src/game.js';
  
  // Call initialization logic when the page loads
  document.addEventListener('DOMContentLoaded', () => {
      initGameFirebase();
  });
</script>
```

Feel free to bind your specific HTML buttons (like the `login-btn`, `logout-btn`, and your game-over triggers) to the functions within `src/game.js`!

## 4. Service Worker Details
The `firebase-messaging-sw.js` script handles **background notifications** (when the user is not actively viewing the game tab). 
* Due to limitations in Service Workers, Vite environment variables (`import.meta.env`) cannot be read automatically. In `firebase-messaging-sw.js`, you must either leave your keys hardcoded or use a build step plugin to replace variables dynamically on compile.
* Foreground notifications (when the game tab is active) are handled natively in `src/messaging.js`, which then triggers a Javascript alert or desktop notification alert.
