// 极简 Markdown -> HTML 渲染器（避免引入 react-markdown 依赖）。
// 支持：标题(#/##/###)、有序/无序列表、加粗 **x**、行内代码 `x`、段落与换行。
// 输入先转义 HTML，避免 XSS。

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function inline(s: string): string {
  return s
    .replace(/`([^`]+)`/g, '<code class="rounded bg-slate-100 px-1">$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

export function renderMarkdown(md: string): string {
  const lines = escapeHtml(md).split("\n");
  const out: string[] = [];
  let inUl = false;
  let inOl = false;

  const closeLists = () => {
    if (inUl) {
      out.push("</ul>");
      inUl = false;
    }
    if (inOl) {
      out.push("</ol>");
      inOl = false;
    }
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      closeLists();
      continue;
    }
    const h = line.match(/^(#{1,3})\s+(.*)$/);
    if (h) {
      closeLists();
      const level = h[1].length;
      out.push(`<h${level} class="font-semibold mt-3 mb-1">${inline(h[2])}</h${level}>`);
      continue;
    }
    const ul = line.match(/^[-*]\s+(.*)$/);
    if (ul) {
      if (!inUl) {
        closeLists();
        out.push('<ul class="list-disc pl-5 space-y-1">');
        inUl = true;
      }
      out.push(`<li>${inline(ul[1])}</li>`);
      continue;
    }
    const ol = line.match(/^\d+\.\s+(.*)$/);
    if (ol) {
      if (!inOl) {
        closeLists();
        out.push('<ol class="list-decimal pl-5 space-y-1">');
        inOl = true;
      }
      out.push(`<li>${inline(ol[1])}</li>`);
      continue;
    }
    closeLists();
    out.push(`<p class="leading-relaxed">${inline(line)}</p>`);
  }
  closeLists();
  return out.join("\n");
}
