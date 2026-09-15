import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildTranslationRequest,
  calculateRequestGate,
  extractJson,
  MODEL,
  MIN_REQUEST_START_INTERVAL_SECONDS,
  RPD_LIMIT,
  RPM_USER_LIMIT,
  selectVerifiedPilotQuestions,
  validateTranslation,
} from '../scripts/translation/translate_verified_pilot_ru.mjs';

test('uses the approved Gemini Flash Lite model', () => {
  assert.equal(MODEL, 'gemini-3.5-flash-lite');
  assert.equal(RPM_USER_LIMIT, 15);
  assert.equal(RPD_LIMIT, 500);
  assert.equal(MIN_REQUEST_START_INTERVAL_SECONDS, 5);
});

const sourceQuestion = {
  item_id: 'QPILOT-V1-MED-01',
  discipline: 'MED',
  topic: 'Chest Pain',
  subtopic: 'Initial investigation',
  population_context: 'NA',
  stem: 'A 58-year-old man has 97% oxygen saturation.',
  lead_in: 'What is the next investigation?',
  answer_choices: ['Troponin', 'D-dimer'],
  author_proposed_key: 'Troponin',
  author_rationale: 'Troponin completes the initial assessment.',
  per_distractor_rationales: [{
    choice: 'D-dimer',
    why_plausible: 'Chest pain has alternatives.',
    why_inferior_here: 'This presentation is ischaemic.',
    what_would_make_correct: 'Pulmonary embolism risk would make it appropriate.',
  }],
};

test('selects exactly manifest-listed accepted questions and excludes the rejected OBGYN item', () => {
  const selected = selectVerifiedPilotQuestions(
    { items: [{ item_id: 'QPILOT-V1-MED-01' }, { item_id: 'QPILOT-V1-OBGYN-03' }] },
    [sourceQuestion, { ...sourceQuestion, item_id: 'QPILOT-V1-OBGYN-02' }, { ...sourceQuestion, item_id: 'QPILOT-V1-OBGYN-03' }],
  );

  assert.deepEqual(selected.map((question) => question.item_id), ['QPILOT-V1-MED-01', 'QPILOT-V1-OBGYN-03']);
  assert.equal(selected.some((question) => question.item_id === 'QPILOT-V1-OBGYN-02'), false);
});

test('sends one complete unmasked question with medical context and no source metadata', () => {
  const request = buildTranslationRequest(sourceQuestion);

  assert.equal(request.question.item_id, sourceQuestion.item_id);
  assert.equal(request.question.stem, sourceQuestion.stem);
  assert.equal(request.question.lead_in, sourceQuestion.lead_in);
  assert.deepEqual(request.question.options.map((option) => option.id), ['A', 'B']);
  assert.equal(request.question.correct_option_id, 'A');
  assert.equal(request.question.main_rationale, sourceQuestion.author_rationale);
  assert.equal(request.question.option_rationales.length, 1);
  assert.equal(request.question.context.discipline, 'MED');
  assert.deepEqual(Object.keys(request.question).sort(), [
    'conditional_next_action_information', 'context', 'correct_answer_context', 'correct_option_id',
    'item_id', 'lead_in', 'main_rationale', 'option_rationales', 'options', 'stem',
  ]);
});

test('accepts natural Russian localization while preserving structural identity', () => {
  const sourceContentHash = 'a'.repeat(64);
  const valid = {
    schema_version: '1.0',
    status: 'GENERATED_UNREVIEWED',
    item_id: sourceQuestion.item_id,
    sourceContentHash,
    stem_ru: 'У 58-летнего мужчины сатурация кислорода 97%.',
    lead_in_ru: 'Какое исследование следует выполнить следующим?',
    options: [
      { id: 'A', text_ru: 'Тропонин' },
      { id: 'B', text_ru: 'D-димер' },
    ],
    correct_option_id: 'A',
    main_rationale_ru: 'Тропонин дополняет первоначальную оценку.',
    option_rationales: [{
      option_id: 'B',
      why_plausible_ru: 'Боль в груди имеет альтернативные причины.',
      why_inferior_here_ru: 'Эта картина ишемическая.',
      what_would_make_correct_ru: 'Риск лёгочной эмболии сделал бы этот вариант уместным.',
    }],
  };

  assert.doesNotThrow(() => validateTranslation(sourceQuestion, valid, sourceContentHash));
  assert.throws(() => validateTranslation(sourceQuestion, { ...valid, options: [...valid.options].reverse() }, sourceContentHash), /option IDs or order/);
  assert.doesNotThrow(() => validateTranslation(sourceQuestion, { ...valid, stem_ru: 'У мужчины нормальная сатурация кислорода.' }, sourceContentHash));
});

