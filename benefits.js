const MONEY = new Intl.NumberFormat("ko-KR");

const YEAR = "2026";
const FOOD = {
  meal: 3500,
  snack: 1000
};

const REGULAR_CARE = {
  label: "일반요양",
  hourlyPay: 14000,
  defaultDays: 20
};

const FAMILY_CARE = {
  family60: { label: "가족 60분", hourlyPay: 21000, hours: 1, defaultDays: 20 },
  family90: { label: "가족 90분", hourlyPay: 19000, hours: 1.5, defaultDays: 31 }
};

const DISCOUNTS = {
  facility: [
    { key: "standard", label: "일반", rate: 0.2 },
    { key: "facility40", label: "시설 40% 감경 (12%)", rate: 0.12 },
    { key: "facility60", label: "시설 60% 감경 (8%)", rate: 0.08 },
    { key: "basic", label: "기초수급 (0%)", rate: 0 }
  ],
  home: [
    { key: "standard", label: "일반", rate: 0.15 },
    { key: "home40", label: "재가 40% 감경 (9%)", rate: 0.09 },
    { key: "home60", label: "재가 60% 감경 (6%)", rate: 0.06 },
    { key: "basic", label: "기초수급 (0%)", rate: 0 }
  ]
};

const DATA = {
  homeLimit: { 1: 2512900, 2: 2331200, 3: 1528200, 4: 1409700, 5: 1208900 },
  facility: { 1: 93070, 2: 86340, 3: 81540, 4: 81540, 5: 81540 },
  daycare: {
    "3-6": { 1: 41820, 2: 38720, 3: 35740, 4: 34120, 5: 32490 },
    "6-8": { 1: 56060, 2: 51930, 3: 47940, 4: 46300, 5: 44650 },
    "8-10": { 1: 69730, 2: 64590, 3: 59640, 4: 58010, 5: 56360 },
    "10-13": { 1: 76820, 2: 71160, 3: 65750, 4: 64090, 5: 62460 },
    "13+": { 1: 82370, 2: 76310, 3: 70500, 4: 68860, 5: 67240 }
  },
  visit: { 30: 17450, 60: 25320, 90: 34120, 120: 43430, 150: 50640, 180: 57020, 210: 63530, 240: 70080 }
};

const refs = {
  year: document.querySelector("#year"),
  serviceType: document.querySelector("#serviceType"),
  grade: document.querySelector("#grade"),
  discount: document.querySelector("#discount"),
  timeBand: document.querySelector("#timeBand"),
  visitTime: document.querySelector("#visitTime"),
  days: document.querySelector("#days"),
  daysLabel: document.querySelector("#daysLabel"),
  mealCount: document.querySelector("#mealCount"),
  snackCount: document.querySelector("#snackCount"),
  familyMode: document.querySelector("#familyMode"),
  timeBandWrap: document.querySelector("#timeBandWrap"),
  visitTimeWrap: document.querySelector("#visitTimeWrap"),
  mealCountWrap: document.querySelector("#mealCountWrap"),
  snackCountWrap: document.querySelector("#snackCountWrap"),
  familyModeWrap: document.querySelector("#familyModeWrap"),
  familySection: document.querySelector("#familySection"),
  familyPayCard: document.querySelector("#familyPayCard"),
  totalCost: document.querySelector("#totalCost"),
  resultNote: document.querySelector("#resultNote"),
  careCopay: document.querySelector("#careCopay"),
  careDetail: document.querySelector("#careDetail"),
  foodCost: document.querySelector("#foodCost"),
  foodDetail: document.querySelector("#foodDetail"),
  familyPay: document.querySelector("#familyPay"),
  familyPayDetail: document.querySelector("#familyPayDetail"),
  familyBigPay: document.querySelector("#familyBigPay"),
  selectedCarePayLabel: document.querySelector("#selectedCarePayLabel"),
  regularCarePay: document.querySelector("#regularCarePay"),
  regularCareDetail: document.querySelector("#regularCareDetail"),
  family60Pay: document.querySelector("#family60Pay"),
  family60Detail: document.querySelector("#family60Detail"),
  family90Pay: document.querySelector("#family90Pay"),
  family90Detail: document.querySelector("#family90Detail"),
  comparisonBody: document.querySelector("#comparisonBody"),
  gradeBody: document.querySelector("#gradeBody"),
  discountCol1: document.querySelector("#discountCol1"),
  discountCol2: document.querySelector("#discountCol2"),
  counselMemo: document.querySelector("#counselMemo"),
  printBtn: document.querySelector("#printBtn")
};

