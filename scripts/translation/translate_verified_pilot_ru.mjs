#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

export const MODEL = 'gemini-3.5-flash-lite';
export const RPM_USER_LIMIT = 15;
export const RPD_LIMIT = 500;
export const CONCURRENCY = 1;
export const MIN_REQUEST_START_INTERVAL_SECONDS = 5;
export const MIN_REQUEST_INTERVAL_MS = MIN_REQUEST_START_INTERVAL_SECONDS * 1_000;
export const CRASH_RECOVERY_WAIT_MS = 60_000;
export const MAX_RETRY_PER_QUESTION = 1;

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
export const ROOT = path.resolve(SCRIPT_DIR, '../..');
export const INPUT_DIR = path.join(ROOT, 'research/qgen/production_pilot_v1');
export const OUTPUT_DIR = path.join(INPUT_DIR, 'generated_russian_unreviewed');
export const LOCK_DIR = path.join(OUTPUT_DIR, '.translator.lock');
export const LEDGER_PATH = path.join(OUTPUT_DIR, 'request-ledger.json');
export const REVIEW_PATH = path.join(OUTPUT_DIR, 'verified-practice-pilot-v1-ru-review.md');

const textFields = [
  'stem_ru', 'lead_in_ru', 'main_rationale_ru',
];

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
const sha256 = (value) => crypto.createHash('sha256').update(value).digest('hex');
const today = () => new Date().toISOString().slice(0, 10);

async function readJson(filePath, label) {
  let content;
  try {
    content = await fs.readFile(filePath, 'utf8');
  } catch (error) {
    throw new Error(`${label} is unavailable: ${error.message}`);
  }
  try {
    return JSON.parse(content);
  } catch (error) {
    throw new Error(`${label} is unreadable or corrupt; refusing to continue: ${error.message}`);
  }
}

async function writeJsonAtomic(filePath, value) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  const temporary = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  await fs.writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  await fs.rename(temporary, filePath);
}

export function optionId(index) {
  return String.fromCharCode(65 + index);
}

export function selectVerifiedPilotQuestions(manifest, authoredItems) {
  if (!Array.isArray(manifest?.items)) throw new Error('Verified Practice Pilot V1 manifest items are missing.');
  const byId = new Map(authoredItems.map((item) => [item.item_id, item]));
  const questions = manifest.items.map(({ item_id }) => byId.get(item_id));
  if (questions.some((question) => question === undefined)) {
    throw new Error('A manifest-listed verified question is missing from pilot_authored_items.json.');
  }
  if (questions.some((question) => question.item_id === 'QPILOT-V1-OBGYN-02')) {
    throw new Error('QPILOT-V1-OBGYN-02 is rejected and must never enter the translation set.');
  }
  return questions;
}

export function englishSourceHash(question) {
  const canonical = {
    item_id: question.item_id,
    discipline: question.discipline,
    topic: question.topic,
    subtopic: question.subtopic,
    learner_decision: question.learner_decision,
    population_context: question.population_context,
    stem: question.stem,
    lead_in: question.lead_in,
    answer_choices: question.answer_choices,
    author_proposed_key: question.author_proposed_key,
    author_rationale: question.author_rationale,
    per_distractor_rationales: question.per_distractor_rationales,
    conditional_next_action_information: question.conditional_next_action_information,
  };
  return sha256(JSON.stringify(canonical));
}