test('blocks at 500 recorded daily attempts and applies 5-second spacing conservatively', () => {
  const now = new Date('2026-09-14T12:00:00.000Z').getTime();
  const incomplete = { attempts: [{ date: '2026-09-14', started_at: new Date(now - 1_000).toISOString(), status: 'RECORDED' }] };
  assert.deepEqual(calculateRequestGate(incomplete, now, '2026-09-14'), { blocked: false, wait_ms: 60_000 });

  const spaced = { attempts: [{ date: '2026-09-14', started_at: new Date(now - 4_000).toISOString(), status: 'SUCCEEDED' }] };
  assert.deepEqual(calculateRequestGate(spaced, now, '2026-09-14'), { blocked: false, wait_ms: 1_000 });

  const exhausted = { attempts: Array.from({ length: 500 }, () => ({ date: '2026-09-14', started_at: new Date(now - 60_000).toISOString(), status: 'FAILED' })) };
  assert.deepEqual(calculateRequestGate(exhausted, now, '2026-09-14'), { blocked: true, wait_ms: 0 });
});

function measurementQuestion(expression) {
  return {
    ...sourceQuestion,
    stem: `Heart rate is ${expression}.`,
  };
}

function generatedTranslation(question, stemRu) {
  return {
    schema_version: '1.0',
    status: 'GENERATED_UNREVIEWED',
    item_id: question.item_id,
    sourceContentHash: 'b'.repeat(64),
    stem_ru: stemRu,
    lead_in_ru: 'Какое исследование следует выполнить следующим?',
    options: [
      { id: 'A', text_ru: 'Тропонин' },
      { id: 'B', text_ru: 'D-димер' },
    ],
    correct_option_id: 'A',
    main_rationale_ru: 'Тропонин дополняет первоначальную оценку.',
    option_rationales: [{
      option_id: 'B',
      why_plausible_ru: 'Боль в груди имеет альтернативные причины.',
      why_inferior_here_ru: 'Эта картина ишемическая.',
      what_would_make_correct_ru: 'Риск лёгочной эмболии сделал бы этот вариант уместным.',
    }],
  };
}

test('accepts Russian hours and beats-per-minute localization without measurement placeholders', () => {
  const hours = measurementQuestion('within 6 hours');
  const beats = measurementQuestion('120 beats/min');
  assert.doesNotThrow(() => validateTranslation(hours, generatedTranslation(hours, 'В течение 6 часов.'), 'b'.repeat(64)));
  assert.doesNotThrow(() => validateTranslation(beats, generatedTranslation(beats, 'Частота сердечных сокращений составляет 120 уд/мин.'), 'b'.repeat(64)));
  assert.doesNotMatch(buildTranslationRequest(beats).question.stem, /PROTECTED_MEASUREMENT/);
});

test('fails closed for missing learner-facing text, malformed structure, and generated citation fields', () => {
  const valid = generatedTranslation(sourceQuestion, 'У мужчины сатурация кислорода 97%.');
  assert.throws(() => validateTranslation(sourceQuestion, { ...valid, stem_ru: '' }, 'b'.repeat(64)), /stem_ru must be a populated string/);
  assert.throws(() => validateTranslation(sourceQuestion, { ...valid, options: null }, 'b'.repeat(64)), /option count mismatch/);
  assert.throws(() => validateTranslation(sourceQuestion, { ...valid, citation_ru: 'Источник' }, 'b'.repeat(64)), /source or citation field/);
});

test('fails closed for malformed Gemini JSON', () => {
  assert.throws(() => extractJson('{not json'), /Gemini did not return valid JSON/);
});
