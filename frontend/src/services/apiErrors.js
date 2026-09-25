const FIELD_LABELS = {
  email: "Email",
  password: "Пароль",
  name: "ФИО",
  channel_id: "Датчик",
  event_at: "Дата события",
};

function validationErrorMessage(error) {
  const field = [...(error.loc || [])].reverse().find((item) => typeof item === "string" && item !== "body");
  const label = FIELD_LABELS[field] || field || "Поле";

  if (error.type === "string_too_short")
    return `${label}: минимум ${error.ctx?.min_length ?? "установленное количество"} символов`;
  if (error.type === "string_too_long")
    return `${label}: максимум ${error.ctx?.max_length ?? "установленное количество"} символов`;
  if (error.type === "value_error" && field === "email")
    return `${label}: укажите корректный адрес`;
  if (error.type === "missing") return `${label}: обязательное поле`;

  return `${label}: ${error.msg || "некорректное значение"}`;
}

export function apiErrorMessage(payload, fallback = "Не удалось выполнить запрос") {
  if (typeof payload === "string" && payload.trim()) return payload;
  if (typeof payload?.detail === "string" && payload.detail.trim()) return payload.detail;
  if (Array.isArray(payload?.detail) && payload.detail.length)
    return payload.detail.map(validationErrorMessage).join("; ");
  if (typeof payload?.message === "string" && payload.message.trim()) return payload.message;
  return fallback;
}
