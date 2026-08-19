#!/usr/bin/env node
// Conia codici d'accesso per Job Pipeline.
// Uso:  node mint-codes.mjs 10 "amici beta"
//   -> stampa 10 codici + il comando wrangler per inserirli nella D1.
// I codici NON finiscono nel repo: vivono solo nella tua D1 (e in questo output, che tieni tu).

import { randomInt } from 'node:crypto';

const n = Math.max(1, Math.min(500, parseInt(process.argv[2] || '10', 10)));
const label = (process.argv[3] || '').replace(/'/g, "''");
const ALPHA = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // niente 0/O/1/I: leggibili
const block = () => Array.from({ length: 4 }, () => ALPHA[randomInt(ALPHA.length)]).join('');
const codes = Array.from({ length: n }, () => `JP-${block()}-${block()}`);

console.log('# Codici generati (dalli a chi vuoi far entrare):\n');
codes.forEach(c => console.log('  ' + c));

const values = codes.map(c => `('${c}', '${label}')`).join(', ');
const sql = `INSERT INTO codes (code, label) VALUES ${values};`;

console.log('\n# Per inserirli nella D1, lancia:\n');
console.log(`  npx wrangler d1 execute job-pipeline --remote --command "${sql.replace(/"/g, '\\"')}"`);
console.log('\n# (togli --remote per provare sul DB locale)');
