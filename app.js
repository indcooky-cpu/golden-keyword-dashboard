const PAGE_SIZE = 50;

const state = {
  keywords: [],
  category: "전체",
  search: "",
  sort: "golden_ratio:desc",
  lowOnly: false,
  limit: PAGE_SIZE,
};

const els = {
  updatedAt: document.getElementById("updatedAt"),
  totalCount: document.getElementById("totalCount"),
  filteredInfo: document.getElementById("filteredInfo"),
  bestRatio: document.getElementById("bestRatio"),
  bestKeyword: document.getElementById("bestKeyword"),
  avgSearch: document.getElementById("avgSearch"),
  lowCompCount: document.getElementById("lowCompCount"),
  lowCompRatio: document.getElementById("lowCompRatio"),
  longTailCount: document.getElementById("longTailCount"),
  longTailSub: document.getElementById("longTailSub"),
  categoryTabs: document.getElementById("categoryTabs"),
  lowOnlyBtn: document.getElementById("lowOnlyBtn"),
  searchInput: document.getElementById("searchInput"),
  sortSelect: document.getElementById("sortSelect"),
  tableBody: document.getElementById("keywordTableBody"),
  pager: document.getElementById("pager"),
  pagerInfo: document.getElementById("pagerInfo"),
  moreBtn: document.getElementById("moreBtn"),
};

const LOW_TAIL_MIN = 500;
const LOW_TAIL_MAX = 10000;

function formatNum(num) {
  return Number(num || 0).toLocaleString("ko-KR");
}

function getCompetitionInfo(competition) {
  if (competition === "낮음") {
    return { label: "낮음", cls: "low" };
  }
  if (competition === "높음") {
    return { label: "높음", cls: "high" };
  }
  return { label: "보통", cls: "mid" };
}

function getTrendInfo(trend) {
  if (trend === "상승") return { label: "▲ 상승", cls: "up" };
  if (trend === "하락") return { label: "▼ 하락", cls: "down" };
  if (trend === "신규") return { label: "＋ 신규", cls: "new" };
  return { label: "— 유지", cls: "steady" };
}

function isLongTail(item) {
  const volume = item.monthly_search || 0;
  return volume >= LOW_TAIL_MIN && volume <= LOW_TAIL_MAX;
}

function getFilteredAndSorted() {
  const q = state.search.trim().toLowerCase();
  const filtered = state.keywords.filter((item) => {
    const matchCat = state.category === "전체" || item.category === state.category;
    const haystack = `${item.keyword || ""} ${item.seed || ""}`.toLowerCase();
    const matchSearch = !q || haystack.includes(q);
    const matchLow = !state.lowOnly || item.competition === "낮음";
    return matchCat && matchSearch && matchLow;
  });

  const [key, dir] = state.sort.split(":");
  const sign = dir === "asc" ? 1 : -1;

  filtered.sort((a, b) => {
    if (key === "keyword") {
      return a.keyword.localeCompare(b.keyword, "ko") * sign;
    }
    return ((a[key] || 0) - (b[key] || 0)) * sign;
  });

  return filtered;
}

function updateSummary(list) {
  els.totalCount.textContent = formatNum(list.length);
  els.filteredInfo.textContent =
    state.category === "전체" && !state.search.trim() && !state.lowOnly
      ? "전체 카테고리 기준"
      : `${state.category}${state.lowOnly ? " · 낮음만" : ""} 필터 적용`;

  if (!list.length) {
    els.bestRatio.textContent = "0.00";
    els.bestKeyword.textContent = "-";
    els.avgSearch.textContent = "0";
    els.lowCompCount.textContent = "0";
    els.lowCompRatio.textContent = "낮음 비율 -";
    els.longTailCount.textContent = "0";
    els.longTailSub.textContent = "경쟁 낮음 -";
    return;
  }

  const best = list.reduce((acc, cur) =>
    (cur.golden_ratio || 0) > (acc.golden_ratio || 0) ? cur : acc
  );
  const avg = Math.round(
    list.reduce((sum, item) => sum + (item.monthly_search || 0), 0) / list.length
  );
  const lowList = list.filter((item) => item.competition === "낮음");
  const longTailList = list.filter(isLongTail);
  const lowLongTail = lowList.filter(isLongTail);

  els.bestRatio.textContent = Number(best.golden_ratio || 0).toFixed(2);
  els.bestKeyword.textContent = best.keyword || "-";
  els.avgSearch.textContent = formatNum(avg);
  els.lowCompCount.textContent = formatNum(lowList.length);
  els.lowCompRatio.textContent = `낮음 비율 ${Math.round((lowList.length / list.length) * 100)}%`;
  els.longTailCount.textContent = formatNum(longTailList.length);
  els.longTailSub.textContent = `그중 경쟁 낮음 ${formatNum(lowLongTail.length)}건`;
}