function won(value) {
  return `${MONEY.format(Math.round(value))}원`;
}

function rateText(rate) {
  return `${Math.round(rate * 100)}%`;
}

function isHomeService(serviceType) {
  return serviceType === "daycare" || serviceType === "visit";
}

function getDiscounts(serviceType) {
  return serviceType === "facility" ? DISCOUNTS.facility : DISCOUNTS.home;
}

function getSelectedDiscount(serviceType, key = refs.discount.value) {
  return getDiscounts(serviceType).find((item) => item.key === key) || getDiscounts(serviceType)[0];
}

function getUnitRate(serviceType, grade) {
  if (serviceType === "facility") return DATA.facility[grade];
  if (serviceType === "daycare") return DATA.daycare[refs.timeBand.value][grade];
  return DATA.visit[refs.visitTime.value];
}

function getDefaults(serviceType) {
  if (serviceType === "facility") return { days: 30, meals: 3, snacks: 1 };
  if (serviceType === "daycare") return { days: 20, meals: 2, snacks: 1 };
  return { days: 20, meals: 0, snacks: 0 };
}

function syncVisitTimeByGrade() {
  if (refs.serviceType.value !== "visit") return;
  if (refs.familyMode.value === "family60") {
    refs.visitTime.value = "60";
    return;
  }
  if (refs.familyMode.value === "family90") {
    refs.visitTime.value = "90";
    return;
  }
  refs.visitTime.value = Number(refs.grade.value) <= 2 ? "240" : "180";
}

function getRegularCareHours(grade) {
  return Number(grade) <= 2 ? 4 : 3;
}

function getRegularCarePay(grade, days) {
  return REGULAR_CARE.hourlyPay * getRegularCareHours(grade) * days;
}

function getFamilyCarePay(mode, days) {
  const family = FAMILY_CARE[mode];
  return family.hourlyPay * family.hours * days;
}

function calculate({ serviceType, grade, discountKey }) {
  const days = Math.max(0, Number(refs.days.value) || 0);
  const mealCount = Math.max(0, Number(refs.mealCount.value) || 0);
  const snackCount = Math.max(0, Number(refs.snackCount.value) || 0);
  const unitRate = getUnitRate(serviceType, grade);
  const totalBenefit = unitRate * days;
  const discount = getSelectedDiscount(serviceType, discountKey);
  const careCopay = totalBenefit * discount.rate;
  const foodCost = serviceType === "visit" ? 0 : days * (mealCount * FOOD.meal + snackCount * FOOD.snack);
  const total = careCopay + foodCost;
  const limit = DATA.homeLimit[grade];
  const overLimit = isHomeService(serviceType) && totalBenefit > limit;
  const careMode = refs.familyMode.value;
  const selectedCare = careMode === "regular" ? REGULAR_CARE : FAMILY_CARE[careMode];
  const regularCareHours = getRegularCareHours(grade);
  const regularCarePay = getRegularCarePay(grade, days);
  const family60Days = Math.min(days, FAMILY_CARE.family60.defaultDays);
  const family60Pay = getFamilyCarePay("family60", family60Days);
  const family90Pay = getFamilyCarePay("family90", days);
  const selectedCareDays = careMode === "family60" ? family60Days : days;
  const selectedCarePay = serviceType !== "visit"
    ? 0
    : careMode === "regular"
      ? regularCarePay
      : getFamilyCarePay(careMode, selectedCareDays);

  return {
    days,
    mealCount,
    snackCount,
    unitRate,
    totalBenefit,
    discount,
    careCopay,
    foodCost,
    total,
    limit,
    overLimit,
    regularCareHours,
    regularCarePay: serviceType === "visit" ? regularCarePay : 0,
    family60Days,
    selectedCareDays,
    family60Pay: serviceType === "visit" ? family60Pay : 0,
    family90Pay: serviceType === "visit" ? family90Pay : 0,
    familyPay: selectedCarePay,
    familyLabel: selectedCare.label
  };
}

