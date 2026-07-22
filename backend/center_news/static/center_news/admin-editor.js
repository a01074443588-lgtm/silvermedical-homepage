(function () {
  "use strict";

  const onReady = (callback) => {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback, { once: true });
    } else {
      callback();
    }
  };

  const escapeHtml = (value) =>
    String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  const renderInline = (value) =>
    escapeHtml(value).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  const renderBody = (value) => {
    const blocks = [];
    let listItems = [];
    const flushList = () => {
      if (!listItems.length) return;
      blocks.push(`<ul>${listItems.map((item) => `<li>${renderInline(item)}</li>`).join("")}</ul>`);
      listItems = [];
    };

    String(value || "")
      .split(/\n\s*\n/)
      .map((block) => block.trim())
      .filter(Boolean)
      .forEach((block) => {
        if (block.startsWith("• ")) {
          listItems.push(block.slice(2).trim());
          return;
        }
        flushList();
        if (block.startsWith("## ")) {
          blocks.push(`<h2>${renderInline(block.slice(3).trim())}</h2>`);
        } else if (block.startsWith("> ")) {
          blocks.push(`<blockquote>${renderInline(block.slice(2).trim())}</blockquote>`);
        } else {
          blocks.push(`<p>${renderInline(block).replaceAll("\n", "<br>")}</p>`);
        }
      });
    flushList();
    return blocks.join("");
  };

  const replaceSelection = (textarea, transform) => {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = textarea.value.slice(start, end);
    const replacement = transform(selected || "내용을 입력하세요");
    textarea.setRangeText(replacement, start, end, "select");
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    textarea.focus();
  };

  onReady(() => {
    const bodyField = document.querySelector("#id_body");
    if (bodyField) {
      const toolbar = document.createElement("div");
      toolbar.className = "center-news-body-tools";
      const tools = [
        ["소제목", (text) => `## ${text}`],
        ["굵게", (text) => `**${text}**`],
        ["목록", (text) => text.split("\n").map((line) => `• ${line}`).join("\n\n")],
        ["인용", (text) => `> ${text}`],
      ];
      tools.forEach(([label, transform]) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = label;
        button.addEventListener("click", () => replaceSelection(bodyField, transform));
        toolbar.append(button);
      });
      bodyField.parentElement.insertBefore(toolbar, bodyField);
    }

    const previewSection = document.querySelector(".center-news-editor-preview");
    const previewFrame = document.querySelector("#center-news-preview-frame");
    if (!previewSection || !previewFrame) return;

    const titleField = document.querySelector("#id_title");
    const summaryField = document.querySelector("#id_summary");
    const coverField = document.querySelector("#id_cover_image");
    const imageAltField = document.querySelector("#id_image_alt");
    const status = previewSection.querySelector("[data-preview-status]");

    const updatePreview = () => {
      const frameDocument = previewFrame.contentDocument;
      if (!frameDocument) return;
      const previewTitle = frameDocument.querySelector(".news-detail-heading h1");
      const previewSummary = frameDocument.querySelector(".news-detail-heading > p");
      const previewBody = frameDocument.querySelector(".news-body");
      const previewCover = frameDocument.querySelector(".news-cover");
      if (previewTitle && titleField) previewTitle.textContent = titleField.value;
      if (previewSummary && summaryField) previewSummary.textContent = summaryField.value;
      if (previewBody && bodyField) previewBody.innerHTML = renderBody(bodyField.value);
      if (previewCover && imageAltField) {
        const description = imageAltField.value || "대표 사진";
        const image = previewCover.querySelector("img");
        const caption = previewCover.querySelector("figcaption");
        if (image) image.alt = description;
        if (caption) caption.textContent = description;
      }
      if (status) status.textContent = "현재 입력 중인 제목·요약·본문을 미리보기에 반영했습니다.";
    };

    previewFrame.addEventListener("load", updatePreview);
    [titleField, summaryField, bodyField, imageAltField].filter(Boolean).forEach((field) => {
      field.addEventListener("input", updatePreview);
    });

    if (coverField) {
      coverField.addEventListener("change", () => {
        const [file] = coverField.files;
        if (!file || !file.type.startsWith("image/")) return;
        const reader = new FileReader();
        reader.addEventListener("load", () => {
          const frameDocument = previewFrame.contentDocument;
          if (!frameDocument) return;
          let figure = frameDocument.querySelector(".news-cover");
          if (!figure) {
            figure = frameDocument.createElement("figure");
            figure.className = "news-cover";
            figure.innerHTML = '<img alt="새 대표 사진 미리보기"><figcaption>새 대표 사진 미리보기</figcaption>';
            frameDocument.querySelector(".news-article")?.prepend(figure);
          }
          const image = figure.querySelector("img");
          if (image) image.src = reader.result;
        });
        reader.readAsDataURL(file);
      });
    }

    previewSection.querySelector("[data-preview-refresh]")?.addEventListener("click", () => {
      if (status) status.textContent = "저장된 완성 화면을 다시 불러오는 중입니다.";
      previewFrame.src = previewSection.dataset.previewUrl;
    });
  });
})();
