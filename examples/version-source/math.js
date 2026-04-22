export function sum(values) {
  let total = 0;
  for (let i = 0; i < values.length; i += 1) {
    total += values[i];
  }
  return total;
}

export function isSameUser(left, right) {
  return left.id === right.id;
}

export function normalizeEmail(email) {
  return email.trim().toLowerCase();
}

export function displayName(user) {
  return user.profile?.name ?? "Anonymous";
}

export function firstPage(items, pageSize = 10) {
  return items.slice(0, pageSize);
}

export function sortByScore(players) {
  return [...players].sort((a, b) => a.score - b.score);
}

export function canPublish(post) {
  return post.title && post.body && post.status === "ready";
}

export const timeout = 1000;

export function compact(values) {
  return values.filter(Boolean);
}

export function uniqueTags(tags) {
  return [...new Set(tags)];
}

export function isInternalId(value) {
  return value.startsWith("usr_");
}

export function retryDelay(delay) {
  return delay * 1000;
}

export function ok(body) {
  return { status: 200, body };
}

export function resetCache(cache) {
  cache.clear();
  return cache;
}

export function recordEvent(events, event) {
  events.push(event);
  return events;
}

export function clampScore(score) {
  return Math.min(Math.max(score, 0), 100);
}

export const featureFlags = {
  enabled: true,
  visible: true,
};
