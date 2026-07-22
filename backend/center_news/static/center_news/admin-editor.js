(function () {
  "use strict";

  const onReady = (callback) => {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback, { once: true });
    } else {
      callback();
    }
  };

  const getCsrfToken = () =>
    document.querySelector("input[name='csrfmiddlewaretoken']")?.value || "";

  const normalizedPath = (value) => {
    try {
      return new URL(value, window.location.origin).pathname;
    } catch {
      return value;
    }
  };

  onReady(() => {
    const bodyField = document.querySelector("#id_body");
    const config = document.querySelector("#center-news-editor-config");
    if (!bodyField || !config || !window.Quill) return;

    const Quill = window.Quill;
    const Font = Quill.import("formats/font");
    Font.whitelist = ["serif", "monospace"];
    Quill.register(Font, true);

    const BlockEmbed = Quill.import("blots/block/embed");
    class DividerBlot extends BlockEmbed {}
    DividerBlot.blotName = "divider";
    DividerBlot.tagName = "hr";
    Quill.register(DividerBlot);

    const editorHost = document.createElement("div");
    editorHost.id = "center-news-rich-editor";
    bodyField.insertAdjacentElement("afterend", editorHost);
    bodyField.closest(".form-row")?.classList.add("center-news-rich-editor-row");
    document.body.classList.add("center-news-rich-editor-enabled");

    const quill = new Quill(editorHost, {
      theme: "snow",
      placeholder: "글을 입력하고 사진을 원하는 위치에 추가해 주세요.",
      modules: {
        history: { delay: 500, maxStack: 150, userOnly: true },
        toolbar: {
          container: [
            [{ header: [2, 3, 4, false] }],
            [{ font: [false, "serif", "monospace"] }, { size: ["small", false, "large", "huge"] }],
            ["bold", "italic", "underline", "strike"],
            [{ align: [] }],
            [{ list: "ordered" }, { list: "bullet" }],
            ["blockquote", "link", "image", "divider"],
            ["clean"],
          ],
          handlers: {
            image: () => openImagePicker(),
            divider: () => insertDivider(),
          },
        },
      },
      formats: [
        "align",
        "blockquote",
        "bold",
        "divider",
        "font",
        "header",
        "image",
        "italic",
        "link",
        "list",
        "size",
        "strike",
        "underline",
      ],
    });

    if (bodyField.value.trim()) {
      quill.clipboard.dangerouslyPasteHTML(bodyField.value);
    }

    const editorWrapper = editorHost.closest(".ql-container")?.parentElement || editorHost.parentElement;
    const imageTools = document.createElement("div");
    imageTools.className = "center-news-selected-image-tools";
    imageTools.hidden = true;
    imageTools.innerHTML = [
      '<strong>선택한 사진</strong>',
      '<button type="button" data-image-move="up">위로 이동</button>',
      '<button type="button" data-image-move="down">아래로 이동</button>',
      '<button type="button" data-image-alt>사진 설명</button>',
      '<button type="button" data-image-remove>본문에서 빼기</button>',
    ].join("");
    editorHost.insertAdjacentElement("afterend", imageTools);

    let selectedImage = null;
    const selectImage = (image) => {
      editorHost.querySelectorAll("img.is-selected").forEach((item) => item.classList.remove("is-selected"));
      selectedImage = image;
      if (selectedImage) {
        selectedImage.classList.add("is-selected");
        selectedImage.draggable = true;
      }
      imageTools.hidden = !selectedImage;
    };

    editorHost.addEventListener("click", (event) => {
      selectImage(event.target instanceof HTMLImageElement ? event.target : null);
    });

    const syncBody = () => {
      bodyField.value = quill.root.innerHTML === "<p><br></p>" ? "" : quill.root.innerHTML;
    };
    quill.on("text-change", syncBody);

    const insertImage = (url, alt) => {
      const range = quill.getSelection(true) || { index: Math.max(0, quill.getLength() - 1) };
      quill.insertEmbed(range.index, "image", url, "user");
      const [leaf] = quill.getLeaf(range.index);
      if (leaf?.domNode instanceof HTMLImageElement) {
        leaf.domNode.alt = alt || "센터소식 사진";
        leaf.domNode.loading = "lazy";
      }
      quill.insertText(range.index + 1, "\n", "user");
      quill.setSelection(range.index + 2, 0, "silent");
      syncBody();
    };

    const insertDivider = () => {
      const range = quill.getSelection(true) || { index: Math.max(0, quill.getLength() - 1) };
      quill.insertEmbed(range.index, "divider", true, "user");
      quill.insertText(range.index + 1, "\n", "user");
      quill.setSelection(range.index + 2, 0, "silent");
    };

    const uploadImage = async (file) => {
      const uploadUrl = config.dataset.uploadUrl;
      if (!uploadUrl) {
        throw new Error("먼저 제목·분류·요약을 입력하고 작성 중으로 저장해 주세요.");
      }
      const formData = new FormData();
      formData.append("image", file);
      formData.append("alt", file.name.replace(/\.[^.]+$/, ""));
      const response = await fetch(uploadUrl, {
        method: "POST",
        headers: { "X-CSRFToken": getCsrfToken() },
        body: formData,
        credentials: "same-origin",
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "사진을 올리지 못했습니다.");
      return { ...payload, is_cover: false };
    };

    const openImagePicker = () => {
      if (!config.dataset.uploadUrl) {
        window.alert("먼저 제목·분류·요약을 입력하고 작성 중으로 저장해 주세요.");
        return;
      }
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "image/jpeg,image/png,image/webp";
      input.multiple = true;
      input.addEventListener("change", async () => {
        const files = Array.from(input.files || []);
        if (!files.length) return;
        setEditorStatus(`${files.length}장의 사진을 올리는 중입니다.`);
        try {
          for (const file of files) {
            const asset = await uploadImage(file);
            addAssetCard(asset);
            insertImage(asset.url, asset.alt);
          }
          setEditorStatus(`${files.length}장의 사진을 본문에 추가했습니다.`);
        } catch (error) {
          setEditorStatus(error.message, true);
          window.alert(error.message);
        }
      });
      input.click();
    };

    const moveSelectedImage = (direction) => {
      if (!selectedImage) return;
      const block = selectedImage.closest("p, h2, h3, h4, blockquote");
      if (!block || block.parentElement !== quill.root) {
        setEditorStatus("이 사진은 현재 위치에서 바로 이동할 수 없습니다.", true);
        return;
      }
      const sibling = direction === "up" ? block.previousElementSibling : block.nextElementSibling;
      if (!sibling) return;
      if (direction === "up") {
        quill.root.insertBefore(block, sibling);
      } else {
        quill.root.insertBefore(block, sibling.nextSibling);
      }
      quill.update("user");
      selectImage(selectedImage);
      syncBody();
    };

    imageTools.querySelectorAll("[data-image-move]").forEach((button) => {
      button.addEventListener("click", () => moveSelectedImage(button.dataset.imageMove));
    });
    imageTools.querySelector("[data-image-alt]")?.addEventListener("click", () => {
      if (!selectedImage) return;
      const value = window.prompt("사진 내용을 설명해 주세요.", selectedImage.alt || "");
      if (value !== null && value.trim()) selectedImage.alt = value.trim().slice(0, 160);
      syncBody();
    });
    imageTools.querySelector("[data-image-remove]")?.addEventListener("click", () => {
      if (!selectedImage) return;
      const blot = Quill.find(selectedImage);
      if (blot) quill.deleteText(quill.getIndex(blot), 1, "user");
      selectImage(null);
      syncBody();
    });

    const library = document.querySelector("#center-news-asset-library");
    const status = document.createElement("p");
    status.className = "center-news-editor-status";
    config.querySelector("div")?.append(status);
    const setEditorStatus = (message, isError = false) => {
      status.textContent = message;
      status.classList.toggle("is-error", isError);
    };

    const deleteAsset = async (asset, card) => {
      if (!asset.id || !config.dataset.deleteUrl) return;
      if (!window.confirm("이 사진 파일을 보관함과 본문에서 삭제할까요?")) return;
      const formData = new FormData();
      formData.append("image_id", String(asset.id));
      const response = await fetch(config.dataset.deleteUrl, {
        method: "POST",
        headers: { "X-CSRFToken": getCsrfToken() },
        body: formData,
        credentials: "same-origin",
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "사진을 삭제하지 못했습니다.");
      const deletedPath = normalizedPath(payload.url);
      editorHost.querySelectorAll("img").forEach((image) => {
        if (normalizedPath(image.getAttribute("src")) !== deletedPath) return;
        const blot = Quill.find(image);
        if (blot) quill.deleteText(quill.getIndex(blot), 1, "user");
      });
      card.remove();
      syncBody();
      setEditorStatus("사진 파일을 삭제했습니다.");
    };

    const addAssetCard = (asset) => {
      if (!library) return;
      const card = document.createElement("article");
      card.className = "center-news-asset-card";
      const image = document.createElement("img");
      image.src = asset.url;
      image.alt = asset.alt || "센터소식 사진";
      const label = document.createElement("span");
      label.textContent = asset.is_cover ? "목록 대표사진" : asset.alt || "본문 사진";
      const insertButton = document.createElement("button");
      insertButton.type = "button";
      insertButton.textContent = "본문에 삽입";
      insertButton.addEventListener("click", () => insertImage(asset.url, asset.alt));
      card.append(image, label, insertButton);
      if (asset.id) {
        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "delete-button";
        deleteButton.textContent = "파일 삭제";
        deleteButton.addEventListener("click", async () => {
          try {
            await deleteAsset(asset, card);
          } catch (error) {
            setEditorStatus(error.message, true);
          }
        });
        card.append(deleteButton);
      }
      library.append(card);
    };

    let assets = [];
    try {
      assets = JSON.parse(document.querySelector("#center-news-editor-assets")?.textContent || "[]");
    } catch {
      assets = [];
    }
    assets.forEach(addAssetCard);

    const toolbarLabels = {
      ".ql-image": "사진 추가",
      ".ql-divider": "문단 구분선",
      ".ql-clean": "서식 지우기",
      ".ql-link": "링크",
      ".ql-blockquote": "인용문",
    };
    Object.entries(toolbarLabels).forEach(([selector, label]) => {
      const button = document.querySelector(`.ql-toolbar ${selector}`);
      if (button) {
        button.title = label;
        button.setAttribute("aria-label", label);
      }
    });

    document.querySelector("#post_form")?.addEventListener("submit", syncBody);
    syncBody();
    setEditorStatus(`사진은 최대 ${config.dataset.imageLimit}장까지 보관할 수 있습니다.`);
  });
})();
