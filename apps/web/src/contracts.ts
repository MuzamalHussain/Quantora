import Ajv from 'ajv';
import schema from '../../../contracts/foundation-v1.schema.json';
import type { FoundationEnvelope } from './contracts.generated';

const validate = new Ajv({ strict: true, strictNumbers: true }).compile(schema);
export function parseEnvelope(value: unknown): FoundationEnvelope {
  if (!validate(value)) throw new Error('Invalid foundation contract');
  return value as FoundationEnvelope;
}
