import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyDyrGBkpc_SgP1LFoxWVwzZJksNMLC0b0Y",
  authDomain: "edu-mind-ai-e778b.firebaseapp.com",
  projectId: "edu-mind-ai-e778b",
  storageBucket: "edu-mind-ai-e778b.firebasestorage.app",
  messagingSenderId: "96143134456",
  appId: "1:96143134456:web:deeb233b7cad2785ddf50d",
  measurementId: "G-JJQ3WXSHLR"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export const googleProvider = new GoogleAuthProvider();
