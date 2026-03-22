(() => {
  let sessionId = null;
  let heartbeatTimer = null;
  let sessionClosed = false;
  let stalePollTimer = null;
  let stalePollInFlight = false;

  let cachedBets = [];
  let currentRenderedBets = [];

  let activeStatusFilter = "all";
  let activeLeagueFilter = "all";
  let activeGameFilter = "all";
  let activeBetTypeFilter = "all";

  const STALE_POLL_INTERVAL_MS = 5000;

  const elements = {
    metricGames: document.getElementById("metric-games"),
    metricBets: document.getElementById("metric-bets"),
    metricProb: document.getElementById("metric-prob"),
    metricOdd: document.getElementById("metric-odd"),
    generatedMeta: document.getElementById("generated-meta"),
    scoresMeta: document.getElementById("scores-meta"),
    statusMessage: document.getElementById("status-message"),
    statusSelect: document.getElementById("status-filter"),
    leagueSelect: document.getElementById("league-filter"),
    gameSelect: document.getElementById("game-filter"),
    betTypeSelect: document.getElementById("bet-type-filter"),
    betsTableBody: document.getElementById("bets-table-body"),
  };

  function toNumber(value, fallback = 0) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function avg(values) {
    if (!values.length) return 0;
    const total = values.reduce((sum, item) => sum + toNumber(item, 0), 0);
    return total / values.length;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll("\"", "&quot;")
      .replaceAll("'", "&#39;");
  }

  function dateStamp(dateValue) {
    const year = dateValue.getFullYear();
    const month = String(dateValue.getMonth() + 1).padStart(2, "0");
    const day = String(dateValue.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function formatDateTime(value) {
    if (!value) return "--";
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return "--";
    return dt.toLocaleString("pt-BR");
  }

  function formatKickoff(value) {
    if (!value) return "-";
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return "-";
    return dt.toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function isPayloadFromToday(payload) {
    if (!payload?.generated_at) return false;
    const generated = new Date(payload.generated_at);
    if (Number.isNaN(generated.getTime())) return false;
    return dateStamp(generated) === dateStamp(new Date());
  }

  function setStatusMessage(message, type = "info") {
    if (!elements.statusMessage) return;
    const text = String(message || "");
    elements.statusMessage.textContent = text;
    elements.statusMessage.classList.remove("status-message-info", "status-message-error");
    if (!text) return;
    elements.statusMessage.classList.add(type === "error" ? "status-message-error" : "status-message-info");
  }

  function redirectToLogin(message = "Sua sessão expirou. Entre novamente.") {
    stopStalePolling();
    sessionClosed = true;
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
    const query = new URLSearchParams({ erro: String(message || "") });
    window.location.href = `/login?${query.toString()}`;
  }

  async function ensureAuthenticatedResponse(response) {
    if (response.redirected && String(response.url || "").includes("/login")) {
      redirectToLogin();
      return null;
    }

    if (response.status === 401) {
      let detail = "Sua sessão expirou. Entre novamente.";
      try {
        const payload = await response.json();
        if (payload?.detail) {
          detail = String(payload.detail);
        }
      } catch (_error) {
        detail = "Sua sessão expirou. Entre novamente.";
      }
      redirectToLogin(detail);
      return null;
    }

    return response;
  }

  function uniqueGameCount(bets) {
    return new Set((bets || []).map((bet) => getBetGameKey(bet))).size;
  }

  function getMatchTeams(bet) {
    const home = String(bet?.home_team || "").trim();
    const away = String(bet?.away_team || "").trim();
    if (home && away) return { home, away };

    const parts = String(bet?.jogo || "")
      .split(/\s+vs\s+/i)
      .map((item) => item.trim())
      .filter(Boolean);

    if (parts.length >= 2) {
      return { home: parts[0], away: parts[1] };
    }
    return { home: String(bet?.jogo || "-").trim() || "-", away: "-" };
  }

  function getBetGameKey(bet) {
    const fixtureId = bet?.fixture_id;
    if (fixtureId !== undefined && fixtureId !== null && String(fixtureId).trim() !== "") {
      return `id:${fixtureId}`;
    }
    return `game:${String(bet?.jogo || "").trim().toLowerCase()}`;
  }

  function getBetGameLabel(bet) {
    const teams = getMatchTeams(bet);
    return `${teams.home} vs ${teams.away}`;
  }

  function getSortedBets(bets) {
    return [...(bets || [])].sort((a, b) => {
      const probDiff = toNumber(b.probability) - toNumber(a.probability);
      if (probDiff !== 0) return probDiff;
      return toNumber(b.ev) - toNumber(a.ev);
    });
  }

  function getStatusInfo(bet) {
    const short = String(bet?.status_short || "").toUpperCase().trim();
    if (["NS", "TBD", "PST"].includes(short)) {
      return { key: "upcoming", label: "Não iniciado", css: "status-upcoming" };
    }
    if (["FT", "AET", "PEN"].includes(short)) {
      return { key: "finished", label: "Encerrado", css: "status-finished" };
    }
    if (short) {
      return { key: "live", label: "Em andamento", css: "status-live" };
    }

    const kickoff = new Date(bet?.kickoff);
    if (!Number.isNaN(kickoff.getTime()) && kickoff > new Date()) {
      return { key: "upcoming", label: "Não iniciado", css: "status-upcoming" };
    }
    return { key: "finished", label: "Encerrado", css: "status-finished" };
  }

  function parseGoal(value) {
    if (value === null || value === undefined || value === "") return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function normalizeText(value) {
    return String(value || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function formatFinalScore(bet) {
    const homeGoals = parseGoal(bet?.home_goals);
    const awayGoals = parseGoal(bet?.away_goals);
    if (homeGoals === null || awayGoals === null) return "-";
    return `${homeGoals} x ${awayGoals}`;
  }

  function scoreLabel(value) {
    const goal = parseGoal(value);
    return goal === null ? "-" : String(goal);
  }

  function resolveMarketResult(bet, homeGoals, awayGoals) {
    const market = normalizeText(bet?.tipo_aposta || "");
    const total = homeGoals + awayGoals;

    if (market.startsWith("over 0.5")) return total >= 1;
    if (market.startsWith("over 1.5")) return total >= 2;
    if (market.startsWith("over 2.5")) return total >= 3;
    if (market.startsWith("over 3.5")) return total >= 4;
    if (market.startsWith("under 2.5")) return total <= 2;
    if (market.startsWith("under 3.5")) return total <= 3;

    if (market.includes("ambos marcam")) {
      const bothScore = homeGoals > 0 && awayGoals > 0;
      if (market.includes("nao")) return !bothScore;
      return bothScore;
    }

    if (market.includes("dupla chance 1x")) return homeGoals >= awayGoals;
    if (market.includes("dupla chance x2")) return awayGoals >= homeGoals;
    if (market.includes("dupla chance 12")) return homeGoals !== awayGoals;

    if ((market.includes("vitoria") && market.includes("casa")) || market === "home_win") {
      return homeGoals > awayGoals;
    }
    if (market.includes("empate") || market === "draw") {
      return homeGoals === awayGoals;
    }
    if ((market.includes("vitoria") && market.includes("visitante")) || market === "away_win") {
      return awayGoals > homeGoals;
    }

    return null;
  }

  function getResultInfo(bet, statusInfo) {
    if (statusInfo.key === "live") {
      const score = formatFinalScore(bet);
      return {
        dotClass: "dot-live",
        label: score !== "-" ? "Placar ao vivo" : "Jogo ao vivo",
        score,
      };
    }

    if (statusInfo.key !== "finished") {
      return { dotClass: "dot-gray", label: "Aguardando resultado", score: "-" };
    }

    const homeGoals = parseGoal(bet?.home_goals);
    const awayGoals = parseGoal(bet?.away_goals);
    if (homeGoals === null || awayGoals === null) {
      return { dotClass: "dot-gray", label: "Aguardando resultado", score: "-" };
    }

    const won = resolveMarketResult(bet, homeGoals, awayGoals);
    if (won === true) {
      return { dotClass: "dot-green", label: "Deu bom", score: formatFinalScore(bet) };
    }
    if (won === false) {
      return { dotClass: "dot-red", label: "Deu ruim", score: formatFinalScore(bet) };
    }
    return { dotClass: "dot-gray", label: "Sem avaliação", score: formatFinalScore(bet) };
  }

  function renderMatchMainLine(bet, statusInfo) {
    const teams = getMatchTeams(bet);
    const homeScore = scoreLabel(bet?.home_goals);
    const awayScore = scoreLabel(bet?.away_goals);
    const showScore = statusInfo.key === "live" || statusInfo.key === "finished";
    const scoreMarkup = showScore
      ? `
        <span class="score-chip">${escapeHtml(homeScore)}</span>
        <span class="vs-chip">vs</span>
        <span class="score-chip">${escapeHtml(awayScore)}</span>
      `
      : '<span class="vs-chip">vs</span>';

    return `
      <div class="match-main-line">
        <span class="team-wrap team-wrap-home">
          ${renderTeamLogo(teams.home, bet?.home_team_logo)}
          <span class="team-name" title="${escapeHtml(teams.home)}">${escapeHtml(teams.home)}</span>
        </span>
        ${scoreMarkup}
        <span class="team-wrap team-wrap-away">
          <span class="team-name" title="${escapeHtml(teams.away)}">${escapeHtml(teams.away)}</span>
          ${renderTeamLogo(teams.away, bet?.away_team_logo)}
        </span>
      </div>
    `;
  }

  function normalizeLeague(value) {
    return String(value || "").trim();
  }

  function normalizeBetType(value) {
    return String(value || "").trim();
  }

  function toFriendlyBetTypeLabel(type) {
    const normalized = normalizeBetType(type);
    if (!normalized) return "-";

    const lower = normalized.toLowerCase();
    const overMatch = lower.match(/^over\s*([0-9]+(?:[.,][0-9]+)?)\s*gols?$/);
    if (overMatch) {
      return `Mais de ${String(overMatch[1]).replace(",", ".")} gols`;
    }

    const underMatch = lower.match(/^under\s*([0-9]+(?:[.,][0-9]+)?)\s*gols?$/);
    if (underMatch) {
      return `Menos de ${String(underMatch[1]).replace(",", ".")} gols`;
    }

    return normalized;
  }

  function evClassName(evValue) {
    const ev = toNumber(evValue, 0);
    if (ev > 0.03) return "ev-positive";
    if (ev >= 0) return "ev-neutral";
    return "ev-negative";
  }

  function evBorderClass(evValue) {
    const ev = toNumber(evValue, 0);
    if (ev < 0) return "ev-border-negative";
    if (ev <= 0.03) return "ev-border-mid";
    return "";
  }

  function evDisplay(evValue) {
    const ev = toNumber(evValue, 0);
    return `${ev >= 0 ? "+" : ""}${ev.toFixed(3)}`;
  }

  function probabilityBadge(probability) {
    const pct = Math.max(0, Math.min(100, toNumber(probability) * 100));
    if (pct >= 80) {
      return '<span class="prob-badge prob-badge-high">Alta</span>';
    }
    if (pct >= 70) {
      return '<span class="prob-badge prob-badge-mid">Boa</span>';
    }
    return "";
  }

  function getBestBookmakers(bet) {
    if (!Array.isArray(bet?.best_bookmakers)) return [];
    return bet.best_bookmakers
      .filter((item) => item && String(item.name || "").trim())
      .slice(0, 3);
  }

  function renderBestBookmakers(bet) {
    const houses = getBestBookmakers(bet);
    if (!houses.length) {
      return '<div class="bookmakers-column"><span class="bookmakers-empty">Sem casas destacadas</span></div>';
    }

    const labels = houses
      .map((item) => {
        const name = escapeHtml(String(item.name || ""));
        const odd = toNumber(item.odd, 0);
        const label = odd > 0 ? odd.toFixed(2) : "-";
        const url = String(item.url || "").trim();
        const logoUrl = safeLogoUrl(item.logo_url);
        const initials = escapeHtml(getInitials(item.name || ""));
        const content = `
          <span class="bookmaker-brand">
            ${
              logoUrl
                ? `
                  <img
                    class="bookmaker-logo"
                    src="${logoUrl}"
                    alt="${name}"
                    loading="lazy"
                    referrerpolicy="no-referrer"
                    onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-flex';"
                  />
                  <span class="bookmaker-logo bookmaker-logo-fallback" style="display:none;" aria-hidden="true">${initials}</span>
                `
                : `<span class="bookmaker-logo bookmaker-logo-fallback" aria-hidden="true">${initials}</span>`
            }
            <span class="bookmaker-name">${name}</span>
          </span>
          <span class="bookmaker-odd">${escapeHtml(label)}</span>
        `;
        if (/^https?:\/\//i.test(url)) {
          return `<a class="bookmaker-chip bookmaker-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${content}</a>`;
        }
        return `<span class="bookmaker-chip">${content}</span>`;
      })
      .join("");
    return `<div class="bookmakers-column">${labels}</div>`;
  }

  function renderMarketMeta(bet) {
    return "";
  }

  function safeLogoUrl(value) {
    const raw = String(value || "").trim();
    if (!raw) return "";
    if (!/^https?:\/\//i.test(raw)) return "";
    return raw;
  }

  function getInitials(name) {
    const words = String(name || "")
      .trim()
      .split(/\s+/)
      .filter(Boolean);
    if (!words.length) return "?";
    if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
    return `${words[0][0] || ""}${words[1][0] || ""}`.toUpperCase();
  }

  function renderTeamLogo(name, logoUrl) {
    const safeName = escapeHtml(name || "-");
    const safeLogo = safeLogoUrl(logoUrl);
    const initials = escapeHtml(getInitials(name));

    if (safeLogo) {
      return `
        <span class="logo-wrap">
          <img
            class="team-logo"
            src="${safeLogo}"
            alt="${safeName}"
            loading="lazy"
            referrerpolicy="no-referrer"
            onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-flex';"
          />
          <span class="team-logo logo-fallback" style="display:none;" aria-hidden="true">${initials}</span>
        </span>
      `;
    }

    return `<span class="team-logo logo-fallback" aria-hidden="true">${initials}</span>`;
  }

  function renderLeagueLogo(name, logoUrl) {
    const safeName = escapeHtml(name || "Liga");
    const safeLogo = safeLogoUrl(logoUrl);

    if (safeLogo) {
      return `
        <span class="logo-wrap">
          <img
            class="league-logo"
            src="${safeLogo}"
            alt="${safeName}"
            loading="lazy"
            referrerpolicy="no-referrer"
            onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-flex';"
          />
          <span class="league-logo logo-fallback" style="display:none;" aria-hidden="true">🏆</span>
        </span>
      `;
    }

    return '<span class="league-logo logo-fallback" aria-hidden="true">🏆</span>';
  }

  function matchesStatusFilter(statusInfo) {
    if (activeStatusFilter === "all") return true;
    return statusInfo.key === activeStatusFilter;
  }

  function matchesLeagueFilter(bet) {
    if (activeLeagueFilter === "all") return true;
    return normalizeLeague(bet?.liga) === activeLeagueFilter;
  }

  function matchesGameFilter(bet) {
    if (activeGameFilter === "all") return true;
    return getBetGameKey(bet) === activeGameFilter;
  }

  function matchesBetTypeFilter(bet) {
    if (activeBetTypeFilter === "all") return true;
    return normalizeBetType(bet?.tipo_aposta) === activeBetTypeFilter;
  }

  function getStatusFilteredBets(bets) {
    return getSortedBets(bets).filter((bet) => matchesStatusFilter(getStatusInfo(bet)));
  }

  function getStatusTypeFilteredBets(bets) {
    return getStatusFilteredBets(bets).filter((bet) => matchesBetTypeFilter(bet));
  }

  function getStatusTypeLeagueFilteredBets(bets) {
    return getStatusTypeFilteredBets(bets).filter((bet) => matchesLeagueFilter(bet));
  }

  function getFilteredBets(bets) {
    return getStatusTypeLeagueFilteredBets(bets).filter((bet) => matchesGameFilter(bet));
  }

  function updateStatusOptions(bets) {
    const select = elements.statusSelect;
    if (!(select instanceof HTMLSelectElement)) return;

    const counts = { all: bets.length, upcoming: 0, live: 0, finished: 0 };
    for (const bet of bets) {
      const key = getStatusInfo(bet).key;
      if (counts[key] !== undefined) counts[key] += 1;
    }

    const labels = {
      all: "Todos",
      upcoming: "Não iniciados",
      live: "Em andamento",
      finished: "Encerrados",
    };

    const options = [
      { value: "all", label: `${labels.all} (${counts.all})` },
      { value: "upcoming", label: `${labels.upcoming} (${counts.upcoming})` },
      { value: "live", label: `${labels.live} (${counts.live})` },
      { value: "finished", label: `${labels.finished} (${counts.finished})` },
    ];

    if (!options.some((option) => option.value === activeStatusFilter)) {
      activeStatusFilter = "all";
    }

    select.innerHTML = options
      .map((option) => `<option value="${option.value}">${escapeHtml(option.label)}</option>`)
      .join("");
    select.value = activeStatusFilter;
  }

  function updateBetTypeOptions(bets) {
    const select = elements.betTypeSelect;
    if (!(select instanceof HTMLSelectElement)) return;

    const base = getStatusFilteredBets(bets);
    const counts = new Map();

    for (const bet of base) {
      const type = normalizeBetType(bet?.tipo_aposta);
      if (!type) continue;
      counts.set(type, (counts.get(type) || 0) + 1);
    }

    const options = [
      { value: "all", label: `Todos os tipos (${base.length})` },
      ...[...counts.entries()]
        .sort((a, b) => a[0].localeCompare(b[0], "pt-BR"))
        .map(([type, count]) => ({
          value: type,
          label: `${toFriendlyBetTypeLabel(type)} (${count})`,
        })),
    ];

    if (!options.some((option) => option.value === activeBetTypeFilter)) {
      activeBetTypeFilter = "all";
    }

    select.innerHTML = options
      .map((option) => `<option value="${escapeHtml(option.value)}">${escapeHtml(option.label)}</option>`)
      .join("");
    select.value = activeBetTypeFilter;
  }

  function updateLeagueOptions(bets) {
    const select = elements.leagueSelect;
    if (!(select instanceof HTMLSelectElement)) return;

    const base = getStatusTypeFilteredBets(bets);
    const counts = new Map();

    for (const bet of base) {
      const league = normalizeLeague(bet?.liga);
      if (!league) continue;
      counts.set(league, (counts.get(league) || 0) + 1);
    }

    const options = [
      { value: "all", label: `Todas as ligas (${base.length})` },
      ...[...counts.entries()]
        .sort((a, b) => a[0].localeCompare(b[0], "pt-BR"))
        .map(([league, count]) => ({ value: league, label: `${league} (${count})` })),
    ];

    if (!options.some((option) => option.value === activeLeagueFilter)) {
      activeLeagueFilter = "all";
    }

    select.innerHTML = options
      .map((option) => `<option value="${escapeHtml(option.value)}">${escapeHtml(option.label)}</option>`)
      .join("");
    select.value = activeLeagueFilter;
  }

  function updateGameOptions(bets) {
    const select = elements.gameSelect;
    if (!(select instanceof HTMLSelectElement)) return;

    const base = getStatusTypeLeagueFilteredBets(bets);
    const grouped = new Map();

    for (const bet of base) {
      const key = getBetGameKey(bet);
      const label = getBetGameLabel(bet);
      if (!grouped.has(key)) grouped.set(key, { label, count: 0 });
      grouped.get(key).count += 1;
    }

    const options = [
      { value: "all", label: `Todos os jogos (${grouped.size})` },
      ...[...grouped.entries()]
        .map(([value, item]) => ({ value, label: `${item.label} (${item.count})` }))
        .sort((a, b) => a.label.localeCompare(b.label, "pt-BR")),
    ];

    if (!options.some((option) => option.value === activeGameFilter)) {
      activeGameFilter = "all";
    }

    select.innerHTML = options
      .map((option) => `<option value="${escapeHtml(option.value)}">${escapeHtml(option.label)}</option>`)
      .join("");
    select.value = activeGameFilter;
  }

  function renderMeta(payload) {
    if (elements.generatedMeta) {
      elements.generatedMeta.textContent = `Gerado em: ${formatDateTime(payload?.generated_at)}`;
    }
    if (elements.scoresMeta) {
      elements.scoresMeta.textContent = `Última atualização de placares: ${formatDateTime(payload?.scores_updated_at)}`;
    }
  }

  function renderMetrics(payload, bets) {
    const games = toNumber(payload?.total_games_analyzed, uniqueGameCount(bets));
    const betCount = toNumber(payload?.total_bets, bets.length);
    const avgProb = avg((bets || []).map((bet) => bet?.probability)) * 100;
    const avgOdd = avg((bets || []).map((bet) => bet?.odd));

    if (elements.metricGames) elements.metricGames.textContent = games.toLocaleString("pt-BR");
    if (elements.metricBets) elements.metricBets.textContent = betCount.toLocaleString("pt-BR");
    if (elements.metricProb) elements.metricProb.textContent = `${avgProb.toFixed(2)}%`;
    if (elements.metricOdd) elements.metricOdd.textContent = avgOdd.toFixed(2);
  }

  function renderBetsTable(bets) {
    const tbody = elements.betsTableBody;
    if (!(tbody instanceof HTMLElement)) return;

    const filtered = getFilteredBets(bets);
    currentRenderedBets = filtered;

    if (!filtered.length) {
      tbody.innerHTML = '<tr><td class="empty-state-cell" colspan="6">Nenhuma aposta para o filtro selecionado.</td></tr>';
      return;
    }

    const rows = filtered.map((bet, index) => {
      const teams = getMatchTeams(bet);
      const league = normalizeLeague(bet?.liga) || "-";
      const market = toFriendlyBetTypeLabel(bet?.tipo_aposta || "-");
      const probability = Math.max(0, Math.min(100, toNumber(bet?.probability) * 100));
      const ev = toNumber(bet?.ev, 0);
      const evClass = evClassName(ev);
      const borderClass = evBorderClass(ev);
      const status = getStatusInfo(bet);
      const kickoff = formatKickoff(bet?.kickoff);
      const resultInfo = getResultInfo(bet, status);
      const statusDotClass = resultInfo.dotClass || "dot-gray";

      return `
        <tr class="bet-row bet-row-${status.key} ${borderClass}" data-rec-index="${index}">
          <td class="match-cell">
            ${renderMatchMainLine(bet, status)}
            <div class="kickoff-line">
              <span>${escapeHtml(kickoff)}</span>
              <span class="status-inline">
                <span class="result-dot ${statusDotClass}"></span>
                <span class="status-pill ${status.css}">${escapeHtml(status.label)}</span>
              </span>
            </div>
          </td>

          <td>
            <div class="league-cell">
              ${renderLeagueLogo(league, bet?.league_logo)}
              <span class="league-name">${escapeHtml(league)}</span>
            </div>
          </td>

          <td>
            <div class="market-stack">
              <span class="market-pill">${escapeHtml(market)}</span>
              ${renderMarketMeta(bet)}
            </div>
          </td>

          <td class="prob-cell">
            <div class="prob-top">
              <span class="prob-value">${probability.toFixed(1)}%</span>
              ${probabilityBadge(probability / 100)}
            </div>
            <div class="prob-track"><div class="prob-fill" style="width:${probability.toFixed(1)}%"></div></div>
          </td>
          <td>
            <div class="ev-stack">
              <span class="ev-pill ${evClass}">${escapeHtml(evDisplay(ev))}</span>
            </div>
          </td>

          <td class="houses-cell">
            ${renderBestBookmakers(bet)}
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = rows.join("");
  }

  function rerender() {
    updateStatusOptions(cachedBets);
    updateBetTypeOptions(cachedBets);
    updateLeagueOptions(cachedBets);
    updateGameOptions(cachedBets);
    renderBetsTable(cachedBets);
  }

  function initFilters() {
    if (elements.statusSelect instanceof HTMLSelectElement) {
      elements.statusSelect.addEventListener("change", () => {
        activeStatusFilter = elements.statusSelect.value || "all";
        rerender();
      });
    }

    if (elements.betTypeSelect instanceof HTMLSelectElement) {
      elements.betTypeSelect.addEventListener("change", () => {
        activeBetTypeFilter = elements.betTypeSelect.value || "all";
        rerender();
      });
    }

    if (elements.leagueSelect instanceof HTMLSelectElement) {
      elements.leagueSelect.addEventListener("change", () => {
        activeLeagueFilter = elements.leagueSelect.value || "all";
        rerender();
      });
    }

    if (elements.gameSelect instanceof HTMLSelectElement) {
      elements.gameSelect.addEventListener("change", () => {
        activeGameFilter = elements.gameSelect.value || "all";
        rerender();
      });
    }
  }

  function stopStalePolling() {
    if (stalePollTimer) {
      clearInterval(stalePollTimer);
      stalePollTimer = null;
    }
    stalePollInFlight = false;
  }

  function startStalePolling() {
    if (stalePollTimer) return;

    stalePollTimer = setInterval(async () => {
      if (stalePollInFlight) return;
      stalePollInFlight = true;
      try {
        const state = await loadDashboard();
        if (!state || state.hasError || state.isFresh) {
          stopStalePolling();
        }
      } finally {
        stalePollInFlight = false;
      }
    }, STALE_POLL_INTERVAL_MS);
  }

  async function loadDashboard() {
    try {
      const response = await fetch("/bets", { cache: "no-store" });
      const authResponse = await ensureAuthenticatedResponse(response);
      if (!authResponse) {
        return { hasError: true, isFresh: false };
      }
      const payload = await authResponse.json();
      const hasError = Boolean(payload?.error_message) || String(payload?.status || "").toLowerCase() === "error";
      const isFresh = isPayloadFromToday(payload);
      const warningMessage = String(payload?.warning_message || "").trim();
      const skippedMatchesCount = toNumber(payload?.skipped_matches_count, 0);

      cachedBets = Array.isArray(payload?.bets) ? payload.bets : [];

      renderMeta(payload);
      renderMetrics(payload, cachedBets);
      rerender();

      if (hasError) {
        setStatusMessage(String(payload?.error_message || "Falha ao carregar dados."), "error");
      } else if (!isFresh) {
        setStatusMessage(`Atualizando dados de hoje... cache atual gerado em ${formatDateTime(payload?.generated_at)}.`, "info");
      } else if (warningMessage && skippedMatchesCount <= 0) {
        setStatusMessage(warningMessage, "info");
      } else {
        setStatusMessage("");
      }

      return { hasError, isFresh };
    } catch (error) {
      console.error(error);
      setStatusMessage("Falha ao carregar dashboard.", "error");
      return { hasError: true, isFresh: false };
    }
  }

  async function startBrowserSession() {
    const response = await fetch("/session/start", { method: "POST" });
    const authResponse = await ensureAuthenticatedResponse(response);
    if (!authResponse || !authResponse.ok) return;

    const payload = await authResponse.json();
    sessionId = payload.session_id;

    heartbeatTimer = setInterval(() => {
      if (!sessionId || sessionClosed) return;
      fetch(`/session/heartbeat?session_id=${encodeURIComponent(sessionId)}`, {
        method: "POST",
        keepalive: true,
      })
        .then(ensureAuthenticatedResponse)
        .catch(() => {});
    }, 10000);
  }

  function endBrowserSession() {
    if (!sessionId || sessionClosed) return;
    sessionClosed = true;
    if (heartbeatTimer) clearInterval(heartbeatTimer);
    stopStalePolling();

    const endpoint = `/session/end?session_id=${encodeURIComponent(sessionId)}`;
    if (navigator.sendBeacon) {
      navigator.sendBeacon(endpoint);
    } else {
      fetch(endpoint, { method: "POST", keepalive: true });
    }
  }

  async function bootstrap() {
    initFilters();

    window.addEventListener("pagehide", endBrowserSession);
    window.addEventListener("beforeunload", endBrowserSession);

    await startBrowserSession();
    const state = await loadDashboard();
    if (state && !state.hasError && !state.isFresh) {
      startStalePolling();
    }
  }

  bootstrap();
})();
