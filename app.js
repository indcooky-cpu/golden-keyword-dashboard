const state = {
  keywords: [],
  category: "전체",
  search: "",
  sort: "golden_ratio:desc",
};

const els = {
  updatedAt: document.getElementById("updatedAt"),
  totalCount: document.getElementById("totalCount"),
  filteredInfo: document.getElementById("filteredInfo"),
  bestRatio: document.getElementById("bestRatio"),
  bestKeyword: document.getElementById("bestKeyword"),
  avgSearch: document.getElementById("avgSearch"),
  lowCompCount: document.getElementById("lowCompCount"),
  categoryTabs: document.getElementById("categoryTabs"),
  searchInput: document.getElementById("searchInput"),
  sortSelect: document.getElementById("sortSelect"),
  tableBody: document.getElementById("keywordTableBody"),
};

function formatNum(num) {
  return Number(num || 0).toLocaleString("ko-KR");
}

function getCompetitionInfo(ratio, competition) {
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
  return { label: "— 유지", cls: "steady" };
}

function getFilteredAndSorted() {
  const q = state.search.trim().toLowerCase();
  const filtered = state.keywords.filter((item) => {
    const matchCat = state.category === "전체" || item.category === state.category;
    const haystack = `${item.keyword || ""} ${item.recommend_keyword || ""}`.toLowerCase();
    const matchSearch = !q || haystack.includes(q);
    return matchCat && matchSearch;
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
    state.category === "전체" && !state.search.trim()
      ? "전체 카테고리 기준"
      : `${state.category} 필터 적용`;

  if (!list.length) {
    els.bestRatio.textContent = "0.00";
    els.bestKeyword.textContent = "-";
    els.avgSearch.textContent = "0";
    els.lowCompCount.textContent = "0";
    return;
  }

  const best = list.reduce((acc, cur) =>
    (cur.golden_ratio || 0) > (acc.golden_ratio || 0) ? cur : acc
  );
  const avg = Math.round(
    list.reduce((sum, item) => sum + (item.monthly_search || 0), 0) / list.length
  );
  const lowCount = list.filter((item) => item.competition === "낮음").length;

  els.bestRatio.textContent = Number(best.golden_ratio || 0).toFixed(2);
  els.bestKeyword.textContent = best.recommend_keyword || best.keyword;
  els.avgSearch.textContent = formatNum(avg);
  els.lowCompCount.textContent = formatNum(lowCount);
}

function renderTable(list) {
  if (!list.length) {
    els.tableBody.innerHTML =
      '<tr><td colspan="9" class="empty">조건에 맞는 키워드가 없습니다.</td></tr>';
    return;
  }

  els.tableBody.innerHTML = list
    .map((item, idx) => {
      const comp = getCompetitionInfo(item.golden_ratio, item.competition);
      const trend = getTrendInfo(item.trend);
      const rankClass = idx < 3 ? "rank-num rank-top" : "rank-num";
      const recommend = item.recommend_keyword || "-";
      return `
        <tr>
          <td class="${rankClass}">${idx + 1}</td>
          <td><span class="cat-pill">${item.category}</span></td>
          <td class="kw-name">${item.keyword}</td>
          <td class="num">${formatNum(item.topic_search)}</td>
          <td class="kw-name">${recommend}</td>
          <td class="num">${formatNum(item.recommend_search)}</td>
          <td class="num ratio-val">${Number(item.golden_ratio || 0).toFixed(2)}</td>
          <td><span class="badge ${comp.cls}">${comp.label}</span></td>
          <td><span class="trend ${trend.cls}">${trend.label}</span></td>
        </tr>
      `;
    })
    .join("");
}

function render() {
  const list = getFilteredAndSorted();
  updateSummary(list);
  renderTable(list);
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
      '<tr><td colspan="9" class="empty">data.json을 불러오지 못했습니다. 로컬 서버나 GitHub Pages에서 열어주세요.</td></tr>';
    console.error(err);
  }
}

els.categoryTabs.addEventListener("click", (e) => {
  const btn = e.target.closest(".tab");
  if (!btn) return;
  document.querySelectorAll(".tab").forEach((el) => el.classList.remove("active"));
  btn.classList.add("active");
  state.category = btn.dataset.category;
  render();
});

els.searchInput.addEventListener("input", (e) => {
  state.search = e.target.value;
  render();
});

els.sortSelect.addEventListener("change", (e) => {
  state.sort = e.target.value;
  render();
});

init();
