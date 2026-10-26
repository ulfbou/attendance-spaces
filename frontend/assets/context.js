const patterns = Object.freeze({
  space: /^spc_[A-Za-z0-9_-]{16,64}$/,
  checkpoint: /^cp_[A-Za-z0-9_-]{16,64}$/,
  invite: /^inv_[A-Za-z0-9_-]{32,128}$/,
});

export function parseContext(search) {
  const params = new URLSearchParams(search);
  const context = {};
  for (const [key, pattern] of Object.entries(patterns)) {
    const value = params.get(key);
    if (value !== null && pattern.test(value)) context[key] = value;
  }
  return Object.freeze(context);
}

export function describeContext(context) {
  if (context.invite) return "En inbjudan är redo att behandlas efter inloggning.";
  if (context.space && context.checkpoint) return "Ett närvarotillfälle har valts.";
  if (context.space) return "Ett närvarorum har valts.";
  return "Ingen närvarokontext har valts.";
}
