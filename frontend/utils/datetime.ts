const normalizeUtcIso = (value: string): string => {
  // Some runtimes parse "YYYY-MM-DDTHH:mm:ss+00:00" inconsistently.
  // Convert explicit UTC offset to trailing Z for reliable parsing.
  return value.endsWith("+00:00") ? `${value.slice(0, -6)}Z` : value;
};

const toDate = (utcIso: string): Date | null => {
  if (!utcIso) return null;
  const parsed = new Date(normalizeUtcIso(utcIso));
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

export const formatUtcToLocalDateTime = (utcIso: string): string => {
  const parsed = toDate(utcIso);
  if (!parsed) return utcIso || "Unknown";

  return parsed.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
};

export const formatUtcToLocalTime = (utcIso: string): string => {
  const parsed = toDate(utcIso);
  if (!parsed) return utcIso || "Unknown";

  return parsed.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
};
