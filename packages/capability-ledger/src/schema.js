/**
 * CapabilityLedger receipt JSON schema and valid state/owner enumerations.
 *
 * Aligned with SourceOS-Linux/sourceos-spec#99.
 */

export const CAPABILITY_STATES = /** @type {const} */ ([
  'declared',
  'requested',
  'negotiating',
  'available',
  'enabled',
  'degraded',
  'blocked_by_policy',
  'unsupported_by_runtime',
  'unsupported_by_server',
  'missing_plugin',
  'missing_schema',
  'failed',
]);

export const CAPABILITY_OWNERS = /** @type {const} */ ([
  'UI',
  'runtime',
  'server',
  'plugin',
  'policy',
]);

/**
 * JSON Schema (draft-07) for a CapabilityLedger receipt.
 */
export const receiptSchema = {
  $schema: 'http://json-schema.org/draft-07/schema#',
  $id: 'urn:sourceos:capability-ledger:receipt',
  title: 'CapabilityLedgerReceipt',
  type: 'object',
  required: ['capabilityId', 'state', 'owner', 'timestamp', 'evidenceRefs', 'conflictWarnings'],
  additionalProperties: false,
  properties: {
    capabilityId: { type: 'string', minLength: 1 },
    state: { type: 'string', enum: CAPABILITY_STATES },
    owner: { type: 'string', enum: CAPABILITY_OWNERS },
    timestamp: { type: 'string', format: 'date-time' },
    policyDecisionRef: { type: ['string', 'null'] },
    evidenceRefs: { type: 'array', items: { type: 'string' } },
    conflictWarnings: { type: 'array', items: { type: 'string' } },
  },
};

/**
 * Example receipt — used for schema validation and documentation.
 */
export const receiptExample = {
  capabilityId: 'pdf-viewer',
  state: 'enabled',
  owner: 'runtime',
  timestamp: '2026-01-01T00:00:00.000Z',
  policyDecisionRef: 'policy:allow-pdf-viewer:v1',
  evidenceRefs: ['config:features/pdf-viewer:enabled', 'plugin:pdf-renderer:loaded'],
  conflictWarnings: [],
};
