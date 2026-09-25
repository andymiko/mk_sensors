import { apiErrorMessage } from "./apiErrors";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export async function downloadReport(dataset, format, params = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") query.set(key, value);
  }
  const response = await fetch(`${API_BASE_URL}/reports/${dataset}/${format}?${query}`, {
    headers: { Authorization: `Bearer ${localStorage.getItem("baseproject_token") || ""}` },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(apiErrorMessage(payload, "Не удалось построить отчёт"));
  }
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";
  const filename = disposition.match(/filename="?([^";]+)"?/)?.[1] || `report.${format}`;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
