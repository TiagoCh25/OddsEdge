(() => {
  const nameInput = document.getElementById("nome");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("senha");
  const label = document.getElementById("password-strength-label");
  const fill = document.getElementById("password-strength-fill");
  const rules = document.getElementById("password-rules");

  if (!(passwordInput instanceof HTMLInputElement) || !label || !fill || !rules) {
    return;
  }

  function normalizeText(value) {
    return String(value || "")
      .toLowerCase()
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "");
  }

  function looksPersonal(password, name, email) {
    const normalizedPassword = normalizeText(password);
    if (!normalizedPassword) return false;

    const emailLocal = normalizeText(String(email || "").split("@", 1)[0] || "");
    if (emailLocal.length >= 3 && normalizedPassword.includes(emailLocal)) {
      return true;
    }

    const parts = String(name || "")
      .toLowerCase()
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .split(/\s+/)
      .filter((item) => item.trim().length >= 3)
      .map((item) => normalizeText(item));

    return parts.some((part) => part && normalizedPassword.includes(part));
  }

  function looksCommon(password) {
    const normalizedPassword = normalizeText(password);
    const blocked = new Set([
      "12345678",
      "123456789",
      "1234567890",
      "12345678901",
      "123456789012",
      "admin123",
      "password",
      "password123",
      "qwerty123",
      "senha123",
      "senhaforte123",
      "abc123456",
      "welcome123",
      "letmein123",
      "nome123456",
    ]);
    return blocked.has(normalizedPassword);
  }

  function looksSimpleSequence(password) {
    const normalizedPassword = normalizeText(password);
    if (!normalizedPassword) return false;
    const sequences = [
      "01234567890123456789",
      "abcdefghijklmnopqrstuvwxyz",
      "qwertyuiopasdfghjklzxcvbnm",
    ];

    for (let start = 0; start <= normalizedPassword.length - 4; start += 1) {
      for (let size = 4; size <= normalizedPassword.length - start; size += 1) {
        const chunk = normalizedPassword.slice(start, start + size);
        if (sequences.some((sequence) => sequence.includes(chunk))) {
          return true;
        }
      }
    }
    return false;
  }

  function countCharacterClasses(password) {
    return [
      /[a-z]/.test(password),
      /[A-Z]/.test(password),
      /\d/.test(password),
      /[^A-Za-z0-9\s]/.test(password),
    ].filter(Boolean).length;
  }

  function analyzePassword(value) {
    const password = String(value || "");
    const name = nameInput instanceof HTMLInputElement ? nameInput.value : "";
    const email = emailInput instanceof HTMLInputElement ? emailInput.value : "";
    const hasLetter = /[A-Za-z]/.test(password);
    const hasNumber = /\d/.test(password);
    const hasSymbol = /[^A-Za-z0-9\s]/.test(password);
    const personal = looksPersonal(password, name, email);
    const common = looksCommon(password);
    const sequential = looksSimpleSequence(password);
    const classes = countCharacterClasses(password);
    const requirements = {
      minimo_10: password.length >= 10,
      tem_letra: hasLetter,
      tem_numero_ou_simbolo: hasNumber || hasSymbol,
      nao_pessoal: !personal,
      nao_comum: !common && !sequential,
      tem_reforco: password.length >= 14 && classes >= 3,
    };

    const minimumOk = (
      requirements.minimo_10
      && requirements.tem_letra
      && requirements.tem_numero_ou_simbolo
      && requirements.nao_pessoal
      && requirements.nao_comum
    );
    const score = (
      Number(requirements.minimo_10)
      + Number(password.length >= 14)
      + classes
      + Number(requirements.nao_pessoal)
      + Number(requirements.nao_comum)
    );

    if (!password || !minimumOk) {
      return { level: "fraca", width: "28%", requirements };
    }
    if (password.length >= 14 && classes >= 3) {
      return { level: "forte", width: "100%", requirements };
    }
    if (score >= 6) {
      return { level: "normal", width: "62%", requirements };
    }
    return { level: "fraca", width: "28%", requirements };
  }

  function labelFor(level) {
    if (level === "forte") return "Forte";
    if (level === "normal") return "Normal";
    return "Fraca";
  }

  function applyAnalysis() {
    const analysis = analyzePassword(passwordInput.value);

    label.textContent = labelFor(analysis.level);
    fill.classList.remove("is-fraca", "is-normal", "is-forte");
    fill.classList.add(`is-${analysis.level}`);
    fill.style.width = analysis.width;

    rules.querySelectorAll("[data-rule]").forEach((item) => {
      const key = item.getAttribute("data-rule");
      const ok = Boolean(key && analysis.requirements[key]);
      item.classList.toggle("is-ok", ok);
    });
  }

  passwordInput.addEventListener("input", applyAnalysis);
  if (nameInput instanceof HTMLInputElement) {
    nameInput.addEventListener("input", applyAnalysis);
  }
  if (emailInput instanceof HTMLInputElement) {
    emailInput.addEventListener("input", applyAnalysis);
  }
  applyAnalysis();
})();
