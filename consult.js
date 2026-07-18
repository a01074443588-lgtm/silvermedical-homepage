const form = document.querySelector("[data-consult-form]");
const message = document.querySelector("#id_message");
const messageCount = document.querySelector("#message-count");
const messageGuide = document.querySelector("#message-guide");
const messageClientError = document.querySelector("#message-client-error");
const submitButton = document.querySelector("[data-submit-button]");
const errorSummary = document.querySelector("#form-error-summary");

function updateMessageState(showError = false) {
  if (!message || !messageCount) return true;
  const length = message.value.trim().length;
  const isShort = length < 10;
  messageCount.textContent = `${length}자 / 최소 10자`;
  messageGuide?.classList.toggle("is-short", showError && isShort);
  message.closest(".field-row")?.classList.toggle("has-error", showError && isShort);
  if (messageClientError) messageClientError.hidden = !(showError && isShort);
  message.setCustomValidity(showError && isShort ? "상담 내용을 10자 이상 입력해 주세요." : "");
  return !isShort;
}

if (message) {
  updateMessageState(false);
  message.addEventListener("input", () => updateMessageState(message.value.length > 0));
}

document.querySelectorAll(".field-error").forEach((error) => {
  error.closest(".field-row, .privacy-box")?.classList.add("has-error");
});

if (errorSummary) {
  requestAnimationFrame(() => {
    errorSummary.scrollIntoView({ behavior: "smooth", block: "center" });
    errorSummary.focus({ preventScroll: true });
  });
}

form?.addEventListener("submit", (event) => {
  const messageIsValid = updateMessageState(true);
  if (!messageIsValid || !form.checkValidity()) {
    event.preventDefault();
    const invalidField = form.querySelector(":invalid");
    invalidField?.scrollIntoView({ behavior: "smooth", block: "center" });
    invalidField?.focus({ preventScroll: true });
    invalidField?.reportValidity();
    return;
  }

  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = "안전하게 접수하고 있습니다...";
  }
});
