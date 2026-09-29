import { compileFromFile } from 'json-schema-to-typescript';
import { writeFile, readFile } from 'node:fs/promises';
const target = 'apps/web/src/contracts.generated.d.ts';
const output = await compileFromFile('contracts/foundation-v1.schema.json', {
  bannerComment: '/* Generated from contracts/foundation-v1.schema.json. Do not edit. */',
});
if (process.argv.includes('--check')) {
  if (await readFile(target, 'utf8') !== output) throw new Error('Generated types are stale');
} else await writeFile(target, output);
