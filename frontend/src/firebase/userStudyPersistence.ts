import {
  addDoc,
  collection,
  doc,
  getDocs,
  increment,
  orderBy,
  query,
  serverTimestamp,
  setDoc,
  type Firestore,
} from "firebase/firestore";
import { getAuth, signInAnonymously, type Auth, type User } from "firebase/auth";
import type { TelemetryEvent } from "../ai/hybridInference";

export function buildDocumentSlug(docName: string): string {
  const cleaned = docName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return cleaned || "untitled-document";
}

export async function requireAuthenticatedUser(
  auth: Auth = getAuth(),
  allowAnonymousFallback = true
): Promise<User> {
  if (auth.currentUser) {
    return auth.currentUser;
  }
  if (allowAnonymousFallback) {
    const cred = await signInAnonymously(auth);
    return cred.user;
  }
  throw new Error("User must be signed in before saving study data.");
}

function userSummariesCol(db: Firestore, uid: string) {
  return collection(db, "users", uid, "studySummaries");
}

function userTelemetryCol(db: Firestore, uid: string, docId: string) {
  return collection(db, "users", uid, "studySummaries", docId, "telemetryEvents");
}

export async function saveUserStudySummary(
  db: Firestore,
  params: {
    uid: string;
    documentName: string;
    documentChars: number;
    question: string;
    summaryText: string;
    telemetry: TelemetryEvent[];
  }
): Promise<string> {
  const docId = buildDocumentSlug(params.documentName);
  const docRef = doc(userSummariesCol(db, params.uid), docId);

  const onDeviceCount = params.telemetry.filter((t) => t.actualSource === "ON_DEVICE").length;
  const inCloudCount = params.telemetry.filter((t) => t.actualSource === "IN_CLOUD").length;
  const totalLatencyMs = params.telemetry.reduce((sum, t) => sum + t.latencyMs, 0);

  await setDoc(
    docRef,
    {
      ownerUid: params.uid,
      documentName: params.documentName,
      documentChars: params.documentChars,
      question: params.question,
      summaryText: params.summaryText,
      lastOnDeviceCount: onDeviceCount,
      lastInCloudCount: inCloudCount,
      lastRunLatencyMs: totalLatencyMs,
      totalOnDeviceCalls: increment(onDeviceCount),
      totalInCloudCalls: increment(inCloudCount),
      updatedAt: serverTimestamp(),
    },
    { merge: true }
  );

  const eventsCol = userTelemetryCol(db, params.uid, docId);
  for (const ev of params.telemetry) {
    await addDoc(eventsCol, {
      ...ev,
      ownerUid: params.uid,
      documentName: params.documentName,
      recordedAt: serverTimestamp(),
    });
  }

  return docId;
}

export async function loadUserTelemetryHistory(
  db: Firestore,
  uid: string,
  docName: string,
  limitCount = 25
): Promise<TelemetryEvent[]> {
  const docId = buildDocumentSlug(docName);
  const q = query(userTelemetryCol(db, uid, docId), orderBy("timestamp", "asc"));
  const snap = await getDocs(q);

  return snap.docs.slice(-limitCount).map((d) => {
    const data = d.data() as TelemetryEvent;
    return {
      id: d.id,
      timestamp: data.timestamp ?? new Date().toISOString(),
      taskType: data.taskType ?? "short_prompt",
      requestedMode: data.requestedMode ?? "PREFER_ON_DEVICE",
      actualSource: data.actualSource ?? "IN_CLOUD",
      latencyMs: Number(data.latencyMs ?? 0),
      inputChars: Number(data.inputChars ?? 0),
      outputChars: Number(data.outputChars ?? 0),
      fallbackOccurred: Boolean(data.fallbackOccurred),
    };
  });
}
