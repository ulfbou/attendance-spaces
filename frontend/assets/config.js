export const publicConfig = Object.freeze({
  basePath: "/attendance-spaces/",
  callbackPath: "/attendance-spaces/auth/callback.html",
  supportedContextKeys: Object.freeze(["space", "invite", "checkpoint"]),
});

export function urlWithinBase(relativePath = "") {
  const clean = String(relativePath).replace(/^\/+/, "");
  return new URL(clean, new URL(publicConfig.basePath, window.location.origin));
}
