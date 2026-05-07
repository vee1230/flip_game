# Firestore Security Rules

Para gumana nang maayos ang Leaderboard system sa iyong Memory Match Puzzle lalo na't isinesave nito ang score ng sino man (kasama ang mga "Guest" nang walang login), kailangan nating ayusin ang **Firestore Security Rules** pabor sa setup mo.

Kadalasan, kapag nag-create ka ng bago at empty na Firestore database, naka-lockdown ito by default (`allow read, write: if false;`). Kaya nire-reject ng Firebase ang iyong `saveLeaderboardEntry` hangga't hindi mo ito pinapalitan.

Narito ang rules na gagamitin natin:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // 1. Default Rule: I-block lahat ng reads at writes sa buong database for safety
    match /{document=**} {
      allow read, write: if false;
    }
    
    // 2. Leaderboard: Payagan ang kahit sino na magbasa at mag-save ng bagong leaderboard score
    match /leaderboard/v1/{difficulty}/{documentId} {
      
      // Payagan mabasa ang listahan ng leaderboard
      allow read: if true;
      
      // Payagan makapag-save (create) ng bagong entry score 
      allow create: if true;
      
      // Payagan ang pag-update ng score kung tataas, at pag-delete para matanggal ang lowest score kung sobra na sa 10
      allow update, delete: if true;
    }
    
    // 3. User Personal Collection: Kung saan isasave ang local/personal records ng bawat isa
    match /users/{userId}/records/{documentId} {
      allow read, write: if true;
    }
  }
}
```

### Paano ito i-apply?
1. Pumunta sa iyong [Firebase Console](https://console.firebase.google.com/).
2. Piliin ang iyong database project (hal. `memory-match-db756`).
3. Sa gawing kaliwa, i-click ang **Firestore Database**.
4. Sa main view, may makikita kang mga tab sa itaas (`Data`, `Rules`, `Indexes`, atbp.). I-click ang **Rules** tab.
5. Bubungad doon ang isang code editor. Burahin ang luma mong codes at **i-paste yung Javascript script** snippet na nasa ibabaw.
6. Pindutin ang **"Publish"** button.

Pagkatapos mapa-publish, i-reload ulit ang iyong website/game at susubukan na niyan muling mag-save ng score dahil enabled na ang Write Permission!