function renderTable(list) {
  if (!list.length) {
    els.tableBody.innerHTML =
      '<tr><td colspan="8" class="empty">조건에 맞는 키워드가 없습니다.</td></tr>';
    return;
  }

  const visible = list.slice(0, state.limit);
  els.tableBody.innerHTML = visible
    .map((item, idx) => {
      const comp = getCompetitionInfo(item.competition);
      const trend = getTrendInfo(item.trend);
      const rankClass = idx < 3 ? "rank-num rank-top" : "rank-num";
      return `
        <tr>
          <td class="${rankClass}">${idx + 1}</td>
          <td><span class="cat-pill">${item.category}</span></td>
          <td class="kw-name">${item.keyword}</td>
          <td class="num">${formatNum(item.monthly_search)}</td>
          <td><span class="badge ${comp.cls}">${comp.label}</span></td>
          <td class="num ratio-val">${Number(item.golden_ratio || 0).toFixed(2)}</td>
          <td><span class="trend ${trend.cls}">${trend.label}</span></td>
          <td class="seed-name">${item.seed || "-"}</td>
        </tr>
      `;
    })
    .join("");
}

function renderPager(total) {
  if (total > state.limit) {
    els.pager.hidden = false;
    els.pagerInfo.textContent = `${formatNum(state.limit)} / ${formatNum(total)}개 표시 중`;
    els.moreBtn.textContent = `더 보기 (${formatNum(total - state.limit)}개)`;
  } else {
    els.pager.hidden = total === 0 ? true : false;
    els.pagerInfo.textContent = total ? `전체 ${formatNum(total)}개 표시 중` : "";
    els.moreBtn.hidden = true;
  }
  if (total > state.limit) {
    els.moreBtn.hidden = false;
  }
}

function render() {
  const list = getFilteredAndSorted();
  updateSummary(list);
  renderTable(list);
  renderPager(list.length);
}

function resetLimit() {
  state.limit = PAGE_SIZE;
}

async function init() {
  try {
    const res = await fetch("data.json", { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.keywords = Array.isArray(data.keywords) ? data.keywords : [];
    els.updatedAt.textContent = data.updated_at || "-";
    render();
  } catch (err) {
    els.tableBody.innerHTML =
      '<tr><td colspan="8" class="empty">data.json을 불러오지 못했습니다. 로컬 서버나 GitHub Pages에서 열어주세요.</td></tr>';
    console.error(err);
  }
}

els.categoryTabs.addEventListener("click", (e) => {
  const btn = e.target.closest(".tab");
  if (!btn) return;
  if (btn.id === "lowOnlyBtn") {
    state.lowOnly = !state.lowOnly;
    btn.classList.toggle("active", state.lowOnly);
    btn.setAttribute("aria-pressed", String(state.lowOnly));
  } else {
    document.querySelectorAll(".tab:not(.filter-tab)").forEach((el) => el.classList.remove("active"));
    btn.classList.add("active");
    state.category = btn.dataset.category;
  }
  resetLimit();
  render();
});

els.searchInput.addEventListener("input", (e) => {
  state.search = e.target.value;
  resetLimit();
  render();
});

els.sortSelect.addEventListener("change", (e) => {
  state.sort = e.target.value;
  resetLimit();
  render();
});

els.moreBtn.addEventListener("click", () => {
  state.limit += PAGE_SIZE;
  render();
});

init();
