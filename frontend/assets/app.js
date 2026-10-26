import { beginLogin, currentSession, logout } from "./auth.js";
import { publicConfig } from "./config.js";
import { describeContext, parseContext } from "./context.js";

const context = parseContext(window.location.search);
const message = document.querySelector("#context-message");
const details = document.querySelector("#context-details");
const loginButton = document.querySelector("#login-button");
const authStatus = document.querySelector("#auth-status");

message.textContent = describeContext(context);
for (const [key, value] of Object.entries(context)) {
  const term = document.createElement("dt");
  term.textContent = key === "space" ? "Närvarorum" : key === "checkpoint" ? "Tillfälle" : "Inbjudan";
  const description = document.createElement("dd");
  description.textContent = value;
  details.append(term, description);
}
details.hidden = Object.keys(context).length === 0;

const session = currentSession();
if (session) {
  authStatus.textContent = session.claims.name || session.claims.email || "Inloggad användare";
  loginButton.textContent = "Logga ut";
  loginButton.addEventListener("click", logout);
} else {
  authStatus.textContent = "Inte inloggad";
  loginButton.addEventListener("click", async () => {
    loginButton.disabled = true;
    try { await beginLogin(window.location.search); }
    catch (error) {
      authStatus.textContent = error.message;
      loginButton.disabled = false;
    }
  });
}

document.querySelector("#primary-action").addEventListener("click", async () => {
  if (session) {
    message.textContent = "Du är inloggad. Nästa leverans ansluter närvarofunktionerna.";
    return;
  }
  await beginLogin(window.location.search).catch((error) => { message.textContent = error.message; });
});

window.ATTENDANCE_PUBLIC_CONFIG = publicConfig;