export function buildTranslationRequest(question) {
  const options = question.answer_choices.map((text, index) => ({ id: optionId(index), text }));
  const correctIndex = question.answer_choices.indexOf(question.author_proposed_key);
  if (correctIndex < 0) throw new Error(`${question.item_id}: author_proposed_key is not an answer choice.`);
  const optionRationales = question.per_distractor_rationales.map((rationale) => {
    const index = question.answer_choices.indexOf(rationale.choice);
    if (index < 0) throw new Error(`${question.item_id}: a rationale choice is not an answer choice.`);
    return { option_id: optionId(index), ...rationale };
  });
  return {
    task: 'Translate this one Canadian medical examination question from English to Russian. Return JSON only.',
    rules: [
      'Translate every supplied learner-facing and explanatory field into professional Russian medical language for MCCQE-style medical education.',
      'Preserve clinical meaning, negation, chronology, severity, stage of care, drug identity, diagnostic modality, and numeric meaning. Translate units and terminology naturally where appropriate.',
      'Do not simplify, add medical recommendations, correct or change the underlying medicine, or leak rationale information into the stem or options.',
      'Keep option IDs, their order, and the correct option ID unchanged.',
      'Do not translate references, books, source titles, guideline titles, citations, URLs, DOIs, or publication dates. None are supplied here.',
      'Return exactly this shape: {item_id, stem_ru, lead_in_ru, options:[{id,text_ru}], correct_option_id, main_rationale_ru, option_rationales:[{option_id,why_plausible_ru,why_inferior_here_ru,what_would_make_correct_ru}]}.',
    ],
    question: {
      item_id: question.item_id,
      context: {
        discipline: question.discipline,
        topic: question.topic,
        subtopic: question.subtopic,
        learner_decision: question.learner_decision,
        population_context: question.population_context,
      },
      stem: question.stem,
      lead_in: question.lead_in,
      options,
      correct_option_id: optionId(correctIndex),
      correct_answer_context: question.author_proposed_key,
      main_rationale: question.author_rationale,
      option_rationales: optionRationales,
      conditional_next_action_information: question.conditional_next_action_information,
    },
  };
}

