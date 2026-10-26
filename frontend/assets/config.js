import { runtimeConfig } from "./runtime-config.js";

const BASE_PATH = "/attendance-spaces/";
const CALLBACK_PATH = `${BASE_PATH}auth/callback.html`;

export const publicConfig = Object.freeze({
  basePath: "/attendance-spaces/",
  callbackPath: "/attendance-spaces/auth/callback.html",
  supportedContextKeys: Object.freeze(["space", "invite", "checkpoint"]),
  cognito: Object.freeze({ ...runtimeConfig }),
});

export function urlWithinBase(relativePath = "") {
  const clean = String(relativePath).replace(/^\/+/, "");
  return new URL(clean, new URL(publicConfig.basePath, window.location.origin));
}

export function callbackUrl(origin = window.location.origin) {
  return new URL(publicConfig.callbackPath, origin).toString();
}
