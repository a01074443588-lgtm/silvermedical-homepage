(() => {
  const root = document.querySelector("[data-notification-console]");
  if (!root) return;

  const result = root.querySelector("[data-action-result]");
  const permissionBadge = root.querySelector("[data-permission-badge]");
  const pushStatus = root.querySelector("[data-push-status]");
  const csrfToken = root.querySelector("input[name='csrfmiddlewaretoken']")?.value || "";

  const setResult = (message, isError = false) => {
    result.textContent = message;
    result.classList.toggle("is-error", isError);
  };

  const postJson = async (url, data) => {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
      body: JSON.stringify(data),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `http_${response.status}`);
    return payload;
  };

  const base64UrlToUint8Array = (value) => {
    const padding = "=".repeat((4 - (value.length % 4)) % 4);
    const base64 = (value + padding).replace(/-/g, "+").replace(/_/g, "/");
    const raw = window.atob(base64);
    return Uint8Array.from([...raw].map((character) => character.charCodeAt(0)));
  };

  const browserLabel = () => {
    const ua = navigator.userAgent;
    if (/Edg\//.test(ua)) return "Microsoft Edge";
    if (/CriOS|Chrome/.test(ua)) return "Google Chrome";
    if (/Safari/.test(ua)) return "Safari";
    return "지원 브라우저";
  };

  const deviceLabel = () => {
    const platform = navigator.userAgentData?.platform || navigator.platform || "기기";
    return `${platform} ${browserLabel()}`.slice(0, 100);
  };

  const supportsPush = () =>
    "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;

  const updatePermissionStatus = () => {
    if (!supportsPush()) {
      permissionBadge.textContent = "지원하지 않음";
      pushStatus.textContent = "사용 불가";
      return;
    }
    const labels = { granted: "허용됨", denied: "차단됨", default: "허용 전" };
    permissionBadge.textContent = labels[Notification.permission] || "확인 필요";
    permissionBadge.classList.toggle("is-active", Notification.permission === "granted");
    pushStatus.textContent = Notification.permission === "granted" ? "사용 가능" : "설정 필요";
  };

  const updateCurrentDeviceStatus = async () => {
    updatePermissionStatus();
    if (!supportsPush() || Notification.permission !== "granted") return;
    const registration = await navigator.serviceWorker.getRegistration("/staff/");
    const subscription = registration ? await registration.pushManager.getSubscription() : null;
    if (subscription) {
      pushStatus.textContent = "이 기기 등록됨";
      permissionBadge.textContent = "허용·등록됨";
      permissionBadge.classList.add("is-active");
    } else {
      pushStatus.textContent = "기기 등록 필요";
    }
  };

  const getRegistration = async () => {
    await navigator.serviceWorker.register("/staff/notification-sw.js", { scope: "/staff/" });
    return navigator.serviceWorker.ready;
  };

  root.querySelector("[data-enable-push]")?.addEventListener("click", async () => {
    try {
      if (!supportsPush()) throw new Error("unsupported_browser");
      const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
      const isStandalone = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone;
      if (isIOS && !isStandalone) throw new Error("ios_home_screen_required");
      const permission = await Notification.requestPermission();
      updatePermissionStatus();
      if (permission !== "granted") throw new Error("notification_permission_denied");
      const configResponse = await fetch(root.dataset.configUrl, { credentials: "same-origin", cache: "no-store" });
      const config = await configResponse.json();
      if (!config.configured || !config.publicKey) throw new Error("push_not_configured");
      const registration = await getRegistration();
      let subscription = await registration.pushManager.getSubscription();
      if (!subscription) {
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: base64UrlToUint8Array(config.publicKey),
        });
      }
      const serialized = subscription.toJSON();
      await postJson(root.dataset.subscribeUrl, {
        ...serialized,
        deviceName: deviceLabel(),
        browser: browserLabel(),
      });
      setResult("이 기기의 상담 알림을 등록했습니다. 시험 알림으로 확인해 주세요.");
      await updateCurrentDeviceStatus();
    } catch (error) {
      const messages = {
        unsupported_browser: "이 브라우저는 웹 푸시를 지원하지 않습니다.",
        ios_home_screen_required: "아이폰은 먼저 홈 화면에 추가한 뒤 설치된 아이콘으로 열어주세요.",
        notification_permission_denied: "알림 권한이 허용되지 않았습니다. 브라우저 설정을 확인해 주세요.",
        push_not_configured: "서버 푸시 키 설정이 아직 완료되지 않았습니다.",
      };
      setResult(messages[error.message] || "알림 기기 등록에 실패했습니다. 잠시 후 다시 시도해 주세요.", true);
    }
  });

  root.querySelector("[data-disable-push]")?.addEventListener("click", async () => {
    try {
      if (!supportsPush()) throw new Error("unsupported_browser");
      const registration = await navigator.serviceWorker.getRegistration("/staff/");
      const subscription = registration ? await registration.pushManager.getSubscription() : null;
      if (!subscription) {
        setResult("현재 브라우저에 등록된 알림이 없습니다.");
        return;
      }
      await postJson(root.dataset.unsubscribeUrl, { endpoint: subscription.endpoint });
      await subscription.unsubscribe();
      setResult("현재 기기의 상담 알림을 해제했습니다.");
      pushStatus.textContent = "해제됨";
    } catch (_error) {
      setResult("현재 기기 알림 해제에 실패했습니다.", true);
    }
  });

  root.querySelector("[data-test-push]")?.addEventListener("click", async () => {
    try {
      await postJson(root.dataset.testUrl, { channel: "web_push" });
      setResult("시험 푸시를 발송 대기열에 등록했습니다. 잠시 후 알림을 확인해 주세요.");
    } catch (error) {
      setResult(error.message === "no_push_device" ? "먼저 이 기기에서 알림 받기를 등록해 주세요." : "시험 푸시 요청에 실패했습니다.", true);
    }
  });

  root.querySelector("[data-test-kakao]")?.addEventListener("click", async () => {
    try {
      await postJson(root.dataset.testUrl, { channel: "kakao" });
      setResult("카카오톡 시험 메시지를 발송 대기열에 등록했습니다.");
    } catch (_error) {
      setResult("카카오톡 연결 상태를 확인해 주세요.", true);
    }
  });

  updateCurrentDeviceStatus().catch(updatePermissionStatus);
})();
