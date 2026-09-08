
/**
 * Firebase Configuration — App, Auth, and Firestore initialization.
 * Reads config from VITE_FIREBASE_* environment variables.
 */

import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || 'AIzaSyBxUKXN4kwIfHizLMYMQZ64Pw2PE7CNgJc',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'satqueryai-9bda3.firebaseapp.com',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'satqueryai-9bda3',
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || 'satqueryai-9bda3.firebasestorage.app',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '883648684868',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '1:883648684868:web:a57c383518dca23c1cad11',
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || 'G-MF8FN68WHE',
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export default app;