function setServiceDefaults() {
  const defaults = getDefaults(refs.serviceType.value);
  refs.days.value = defaults.days;
  refs.mealCount.value = defaults.meals;
  refs.snackCount.value = defaults.snacks;
}

function updateDiscountOptions() {
  const serviceType = refs.serviceType.value;
  const currentValue = refs.discount.value;
  const options = getDiscounts(serviceType);
  refs.discount.innerHTML = options.map((item) => `<option value="${item.key}">${item.label}</option>`).join("");
  refs.discount.value = options.some((item) => item.key === currentValue) ? currentValue : "standard";
}

function updateVisibility() {
  const serviceType = refs.serviceType.value;
  refs.timeBandWrap.classList.toggle("hidden", serviceType !== "daycare");
  refs.visitTimeWrap.classList.toggle("hidden", serviceType !== "visit");
  refs.mealCountWrap.classList.toggle("hidden", serviceType === "visit");
  refs.snackCountWrap.classList.toggle("hidden", serviceType === "visit");
  refs.familyModeWrap.classList.toggle("hidden", serviceType !== "visit");
  refs.familySection.classList.toggle("hidden", serviceType !== "visit");
  refs.familyPayCard.classList.toggle("hidden", serviceType !== "visit");
  refs.discountCol1.textContent = serviceType === "facility" ? "시설 40% (12%)" : "재가 40% (9%)";
  refs.discountCol2.textContent = serviceType === "facility" ? "시설 60% (8%)" : "재가 60% (6%)";
  refs.daysLabel.textContent = serviceType === "visit" ? "방문횟수" : "월 이용일수";
}

function renderSummary() {
  const serviceType = refs.serviceType.value;
  const grade = refs.grade.value;
  const result = calculate({ serviceType, grade, discountKey: refs.discount.value });
  const serviceName = refs.serviceType.selectedOptions[0].textContent;
  const gradeName = refs.grade.selectedOptions[0].textContent;

  refs.totalCost.textContent = won(result.total);
  refs.careCopay.textContent = won(result.careCopay);
  refs.foodCost.textContent = won(result.foodCost);
  const careLabelMap = {
    regular: "일반요양 예상급여",
    family60: "가족 60분 예상급여",
    family90: "가족 90분 예상급여"
  };
  refs.selectedCarePayLabel.textContent = careLabelMap[refs.familyMode.value];
  refs.familyPay.textContent = won(result.familyPay);
  refs.familyBigPay.textContent = won(result.familyPay);
  refs.regularCarePay.textContent = won(result.regularCarePay);
  refs.family60Pay.textContent = won(result.family60Pay);
  refs.family90Pay.textContent = won(result.family90Pay);
  refs.resultNote.textContent = `${YEAR}년 ${serviceName} ${gradeName}, ${result.discount.label} 기준입니다.`;
  refs.careDetail.textContent = `${won(result.unitRate)} x ${result.days}일 x 본인부담 ${rateText(result.discount.rate)}`;
  refs.foodDetail.textContent = serviceType === "visit"
    ? "방문요양은 식재료비를 계산하지 않습니다."
    : `식사 ${result.mealCount}회, 간식 ${result.snackCount}회 / ${result.days}일`;
  refs.familyPayDetail.textContent = `${result.familyLabel}, ${result.selectedCareDays}회 기준 상담용 예상 금액입니다.`;
  refs.regularCareDetail.textContent = `${won(REGULAR_CARE.hourlyPay)} x ${result.regularCareHours}시간 x ${result.days}회`;
  refs.family60Detail.textContent = `${won(FAMILY_CARE.family60.hourlyPay)} x ${result.family60Days}회 인정`;
  refs.family90Detail.textContent = `${won(FAMILY_CARE.family90.hourlyPay)} x 1.5시간 x ${result.days}회`;

  if (result.overLimit) {
    refs.resultNote.textContent += ` 재가 월 한도액 ${won(result.limit)}을 초과할 수 있어 확인이 필요합니다.`;
  }

  renderComparison(serviceType, grade);
  renderGradeTable(serviceType);
  renderMemo(serviceType, grade, result);
}

