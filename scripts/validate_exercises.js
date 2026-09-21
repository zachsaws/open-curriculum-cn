#!/usr/bin/env node
/**
 * Small data-contract check for the browser-only practice flow.
 * It intentionally accepts both historical fill_blank answer shapes: string and string[].
 */
const fs = require('fs');
const path = require('path');

const file = path.resolve(__dirname, '../web/data/exercises.json');
const payload = JSON.parse(fs.readFileSync(file, 'utf8'));
const exercises = Array.isArray(payload) ? payload : (payload.exercises || []);
const knownTypes = new Set(['multiple_choice', 'fill_blank', 'short_answer']);
const structural = [];
const notes = [];
const byType = {};

for (const [index, ex] of exercises.entries()) {
  byType[ex.type] = (byType[ex.type] || 0) + 1;
  const ref = ex.id || `#${index}`;
  if (!knownTypes.has(ex.type)) structural.push(`${ref}: unknown type ${String(ex.type)}`);
  if (!String(ex.question || '').trim()) structural.push(`${ref}: missing question`);
  if (ex.answer === undefined || ex.answer === null || ex.answer === '') structural.push(`${ref}: missing answer`);
  if (ex.type === 'multiple_choice') {
    let options = ex.options;
    if (typeof options === 'string') {
      try { options = JSON.parse(options); } catch { structural.push(`${ref}: options is not valid JSON`); }
    }
    if (!Array.isArray(options) || options.length < 2) structural.push(`${ref}: multiple choice needs at least two options`);
  }
  if (ex.type === 'fill_blank' && !Array.isArray(ex.answer)) notes.push(`${ref}: historical string answer`);
}

console.log(JSON.stringify({
  total: exercises.length,
  byType,
  structuralErrors: structural.length,
  historicalStringFillAnswers: notes.length,
  samples: { structural: structural.slice(0, 10), stringFill: notes.slice(0, 10) },
}, null, 2));

if (structural.length) process.exitCode = 1;
