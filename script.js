const menuButton = document.querySelector(".menu-toggle");
const menu = document.querySelector("#site-menu");

function closeMenu() {
  if (!menuButton || !menu) return;
  menu.classList.remove("is-open");
  menuButton.setAttribute("aria-expanded", "false");
  menuButton.setAttribute("aria-label", "전체 메뉴 열기");
}

if (menuButton && menu) {
  menuButton.addEventListener("click", () => {
    const isOpen = menu.classList.toggle("is-open");
    menuButton.setAttribute("aria-expanded", String(isOpen));
    menuButton.setAttribute("aria-label", isOpen ? "전체 메뉴 닫기" : "전체 메뉴 열기");
  });

  menu.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMenu));

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });
}

const kakaoChannelUrl = "https://pf.kakao.com/_Kxjtxhn";
document.querySelectorAll(".js-smart-contact").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    const phone = link.dataset.phone;
    const isMobilePhone = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);

    if (isMobilePhone && phone) {
      window.location.href = `tel:${phone}`;
      return;
    }

    window.open(kakaoChannelUrl, "_blank", "noopener,noreferrer");
  });
});

const consultationEntries = document.querySelectorAll(".consultation-entry");
if (consultationEntries.length) {
  fetch("/consult/health/", {
    cache: "no-store",
    headers: { Accept: "application/json" },
  })
    .then((response) => {
      if (!response.ok) return;
      consultationEntries.forEach((entry) => entry.removeAttribute("hidden"));
    })
    .catch(() => {
      // 전화와 카카오 상담은 상담 서버 상태와 관계없이 계속 제공됩니다.
    });
}

document.querySelectorAll(".back-to-top").forEach((button) => {
  button.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
});

const revealItems = document.querySelectorAll(".reveal");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (reduceMotion || !("IntersectionObserver" in window)) {
  revealItems.forEach((item) => item.classList.add("is-visible"));
} else {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.08, rootMargin: "0px 0px -40px" }
  );

  revealItems.forEach((item) => observer.observe(item));
}