function renderComparison(serviceType, grade) {
  refs.comparisonBody.innerHTML = getDiscounts(serviceType).map((discount) => {
    const result = calculate({ serviceType, grade, discountKey: discount.key });
    return `
      <tr>
        <td>${discount.label}</td>
        <td>${rateText(discount.rate)}</td>
        <td>${won(result.careCopay)}</td>
        <td>${won(result.foodCost)}</td>
        <td class="highlight">${won(result.total)}</td>
      </tr>
    `;
  }).join("");
}

function renderGradeTable(serviceType) {
  refs.gradeBody.innerHTML = [1, 2, 3, 4, 5].map((grade) => {
    const cells = getDiscounts(serviceType).map((discount) => {
      const result = calculate({ serviceType, grade, discountKey: discount.key });
      return `<td>${won(result.total)}</td>`;
    }).join("");

    return `
      <tr>
        <td>${grade}등급</td>
        <td>${won(getUnitRate(serviceType, grade))}</td>
        ${cells}
      </tr>
    `;
  }).join("");
}

function renderMemo(serviceType, grade, result) {
  const serviceName = refs.serviceType.selectedOptions[0].textContent;
  const limitMessage = serviceType === "facility"
    ? "시설급여는 1일 수가 기준으로 계산했습니다."
    : `재가급여 월 한도액은 ${won(result.limit)}이며, 한도 초과 여부는 실제 일정 기준으로 확인해야 합니다.`;
  const familyMessage = serviceType === "visit"
    ? `요양보호사 예상급여는 본인부담금과 별도 항목입니다. 일반요양은 ${won(result.regularCarePay)}, 선택 가족요양은 ${won(result.familyPay)} 기준입니다.`
    : "가족요양 예상 급여는 방문요양 선택 시 별도 카드로 표시됩니다.";

  refs.counselMemo.innerHTML = `
    <div class="memo-pill">상담 기준: ${YEAR}년 ${serviceName} ${grade}등급, 월 ${result.days}일 이용 기준입니다.</div>
    <div class="memo-pill">식재료비는 기관 기준인 식사 1끼 ${won(FOOD.meal)}, 간식 1회 ${won(FOOD.snack)}으로 계산했습니다.</div>
    <div class="memo-pill">${limitMessage}</div>
    <div class="memo-pill">${familyMessage}</div>
  `;
}

function bindEvents() {
  refs.serviceType.addEventListener("change", () => {
    setServiceDefaults();
    syncVisitTimeByGrade();
    updateDiscountOptions();
    updateVisibility();
    renderSummary();
  });

  [
    refs.year,
    refs.grade,
    refs.discount,
    refs.timeBand,
    refs.visitTime,
    refs.days,
    refs.mealCount,
    refs.snackCount
  ].forEach((input) => input.addEventListener("input", renderSummary));

  refs.grade.addEventListener("change", () => {
    syncVisitTimeByGrade();
    renderSummary();
  });

  refs.familyMode.addEventListener("change", () => {
    refs.days.value = refs.familyMode.value === "regular"
      ? REGULAR_CARE.defaultDays
      : FAMILY_CARE[refs.familyMode.value].defaultDays;
    syncVisitTimeByGrade();
    renderSummary();
  });

  document.querySelectorAll("[data-preset]").forEach((button) => {
    button.addEventListener("click", () => {
      refs.serviceType.value = button.dataset.preset;
      setServiceDefaults();
      syncVisitTimeByGrade();
      updateDiscountOptions();
      updateVisibility();
      renderSummary();
    });
  });

  refs.printBtn.addEventListener("click", () => window.print());
}

bindEvents();
setServiceDefaults();
syncVisitTimeByGrade();
updateDiscountOptions();
updateVisibility();
renderSummary();
