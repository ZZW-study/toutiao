export function formatPublishTime(value: string | null) {
  if (!value) {
    return "时间待更新";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatViewCount(value: number) {
  if (value >= 10000) {
    return `${(value / 10000).toFixed(1)} 万阅读`;
  }

  return `${value} 阅读`;
}

export function splitParagraphs(content: string) {
  const paragraphs = content
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean);

  return paragraphs.length ? paragraphs : [content];
}
