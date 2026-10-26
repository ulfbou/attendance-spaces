import { publicConfig, urlWithinBase } from "./config.js";
import { describeContext, parseContext } from "./context.js";

const context = parseContext(window.location.search);
const message = document.querySelector("#context-message");
const details = document.querySelector("#context-details");
message.textContent = describeContext(context);

for (const [key, value] of Object.entries(context)) {
  const term = document.createElement("dt");
  term.textContent = key === "space" ? "Närvarorum" : key === "checkpoint" ? "Tillfälle" : "Inbjudan";
  const description = document.createElement("dd");
  description.textContent = value;
  details.append(term, description);
}

details.hidden = Object.keys(context).length === 0;

document.querySelector("#primary-action").addEventListener("click", () => {
  message.textContent = "Inloggning och skapande aktiveras i kommande avgränsade leveranser.";
});

document.querySelector("#login-button").addEventListener("click", () => {
  window.location.assign(urlWithinBase("auth/callback.html"));
});

window.ATTENDANCE_PUBLIC_CONFIG = publicConfig;
