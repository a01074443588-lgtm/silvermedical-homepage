const menuButton = document.querySelector(".menu-toggle");
const menu = document.querySelector("#site-menu");

if (menuButton && menu) {
  menuButton.addEventListener("click", () => {
    const isOpen = menu.classList.toggle("is-open");
    menuButton.setAttribute("aria-expanded", String(isOpen));
  });

  menu.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      menu.classList.remove("is-open");
      menuButton.setAttribute("aria-expanded", "false");
    });
  });
}

const smartContactLinks = document.querySelectorAll(".js-smart-contact");
const kakaoChannelUrl = "https://pf.kakao.com/_Kxjtxhn";

smartContactLinks.forEach((link) => {
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
