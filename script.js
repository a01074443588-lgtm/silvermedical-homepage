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

const homeNewsGrid = document.querySelector("#homeNewsGrid");
if (homeNewsGrid) {
  fetch("/news/api/latest/", {
    headers: { Accept: "application/json" },
  })
    .then((response) => {
      if (!response.ok) throw new Error("센터소식을 불러오지 못했습니다.");
      return response.json();
    })
    .then(({ posts = [] }) => {
      homeNewsGrid.replaceChildren();
      if (!posts.length) {
        const empty = document.createElement("p");
        empty.className = "home-news-loading";
        empty.textContent = "새로운 센터소식을 준비하고 있습니다.";
        homeNewsGrid.append(empty);
        return;
      }

      posts.forEach((post) => {
        const article = document.createElement("article");
        article.className = "home-news-card";

        const media = document.createElement("a");
        media.className = "home-news-media";
        media.href = post.url;
        media.setAttribute("aria-label", `${post.title} 자세히 보기`);
        if (post.image_url) {
          const image = document.createElement("img");
          image.src = post.image_url;
          image.alt = post.image_alt || "";
          image.loading = "lazy";
          media.append(image);
        } else {
          const placeholder = document.createElement("span");
          placeholder.textContent = post.has_video ? "영상 소식" : post.category;
          media.append(placeholder);
        }

        const body = document.createElement("div");
        body.className = "home-news-body";
        const meta = document.createElement("p");
        meta.className = "home-news-meta";
        meta.textContent = `${post.category} · ${post.published_at.replaceAll("-", ".")}`;
        const title = document.createElement("h3");
        const titleLink = document.createElement("a");
        titleLink.href = post.url;
        titleLink.textContent = post.title;
        title.append(titleLink);
        const summary = document.createElement("p");
        summary.textContent = post.summary;
        body.append(meta, title, summary);
        article.append(media, body);
        homeNewsGrid.append(article);
      });
    })
    .catch(() => {
      homeNewsGrid.replaceChildren();
      const fallback = document.createElement("p");
      fallback.className = "home-news-loading";
      fallback.textContent = "센터소식은 전체보기에서 확인하실 수 있습니다.";
      homeNewsGrid.append(fallback);
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
