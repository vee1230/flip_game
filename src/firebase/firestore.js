import { getFirestore, collection, doc, setDoc, getDoc, updateDoc, query, orderBy, limit, getDocs, addDoc, serverTimestamp } from "firebase/firestore";
import app from "./firebase.js";

export const db = getFirestore(app);

// Save or upgrade a user's score
export const submitScore = async (uid, scoreData) => {
  try {
    // 1. Add to global scores collection
    const scoresRef = collection(db, "scores");
    await addDoc(scoresRef, {
      uid: uid,
      score: scoreData.score,
      timestamp: serverTimestamp(),
      ...scoreData
    });

    // 2. Update user's personal best
    const userRef = doc(db, "users", uid);
    const userDoc = await getDoc(userRef);
    
    let isNewHighScore = false;
    
    if (userDoc.exists()) {
      const userData = userDoc.data();
      const currentHighest = userData.highestScore || 0;
      
      const updates = { lastScore: scoreData.score };
      
      if (scoreData.score > currentHighest) {
        updates.highestScore = scoreData.score;
        isNewHighScore = true;
      }
      
      await updateDoc(userRef, updates);
    } else {
      // Create user doc if somehow missing
      await setDoc(userRef, {
        highestScore: scoreData.score,
        lastScore: scoreData.score,
        createdAt: serverTimestamp()
      }, { merge: true });
      isNewHighScore = true;
    }
    
    return { success: true, isNewHighScore };
  } catch (error) {
    console.error("Error submitting score:", error);
    return { success: false, error };
  }
};

// Fetch global leaderboard
export const getLeaderboard = async (topN = 10) => {
  try {
    const scoresRef = collection(db, "scores");
    const q = query(scoresRef, orderBy("score", "desc"), limit(topN));
    const querySnapshot = await getDocs(q);
    
    const leaderboard = [];
    querySnapshot.forEach((doc) => {
      leaderboard.push({ id: doc.id, ...doc.data() });
    });
    return leaderboard;
  } catch (error) {
    console.error("Error fetching leaderboard:", error);
    return [];
  }
};

export const getPersonalBest = async (uid) => {
  try {
    const userRef = doc(db, "users", uid);
    const userDoc = await getDoc(userRef);
    if (userDoc.exists()) {
      return userDoc.data().highestScore || 0;
    }
    return 0;
  } catch (error) {
    console.error("Error fetching personal best:", error);
    return 0;
  }
};
