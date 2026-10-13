/*
 * Snakbite Password Security analyzer.
 * This file is embedded directly in a local browser component. It makes no
 * network requests and exports no password or analysis data from the iframe.
 */
(function (root) {
  "use strict";

  const COMMON_PASSWORDS = [
    "123456", "123456789", "12345678", "password", "password123", "qwerty",
    "qwerty123", "admin", "admin123", "letmein", "welcome", "iloveyou",
    "monkey", "dragon", "football", "sunshine", "princess", "abc123",
    "passw0rd", "1q2w3e4r", "zaq12wsx", "trustno1", "login", "secret"
  ];
  const WEAK_WORDS = [
    "password", "admin", "welcome", "letmein", "qwerty", "login", "secret",
    "iloveyou", "monkey", "dragon", "football", "sunshine", "princess"
  ];
  const KEYBOARD_PATTERNS = [
    "qwerty", "qwert", "asdfgh", "asdf", "zxcvbn", "zxcvb", "poiuyt",
    "qazwsx", "1qaz2wsx", "!@#$", "098765"
  ];

  function normalizePredictable(value) {
    return value.toLowerCase().replace(/[013457@$]/g, function (ch) {
      return ({ "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s" })[ch] || ch;
    });
  }

  function analyzePassword(password, comparisonValue) {
    const value = String(password == null ? "" : password);
    const comparison = String(comparisonValue == null ? "" : comparisonValue);
    const characters = Array.from(value);
    const length = characters.length;
    if (!length) return { empty: true, score: 0, classification: "—", patterns: [], recommendations: [], checks: [], length: 0, groups: 0, entropy: 0 };

    const checks = [];
    const patterns = [];
    const lower = value.toLowerCase();
    const normalized = normalizePredictable(value).replace(/[^a-z0-9]/g, "");
    const sequenceSource = lower.replace(/[^a-z0-9]/g, "");
    const upperCount = (value.match(/\p{Lu}/gu) || []).length;
    const lowerCount = (value.match(/\p{Ll}/gu) || []).length;
    const numberCount = (value.match(/\p{N}/gu) || []).length;
    const specialCount = Array.from(value).filter(ch => !/[\p{L}\p{N}]/u.test(ch)).length;
    const groups = [upperCount > 0, lowerCount > 0, numberCount > 0, specialCount > 0].filter(Boolean).length;
    const uniqueRatio = new Set(characters).size / length;

    checks.push({ label: "Length", ok: length >= 14, detail: length + " characters" });
    checks.push({ label: "Uppercase letters", ok: upperCount > 0, detail: upperCount + " found" });
    checks.push({ label: "Lowercase letters", ok: lowerCount > 0, detail: lowerCount + " found" });
    checks.push({ label: "Numbers", ok: numberCount > 0, detail: numberCount + " found" });
    checks.push({ label: "Special characters", ok: specialCount > 0, detail: specialCount + " found" });
    checks.push({ label: "Character diversity", ok: groups >= 3 && uniqueRatio >= 0.55, detail: groups + " character groups · " + Math.round(uniqueRatio * 100) + "% unique characters" });

    const common = COMMON_PASSWORDS.some(item => normalizePredictable(lower) === normalizePredictable(item));
    if (common) patterns.push({ label: "Common password", reason: "This exactly matches an example on Snakbite’s small local common-password list." });

    let sequential = false;
    for (let i = 0; i <= sequenceSource.length - 4 && !sequential; i++) {
      let ascending = true, descending = true;
      for (let j = 1; j < 4; j++) {
        const difference = sequenceSource.charCodeAt(i + j) - sequenceSource.charCodeAt(i + j - 1);
        if (difference !== 1) ascending = false;
        if (difference !== -1) descending = false;
      }
      if (ascending || descending) sequential = true;
    }
    if (sequential) patterns.push({ label: "Sequential characters", reason: "A run such as 1234 or abcd is easy to predict." });

    if (/(.)\1{3,}/iu.test(value)) patterns.push({ label: "Repeated character", reason: "Four or more copies of one character add little unpredictability." });
    let repeatedSequence = false;
    for (let size = 1; size <= 3 && !repeatedSequence; size++) {
      for (let i = 0; i + size * 3 <= normalized.length; i++) {
        const part = normalized.slice(i, i + size);
        if (part && normalized.slice(i + size, i + size * 2) === part && normalized.slice(i + size * 2, i + size * 3) === part) { repeatedSequence = true; break; }
      }
    }
    if (repeatedSequence) patterns.push({ label: "Repeated sequence", reason: "A short chunk repeats several times, for example abcabc or 121212." });

    if (KEYBOARD_PATTERNS.some(item => lower.includes(item))) patterns.push({ label: "Keyboard pattern", reason: "A familiar keyboard path is commonly guessed." });

    const predictableWord = WEAK_WORDS.find(word => normalized.includes(normalizePredictable(word)) || lower.includes(word));
    if (predictableWord && !common) patterns.push({ label: "Common word or substitution", reason: "The password contains a predictable word or a simple symbol/number substitution." });

    if (/(password|admin|welcome|letmein|qwerty|login|secret|123|202[0-9]|19[89][0-9])(?:[!@#$._-]+|\d{0,4})$/i.test(lower) && !common) {
      patterns.push({ label: "Predictable prefix or suffix", reason: "A familiar word, year, or short number/symbol ending is a common variation." });
    }

    if (/(?:19|20)\d{2}/.test(value) || /\b\d{1,2}[-/.]\d{1,2}[-/.](?:\d{2}|\d{4})\b/.test(value)) {
      patterns.push({ label: "Date-like pattern", reason: "A year or date-like sequence can be guessed from personal information." });
    }

    const personalFragment = Array.from(new Set(comparison.toLowerCase().split(/[^\p{L}\p{N}]+/u).filter(part => part.length >= 3))).find(part => lower.includes(part));
    if (personalFragment) patterns.push({ label: "Comparison detail match", reason: "The password contains a fragment from the comparison value you supplied." });

    checks.push({ label: "No common-password match", ok: !common, detail: common ? "Example match found" : "No match in the limited local list" });
    checks.push({ label: "No predictable patterns", ok: patterns.length === 0, detail: patterns.length ? patterns.length + " pattern(s) found" : "No listed patterns found" });

    let score = Math.min(50, length * 3.1) + groups * 8 + Math.round(uniqueRatio * 6);
    if (length >= 20 && groups <= 2) score += 8; // long passphrases can be strong without symbol-heavy composition
    if (patterns.length === 0 && length >= 12) score += 5;
    const deductions = {
      "Common password": 55, "Sequential characters": 22, "Repeated character": 18,
      "Repeated sequence": 24, "Keyboard pattern": 25, "Common word or substitution": 18,
      "Predictable prefix or suffix": 14, "Date-like pattern": 14, "Comparison detail match": 25
    };
    patterns.forEach(item => { score -= deductions[item.label] || 0; });
    if (common) score = Math.min(score, 10);
    if (patterns.some(item => ["Keyboard pattern", "Repeated sequence", "Comparison detail match"].includes(item.label))) score = Math.min(score, 39);
    if (sequential && length < 10) score = Math.min(score, 39);
    score = Math.max(0, Math.min(100, Math.round(score)));
    if (length < 8) score = Math.min(score, 19);
    else if (length < 12) score = Math.min(score, 39);
    else if (length < 14) score = Math.min(score, 59);

    let classification = "Very Weak";
    if (score >= 80) classification = "Very Strong";
    else if (score >= 60) classification = "Strong";
    else if (score >= 40) classification = "Fair";
    else if (score >= 20) classification = "Weak";

    const recommendations = [];
    if (length < 14) recommendations.push("Use a longer, unique password; aim for at least 14 characters or a multi-word passphrase.");
    if (common || patterns.some(p => ["Common word or substitution", "Predictable prefix or suffix"].includes(p.label))) recommendations.push("Avoid common password words, predictable substitutions, and familiar endings.");
    if (sequential || repeatedSequence || patterns.some(p => ["Repeated character", "Keyboard pattern"].includes(p.label))) recommendations.push("Avoid keyboard walks, sequences, and repeated characters or chunks.");
    if (patterns.some(p => ["Date-like pattern", "Comparison detail match"].includes(p.label))) recommendations.push("Remove dates and personal details; use words unrelated to you.");
    if (groups < 3) recommendations.push("Use a varied passphrase or a randomly generated password; length and uniqueness matter more than symbol swaps.");
    if (recommendations.length === 0) recommendations.push("Keep it unique to one account. A password manager can generate and store strong passwords.");

    // Upper-bound estimate for a uniformly random choice from the observed character groups.
    let alphabet = 0;
    if (upperCount) alphabet += 26;
    if (lowerCount) alphabet += 26;
    if (numberCount) alphabet += 10;
    if (specialCount) alphabet += 32;
    if (Array.from(value).some(ch => ch.codePointAt(0) > 127)) alphabet += 100;
    const entropy = Math.round(length * Math.log2(Math.max(alphabet, 1)));
    return { empty: false, score, classification, patterns, recommendations, checks, length, groups, entropy, common };
  }

  root.SnakbitePasswordAnalyzer = { analyzePassword: analyzePassword };
  if (typeof module !== "undefined" && module.exports) module.exports = { analyzePassword: analyzePassword };
})(typeof window !== "undefined" ? window : globalThis);
