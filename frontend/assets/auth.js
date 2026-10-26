import { callbackUrl, publicConfig, urlWithinBase } from "./config.js";
import { parseContext } from "./context.js";

const TRANSACTION_KEY = "attendance.auth.transaction.v1";
const SESSION_KEY = "attendance.auth.session.v1";
const TRANSACTION_MAX_AGE_MS = 10 * 60 * 1000;
const encoder = new TextEncoder();

function base64Url(bytes) {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/u, "");
}

function randomUrlSafe(byteLength = 32) {
  const bytes = new Uint8Array(byteLength);
  crypto.getRandomValues(bytes);
  return base64Url(bytes);
}

export async function createPkce() {
  const verifier = randomUrlSafe(64);
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(verifier));
  return Object.freeze({ verifier, challenge: base64Url(new Uint8Array(digest)) });
}

function cognitoSettings() {
  const { cognito } = publicConfig;
  const required = ["cognitoRegion", "cognitoUserPoolId", "cognitoClientId", "cognitoDomain"];
  const missing = required.filter((key) => !String(cognito[key] || "").trim());
  if (missing.length) throw new Error(`Cognito-konfiguration saknas: ${missing.join(", ")}`);
  const domain = String(cognito.cognitoDomain).trim().replace(/\/+$/u, "");
  const issuer = `https://cognito-idp.${cognito.cognitoRegion}.amazonaws.com/${cognito.cognitoUserPoolId}`;
  return Object.freeze({ ...cognito, domain, issuer });
}

function safeContext(search) {
  return parseContext(search || "");
}

export async function beginLogin(search = window.location.search) {
  const settings = cognitoSettings();
  const { verifier, challenge } = await createPkce();
  const state = randomUrlSafe(32);
  const transaction = {
    state,
    verifier,
    createdAt: Date.now(),
    context: safeContext(search),
  };
  sessionStorage.setItem(TRANSACTION_KEY, JSON.stringify(transaction));
  const authorize = new URL(`${settings.domain}/oauth2/authorize`);
  authorize.search = new URLSearchParams({
    client_id: settings.cognitoClientId,
    response_type: "code",
    scope: "openid email profile",
    redirect_uri: callbackUrl(),
    state,
    code_challenge_method: "S256",
    code_challenge: challenge,
    identity_provider: "Google",
  }).toString();
  window.location.assign(authorize);
}

function readTransaction() {
  const raw = sessionStorage.getItem(TRANSACTION_KEY);
  if (!raw) throw new Error("Ingen pågående inloggning hittades.");
  let transaction;
  try { transaction = JSON.parse(raw); } catch { throw new Error("Inloggningstillståndet är ogiltigt."); }
  if (!transaction || typeof transaction.state !== "string" || typeof transaction.verifier !== "string") {
    throw new Error("Inloggningstillståndet är ofullständigt.");
  }
  if (!Number.isFinite(transaction.createdAt) || Date.now() - transaction.createdAt > TRANSACTION_MAX_AGE_MS) {
    throw new Error("Inloggningen har löpt ut. Försök igen.");
  }
  return transaction;
}

function equalText(left, right) {
  if (typeof left !== "string" || typeof right !== "string" || left.length !== right.length) return false;
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  return difference === 0;
}

function callbackParameters(search) {
  const params = new URLSearchParams(search);
  const oauthError = params.get("error");
  if (oauthError) throw new Error("Inloggningen avbröts eller nekades.");
  const code = params.get("code");
  const state = params.get("state");
  if (!code || !state) throw new Error("Autentiseringssvaret saknar obligatoriska värden.");
  return { code, state };
}

function decodePayload(token) {
  const parts = String(token).split(".");
  if (parts.length !== 3) throw new Error("Identitetstoken är ogiltig.");
  const normalized = parts[1].replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  try { return JSON.parse(atob(padded)); } catch { throw new Error("Identitetstoken kan inte läsas."); }
}

function presentationClaims(idToken, settings) {
  const claims = decodePayload(idToken);
  const audience = claims.aud || claims.client_id;
  if (claims.iss !== settings.issuer || audience !== settings.cognitoClientId || claims.token_use !== "id") {
    throw new Error("Identitetstoken matchar inte den konfigurerade klienten.");
  }
  if (!Number.isFinite(claims.exp) || claims.exp * 1000 <= Date.now()) throw new Error("Identitetstoken har löpt ut.");
  return Object.freeze({ sub: claims.sub || "", email: claims.email || "", name: claims.name || "" });
}

export async function completeLogin(search = window.location.search, fetchImpl = fetch) {
  const settings = cognitoSettings();
  const transaction = readTransaction();
  sessionStorage.removeItem(TRANSACTION_KEY);
  try {
    const { code, state } = callbackParameters(search);
    if (!equalText(state, transaction.state)) throw new Error("Inloggningssvaret matchar inte den påbörjade inloggningen.");
    const response = await fetchImpl(`${settings.domain}/oauth2/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        client_id: settings.cognitoClientId,
        code,
        redirect_uri: callbackUrl(),
        code_verifier: transaction.verifier,
      }),
    });
    if (!response.ok) throw new Error("Kodutbytet misslyckades.");
    const tokens = await response.json();
    if (!tokens.access_token || !tokens.id_token || !Number.isFinite(tokens.expires_in)) {
      throw new Error("Kodutbytet gav ett ofullständigt svar.");
    }
    const session = {
      accessToken: tokens.access_token,
      idToken: tokens.id_token,
      expiresAt: Date.now() + Math.max(0, tokens.expires_in - 30) * 1000,
      claims: presentationClaims(tokens.id_token, settings),
    };
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    return Object.freeze({ session: Object.freeze(session), context: Object.freeze(transaction.context || {}) });
  } catch (error) {
    clearSession();
    throw error;
  }
}

export function currentSession() {
  const raw = sessionStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    const session = JSON.parse(raw);
    if (!Number.isFinite(session.expiresAt) || session.expiresAt <= Date.now()) throw new Error("expired");
    return Object.freeze(session);
  } catch {
    clearSession();
    return null;
  }
}

export function clearSession() {
  sessionStorage.removeItem(TRANSACTION_KEY);
  sessionStorage.removeItem(SESSION_KEY);
}

export function restoreContextUrl(context = {}) {
  const target = urlWithinBase();
  for (const key of publicConfig.supportedContextKeys) {
    if (context[key]) target.searchParams.set(key, context[key]);
  }
  return target;
}

export function logout() {
  let target;
  try {
    const settings = cognitoSettings();
    target = new URL(`${settings.domain}/logout`);
    target.search = new URLSearchParams({
      client_id: settings.cognitoClientId,
      logout_uri: urlWithinBase().toString(),
    }).toString();
  } finally {
    clearSession();
  }
  window.location.assign(target);
}