function requiredText(value, label) {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${label} must be a populated string.`);
}

function assertNoSourceOrCitationFields(value, path = '') {
  if (!value || typeof value !== 'object') return;
  for (const [key, child] of Object.entries(value)) {
    const childPath = path ? `${path}.${key}` : key;
    if (/^(?:source|citation|reference|book|guideline|url|doi|publication)(?:_|$)/i.test(key)) {
      throw new Error(`${childPath}: source or citation field must not be generated.`);
    }
    assertNoSourceOrCitationFields(child, childPath);
  }
}

export function validateTranslation(question, translation, sourceContentHash) {
  if (!translation || typeof translation !== 'object') throw new Error(`${question.item_id}: translation is not an object.`);
  assertNoSourceOrCitationFields(translation);
  if (translation.item_id !== question.item_id) throw new Error(`${question.item_id}: translation item ID mismatch.`);
  if (translation.sourceContentHash !== sourceContentHash) throw new Error(`${question.item_id}: sourceContentHash binding mismatch.`);
  if (translation.status !== 'GENERATED_UNREVIEWED') throw new Error(`${question.item_id}: translation status must be GENERATED_UNREVIEWED.`);
  for (const field of textFields) requiredText(translation[field], `${question.item_id}: ${field}`);
  if (!Array.isArray(translation.options) || translation.options.length !== question.answer_choices.length) {
    throw new Error(`${question.item_id}: option count mismatch.`);
  }
  const expectedOptionIds = question.answer_choices.map((_, index) => optionId(index));
  if (translation.options.some((option, index) => option?.id !== expectedOptionIds[index])) {
    throw new Error(`${question.item_id}: option IDs or order mismatch.`);
  }
  translation.options.forEach((option) => requiredText(option.text_ru, `${question.item_id}: option ${option.id}`));
  const expectedCorrectOptionId = optionId(question.answer_choices.indexOf(question.author_proposed_key));
  if (translation.correct_option_id !== expectedCorrectOptionId) throw new Error(`${question.item_id}: correct option ID mismatch.`);
  if (!Array.isArray(translation.option_rationales) || translation.option_rationales.length !== question.per_distractor_rationales.length) {
    throw new Error(`${question.item_id}: option rationale count mismatch.`);
  }
  const expectedRationaleIds = question.per_distractor_rationales.map((rationale) => optionId(question.answer_choices.indexOf(rationale.choice)));
  if (translation.option_rationales.some((rationale, index) => rationale?.option_id !== expectedRationaleIds[index])) {
    throw new Error(`${question.item_id}: option rationale IDs or order mismatch.`);
  }
  translation.option_rationales.forEach((rationale) => {
    requiredText(rationale.why_plausible_ru, `${question.item_id}: why_plausible_ru`);
    requiredText(rationale.why_inferior_here_ru, `${question.item_id}: why_inferior_here_ru`);
    requiredText(rationale.what_would_make_correct_ru, `${question.item_id}: what_would_make_correct_ru`);
  });
  return true;
}

async function acquireLock() {
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  try {
    await fs.mkdir(LOCK_DIR);
  } catch (error) {
    if (error.code === 'EEXIST') {
      throw new Error(`Another translation run may be active, or a previous run terminated unexpectedly. Confirm no translation process is running, then use the documented manual recovery command: node scripts/translation/translate_verified_pilot_ru.mjs --recover-lock`);
    }
    throw error;
  }
  await fs.writeFile(path.join(LOCK_DIR, 'owner.json'), `${JSON.stringify({ pid: process.pid, acquired_at: new Date().toISOString() }, null, 2)}\n`);
}

async function releaseLock() {
  await fs.rm(LOCK_DIR, { recursive: true, force: true });
}

async function recoverLock() {
  try {
    await fs.access(LOCK_DIR);
  } catch {
    console.log('No translator lock exists.');
    return;
  }
  await fs.rm(LOCK_DIR, { recursive: true, force: false });
  console.log('Removed translator lock. Run this only after confirming no translation process is active.');
}

async function loadLedger() {
  try {
    await fs.access(LEDGER_PATH);
  } catch {
    return { schema_version: '1.0', attempts: [] };
  }
  const ledger = await readJson(LEDGER_PATH, 'Request ledger');
  if (!Array.isArray(ledger?.attempts)) throw new Error('Request ledger is unreadable or corrupt; refusing to continue.');
  return ledger;
}

async function saveLedger(ledger) {
  await writeJsonAtomic(LEDGER_PATH, ledger);
}

export function calculateRequestGate(ledger, now = Date.now(), date = today()) {
  const todayAttempts = ledger.attempts.filter((attempt) => attempt.date === date);
  if (todayAttempts.length >= RPD_LIMIT) return { blocked: true, wait_ms: 0 };
  const hasIncompleteAttempt = ledger.attempts.some((attempt) => attempt.status === 'RECORDED');
  const latestStart = ledger.attempts
    .map((attempt) => Date.parse(attempt.started_at))
    .filter(Number.isFinite)
    .sort((a, b) => b - a)[0];
  const spacingWait = latestStart === undefined ? 0 : Math.max(0, MIN_REQUEST_INTERVAL_MS - (now - latestStart));
  return { blocked: false, wait_ms: Math.max(hasIncompleteAttempt ? CRASH_RECOVERY_WAIT_MS : 0, spacingWait) };
}

async function applyCrashRecoveryAndRateLimit(ledger) {
  const gate = calculateRequestGate(ledger);
  if (gate.blocked) {
    const count = ledger.attempts.filter((attempt) => attempt.date === today()).length;
    throw new Error(`Daily request limit reached: ${count}/${RPD_LIMIT} attempts are already recorded today.`);
  }
  if (ledger.attempts.some((attempt) => attempt.status === 'RECORDED')) {
    console.log('A prior recorded attempt is incomplete; it counts toward the daily limit. Waiting 60 seconds before another Gemini request.');
  }
  if (gate.wait_ms > 0) await sleep(gate.wait_ms);
}

export function extractJson(text) {
  const trimmed = text.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  try { return JSON.parse(trimmed); } catch (error) { throw new Error(`Gemini did not return valid JSON: ${error.message}`); }
}

async function geminiTranslate(request, apiKey) {
  const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${encodeURIComponent(apiKey)}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      contents: [{ role: 'user', parts: [{ text: JSON.stringify(request) }] }],
      generationConfig: { responseMimeType: 'application/json', temperature: 0 },
    }),
  });
  if (!response.ok) throw new Error(`Gemini request failed (${response.status}): ${(await response.text()).slice(0, 500)}`);
  const body = await response.json();
  const text = body?.candidates?.[0]?.content?.parts?.map((part) => part.text ?? '').join('');
  if (!text) throw new Error('Gemini returned no text content.');
  return extractJson(text);
}

function retryableTechnicalFailure(error) {
  const message = String(error?.message ?? error);
  return /Gemini request failed \((?:429|5\d\d)\)|fetch failed|network|Gemini did not return valid JSON|Gemini returned no text content|translation is not an object|translation item ID mismatch|sourceContentHash binding mismatch|translation status must be|must be a populated string|option count mismatch|option IDs or order mismatch|correct option ID mismatch|option rationale count mismatch|option rationale IDs or order mismatch|source or citation field/i.test(message);
}

async function existingValidTranslation(question, hash) {
  const filePath = path.join(OUTPUT_DIR, `${question.item_id}.json`);
  try { await fs.access(filePath); } catch { return null; }
  const translation = await readJson(filePath, `${question.item_id} translation`);
  validateTranslation(question, translation, hash);
  return translation;
}

async function translateQuestion(question, ledger, apiKey, counters) {
  const hash = englishSourceHash(question);
  if (await existingValidTranslation(question, hash)) {
    console.log(`${question.item_id}: cached valid translation; skipping.`);
    return;
  }
  for (let retry = 0; retry <= MAX_RETRY_PER_QUESTION; retry += 1) {
    await applyCrashRecoveryAndRateLimit(ledger);
    const attempt = {
      attempt_id: crypto.randomUUID(), item_id: question.item_id, retry_index: retry,
      date: today(), started_at: new Date().toISOString(), status: 'RECORDED', model: MODEL,
    };
    ledger.attempts.push(attempt);
    await saveLedger(ledger); // Persist before the physical API call.
    counters.actualApiCalls += 1;
    try {
      const raw = await geminiTranslate(buildTranslationRequest(question), apiKey);
      const translation = { schema_version: '1.0', status: 'GENERATED_UNREVIEWED', sourceContentHash: hash, ...raw };
      validateTranslation(question, translation, hash);
      await writeJsonAtomic(path.join(OUTPUT_DIR, `${question.item_id}.json`), translation);
      attempt.status = 'SUCCEEDED';
      attempt.finished_at = new Date().toISOString();
      await saveLedger(ledger);
      counters.questionsTranslated += 1;
      console.log(`${question.item_id}: saved and validated.`);
      return;
    } catch (error) {
      attempt.status = 'FAILED';
      attempt.finished_at = new Date().toISOString();
      attempt.error = String(error.message).slice(0, 1000);
      await saveLedger(ledger);
      if (!retryableTechnicalFailure(error) || retry === MAX_RETRY_PER_QUESTION) throw new Error(`${question.item_id}: failed after one retry: ${error.message}`);
      counters.retries += 1;
      console.warn(`${question.item_id}: attempt failed; one retry remains.`);
    }
  }
}

function markdownEscape(value) {
  return String(value).replace(/\r?\n/g, '\n\n');
}

export function buildReviewMarkdown(questions, translations) {
  const blocks = ['# Verified Practice Pilot V1 — Russian Translation Review', '', 'Status: `GENERATED_UNREVIEWED`', ''];
  for (const question of questions) {
    const translation = translations.get(question.item_id);
    blocks.push(`## ${question.item_id}`, '', '### ENGLISH STEM', markdownEscape(question.stem), '', '### RUSSIAN STEM', markdownEscape(translation.stem_ru), '', '### ENGLISH LEAD-IN', markdownEscape(question.lead_in), '', '### RUSSIAN LEAD-IN', markdownEscape(translation.lead_in_ru), '');
    question.answer_choices.forEach((option, index) => {
      blocks.push(`### ENGLISH OPTION ${optionId(index)}`, markdownEscape(option), '', `### RUSSIAN OPTION ${optionId(index)}`, markdownEscape(translation.options[index].text_ru), '');
    });
    blocks.push('### CORRECT OPTION ID', translation.correct_option_id, '', '### ENGLISH MAIN RATIONALE', markdownEscape(question.author_rationale), '', '### RUSSIAN MAIN RATIONALE', markdownEscape(translation.main_rationale_ru), '');
    question.per_distractor_rationales.forEach((rationale, index) => {
      const ru = translation.option_rationales[index];
      blocks.push(`### ENGLISH OPTION RATIONALE ${ru.option_id}`, `**Why plausible:** ${markdownEscape(rationale.why_plausible)}`, '', `**Why inferior here:** ${markdownEscape(rationale.why_inferior_here)}`, '', `**What would make correct:** ${markdownEscape(rationale.what_would_make_correct)}`, '', `### RUSSIAN OPTION RATIONALE ${ru.option_id}`, `**Почему правдоподобен:** ${markdownEscape(ru.why_plausible_ru)}`, '', `**Почему уступает здесь:** ${markdownEscape(ru.why_inferior_here_ru)}`, '', `**Что сделало бы правильным:** ${markdownEscape(ru.what_would_make_correct_ru)}`, '');
    });
  }
  return `${blocks.join('\n')}\n`;
}

