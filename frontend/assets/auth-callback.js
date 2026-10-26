import { clearSession, completeLogin, restoreContextUrl } from "./auth.js";
import { publicConfig, urlWithinBase } from "./config.js";

const status = document.querySelector("#callback-status");

async function run() {
  try {
    const result = await completeLogin(window.location.search);
    status.textContent = "Inloggningen lyckades. Du skickas tillbaka.";
    history.replaceState(null, "", publicConfig.callbackPath);
    window.location.replace(restoreContextUrl(result.context));
  } catch (error) {
    clearSession();
    history.replaceState(null, "", publicConfig.callbackPath);
    status.textContent = error.message;
    const link = document.querySelector("#callback-home");
    link.href = urlWithinBase();
    link.hidden = false;
  }
}

run();
