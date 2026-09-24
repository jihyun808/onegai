export const API_URL = (
  process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:5001"
).replace(/\/$/, "");

const LEGAL_BASE =
  process.env.EXPO_PUBLIC_LEGAL_BASE_URL ??
  "https://jihyun808.github.io/onegai";

export const TERMS_URL = `${LEGAL_BASE}/terms.html`;
export const PRIVACY_URL = `${LEGAL_BASE}/privacy.html`;

export const CONTACT = "contact.eeez@gmail.com";