async function loadQuestions() {
  const manifest = await readJson(path.join(INPUT_DIR, 'pilot_v1_verified_accept_manifest.json'), 'Verified Practice Pilot V1 manifest');
  const authored = await readJson(path.join(INPUT_DIR, 'pilot_authored_items.json'), 'Pilot authored items');
  if (manifest.verified_accept_count !== 11) throw new Error('Verified Practice Pilot V1 manifest must declare exactly 11 accepted questions.');
  return selectVerifiedPilotQuestions(manifest, authored.items);
}

async function run() {
  const argumentsSet = new Set(process.argv.slice(2));
  if (argumentsSet.has('--recover-lock')) { await recoverLock(); return; }
  const dryRun = argumentsSet.has('--dry-run');
  const unexpected = [...argumentsSet].filter((argument) => !['--dry-run'].includes(argument));
  if (unexpected.length) throw new Error(`Unknown argument(s): ${unexpected.join(', ')}`);
  const questions = await loadQuestions();
  if (questions.length !== 11) throw new Error(`Expected 11 verified pilot questions, found ${questions.length}.`);
  if (dryRun) {
    console.log(`DRY_RUN_PASS: selected ${questions.length} verified questions; QPILOT-V1-OBGYN-02 excluded; one complete unmasked request per question.`);
    return;
  }
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) throw new Error('GEMINI_API_KEY is absent. Set it with: export GEMINI_API_KEY="your-key-here"');
  await acquireLock();
  try {
    const ledger = await loadLedger();
    const counters = { questionsTranslated: 0, actualApiCalls: 0, retries: 0 };
    for (const question of questions) await translateQuestion(question, ledger, apiKey, counters);
    const translations = new Map();
    for (const question of questions) {
      const hash = englishSourceHash(question);
      const translation = await existingValidTranslation(question, hash);
      if (!translation) throw new Error(`${question.item_id}: no valid persisted translation after run.`);
      translations.set(question.item_id, translation);
    }
    await fs.writeFile(REVIEW_PATH, buildReviewMarkdown(questions, translations), 'utf8');
    console.log(`COMPLETE: questions_translated=${counters.questionsTranslated} actual_api_calls=${counters.actualApiCalls} retries=${counters.retries}`);
    console.log(`REVIEW_MARKDOWN_PATH=${REVIEW_PATH}`);
  } finally {
    await releaseLock();
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  run().catch((error) => { console.error(`TRANSLATION_FAILURE: ${error.message}`); process.exitCode = 1; });
}
