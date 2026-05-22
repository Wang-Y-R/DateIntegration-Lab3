export const apiBaseUrl = import.meta.env.VITE_API_BASE || "http://localhost:8083";

export const requestJson = async (path, options = {}) => {
  const res = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers
    },
    ...options
  });
  const body = await res.json();
  return body;
};
