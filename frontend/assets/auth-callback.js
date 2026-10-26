import { publicConfig } from "./config.js";

const status = document.querySelector("#callback-status");
status.textContent = "Autentiseringssvaret kan behandlas när Cognito-integrationen är konfigurerad.";
window.ATTENDANCE_PUBLIC_CONFIG = publicConfig;
