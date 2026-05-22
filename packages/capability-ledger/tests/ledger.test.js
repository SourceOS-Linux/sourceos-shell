/**
 * CapabilityLedger runtime tests.
 *
 * Covers acceptance criteria from SourceOS-Linux/sourceos-spec#99:
 *   - enabling a capability
 *   - denying (blocking by policy)
 *   - unsupported by runtime / server
 *   - missing plugin
 *   - failed reconciliation
 *   - conflict warnings
 *   - receipt schema conformance
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

import { CapabilityLedger } from '../src/index.js';
import { CAPABILITY_STATES, CAPABILITY_OWNERS, receiptSchema, receiptExample } from '../src/schema.js';

// ── schema sanity ────────────────────────────────────────────────────────────

describe('receiptSchema', () => {
  test('contains all required capability states', () => {
    assert.deepEqual(receiptSchema.properties.state.enum, CAPABILITY_STATES);
  });

  test('contains all required capability owners', () => {
    assert.deepEqual(receiptSchema.properties.owner.enum, CAPABILITY_OWNERS);
  });

  test('example receipt matches schema required fields', () => {
    for (const field of receiptSchema.required) {
      assert.ok(field in receiptExample, `receiptExample missing required field: ${field}`);
    }
  });

  test('example receipt state is a valid state', () => {
    assert.ok(
      CAPABILITY_STATES.includes(receiptExample.state),
      `example state "${receiptExample.state}" not in CAPABILITY_STATES`,
    );
  });

  test('example receipt owner is a valid owner', () => {
    assert.ok(
      CAPABILITY_OWNERS.includes(receiptExample.owner),
      `example owner "${receiptExample.owner}" not in CAPABILITY_OWNERS`,
    );
  });
});

// ── enabling ─────────────────────────────────────────────────────────────────

describe('enabling a capability', () => {
  test('state transitions: declared → enabled', () => {
    const ledger = new CapabilityLedger();
    ledger.declare('pdf-viewer', 'runtime');
    assert.equal(ledger.getState('pdf-viewer'), 'declared');

    ledger.enable('pdf-viewer', 'runtime', 'policy:allow-pdf:v1', ['config:pdf:on']);
    assert.equal(ledger.getState('pdf-viewer'), 'enabled');
    assert.equal(ledger.isEnabled('pdf-viewer'), true);
  });

  test('receipt has correct fields after enable', () => {
    const ledger = new CapabilityLedger();
    ledger.enable('pdf-viewer', 'runtime', 'policy:allow-pdf:v1', ['config:pdf:on']);
    const receipt = ledger.getReceipt('pdf-viewer');

    assert.equal(receipt.capabilityId, 'pdf-viewer');
    assert.equal(receipt.state, 'enabled');
    assert.equal(receipt.owner, 'runtime');
    assert.equal(receipt.policyDecisionRef, 'policy:allow-pdf:v1');
    assert.deepEqual(receipt.evidenceRefs, ['config:pdf:on']);
    assert.ok(typeof receipt.timestamp === 'string');
  });

  test('isEnabled returns false before enable', () => {
    const ledger = new CapabilityLedger();
    ledger.declare('feature-x', 'UI');
    assert.equal(ledger.isEnabled('feature-x'), false);
  });

  test('isEnabled returns false for unknown capability', () => {
    const ledger = new CapabilityLedger();
    assert.equal(ledger.isEnabled('unknown'), false);
  });
});

// ── denying ──────────────────────────────────────────────────────────────────

describe('denying a capability via policy', () => {
  test('state is blocked_by_policy after deny', () => {
    const ledger = new CapabilityLedger();
    ledger.declare('restricted-feature', 'policy');
    ledger.deny('restricted-feature', 'policy', 'policy:deny-restricted:v2', ['audit:policy-log:42']);

    assert.equal(ledger.getState('restricted-feature'), 'blocked_by_policy');
    assert.equal(ledger.isEnabled('restricted-feature'), false);
  });

  test('receipt records policyDecisionRef and evidenceRefs', () => {
    const ledger = new CapabilityLedger();
    ledger.deny('feature-y', 'policy', 'policy:deny-feature-y:v1', ['log:entry:99']);
    const receipt = ledger.getReceipt('feature-y');

    assert.equal(receipt.policyDecisionRef, 'policy:deny-feature-y:v1');
    assert.deepEqual(receipt.evidenceRefs, ['log:entry:99']);
  });
});

// ── unsupported by runtime ───────────────────────────────────────────────────

describe('unsupported by runtime', () => {
  test('state is unsupported_by_runtime', () => {
    const ledger = new CapabilityLedger();
    ledger.setUnsupportedByRuntime('webgpu', 'runtime', ['runtime:version:1.0.0']);

    assert.equal(ledger.getState('webgpu'), 'unsupported_by_runtime');
    assert.equal(ledger.isEnabled('webgpu'), false);
  });

  test('evidenceRefs are recorded', () => {
    const ledger = new CapabilityLedger();
    ledger.setUnsupportedByRuntime('webgpu', 'runtime', ['runtime:caps:no-webgpu']);
    assert.deepEqual(ledger.getReceipt('webgpu').evidenceRefs, ['runtime:caps:no-webgpu']);
  });
});

// ── unsupported by server ────────────────────────────────────────────────────

describe('unsupported by server', () => {
  test('state is unsupported_by_server', () => {
    const ledger = new CapabilityLedger();
    ledger.setUnsupportedByServer('live-collab', 'server', ['server:version:0.9']);

    assert.equal(ledger.getState('live-collab'), 'unsupported_by_server');
    assert.equal(ledger.isEnabled('live-collab'), false);
  });
});

// ── missing plugin ───────────────────────────────────────────────────────────

describe('missing plugin', () => {
  test('state is missing_plugin', () => {
    const ledger = new CapabilityLedger();
    ledger.setMissingPlugin('ink-sign', 'plugin', ['plugin:ink-renderer:not-installed']);

    assert.equal(ledger.getState('ink-sign'), 'missing_plugin');
    assert.equal(ledger.isEnabled('ink-sign'), false);
  });

  test('receipt records evidenceRefs for missing plugin', () => {
    const ledger = new CapabilityLedger();
    ledger.setMissingPlugin('ink-sign', 'plugin', ['plugin:ink-renderer:not-installed']);
    const receipt = ledger.getReceipt('ink-sign');
    assert.deepEqual(receipt.evidenceRefs, ['plugin:ink-renderer:not-installed']);
  });
});

// ── missing schema ───────────────────────────────────────────────────────────

describe('missing schema', () => {
  test('state is missing_schema', () => {
    const ledger = new CapabilityLedger();
    ledger.setMissingSchema('doc-export', 'runtime', ['schema:export-v2:not-found']);

    assert.equal(ledger.getState('doc-export'), 'missing_schema');
    assert.equal(ledger.isEnabled('doc-export'), false);
  });
});

// ── failed reconciliation ────────────────────────────────────────────────────

describe('failed reconciliation', () => {
  test('state is failed', () => {
    const ledger = new CapabilityLedger();
    ledger.fail('pdf-sign', 'runtime', ['error:load:timeout']);

    assert.equal(ledger.getState('pdf-sign'), 'failed');
    assert.equal(ledger.isEnabled('pdf-sign'), false);
  });

  test('reconcile reports failed capability as pending', () => {
    const ledger = new CapabilityLedger();
    ledger.enable('cap-a', 'runtime');
    ledger.fail('cap-b', 'runtime', []);

    const { enabled, pending } = ledger.reconcile();
    assert.ok(enabled.includes('cap-a'));
    assert.ok(pending.includes('cap-b'));
  });

  test('reconcile returns all enabled capabilities', () => {
    const ledger = new CapabilityLedger();
    ledger.enable('cap-a', 'runtime');
    ledger.enable('cap-b', 'runtime');

    const { enabled, pending } = ledger.reconcile();
    assert.deepEqual(enabled.sort(), ['cap-a', 'cap-b']);
    assert.deepEqual(pending, []);
  });
});

// ── conflict warnings ────────────────────────────────────────────────────────

describe('conflict warnings', () => {
  test('logConflict appends warning to existing receipt', () => {
    const ledger = new CapabilityLedger();
    ledger.declare('cap-conflict', 'runtime');
    ledger.logConflict('cap-conflict', 'UI claims enabled but runtime reports unsupported');

    const receipt = ledger.getReceipt('cap-conflict');
    assert.equal(receipt.conflictWarnings.length, 1);
    assert.equal(receipt.conflictWarnings[0], 'UI claims enabled but runtime reports unsupported');
  });

  test('logConflict creates a receipt for an unknown capability', () => {
    const ledger = new CapabilityLedger();
    ledger.logConflict('ghost-cap', 'claimed by UI but never declared');

    const receipt = ledger.getReceipt('ghost-cap');
    assert.ok(receipt);
    assert.equal(receipt.conflictWarnings.length, 1);
  });

  test('conflicting emit preserves prior conflict warnings', () => {
    const ledger = new CapabilityLedger();
    ledger.declare('cap-x', 'runtime');
    ledger.logConflict('cap-x', 'warning 1');
    ledger.enable('cap-x', 'runtime');

    const receipt = ledger.getReceipt('cap-x');
    assert.equal(receipt.state, 'enabled');
    assert.ok(receipt.conflictWarnings.includes('warning 1'));
  });

  test('reconcile includes conflicted capabilities', () => {
    const ledger = new CapabilityLedger();
    ledger.enable('cap-conflict', 'runtime');
    ledger.logConflict('cap-conflict', 'server disagrees');

    const { conflicted } = ledger.reconcile();
    assert.ok(conflicted.includes('cap-conflict'));
  });
});

// ── getAll ───────────────────────────────────────────────────────────────────

describe('getAll', () => {
  test('returns all tracked receipts', () => {
    const ledger = new CapabilityLedger();
    ledger.enable('a', 'runtime');
    ledger.deny('b', 'policy', null, []);

    const all = ledger.getAll();
    assert.equal(all.length, 2);
    assert.ok(all.find(r => r.capabilityId === 'a'));
    assert.ok(all.find(r => r.capabilityId === 'b'));
  });
});

// ── receipt timestamp ────────────────────────────────────────────────────────

describe('receipt timestamp', () => {
  test('timestamp is a valid ISO-8601 date string', () => {
    const ledger = new CapabilityLedger();
    ledger.enable('ts-test', 'runtime');
    const receipt = ledger.getReceipt('ts-test');
    const parsed = new Date(receipt.timestamp);
    assert.ok(!isNaN(parsed.getTime()), 'timestamp is not a valid date');
  });
});

// ── invalid inputs ───────────────────────────────────────────────────────────

describe('invalid inputs', () => {
  test('throws on invalid state', () => {
    const ledger = new CapabilityLedger();
    assert.throws(
      () => ledger._emit('cap', 'invalid_state', 'runtime'),
      /Invalid capability state/,
    );
  });

  test('throws on invalid owner', () => {
    const ledger = new CapabilityLedger();
    assert.throws(
      () => ledger._emit('cap', 'enabled', 'unknown-owner'),
      /Invalid capability owner/,
    );
  });
});

// ── full lifecycle ───────────────────────────────────────────────────────────

describe('full lifecycle', () => {
  test('declared → requested → negotiating → available → enabled', () => {
    const ledger = new CapabilityLedger();
    const id = 'feature-lifecycle';

    ledger.declare(id, 'UI');
    assert.equal(ledger.getState(id), 'declared');

    ledger.request(id, 'runtime');
    assert.equal(ledger.getState(id), 'requested');

    ledger.negotiate(id, 'server');
    assert.equal(ledger.getState(id), 'negotiating');

    ledger.setAvailable(id, 'runtime');
    assert.equal(ledger.getState(id), 'available');

    ledger.enable(id, 'policy', 'policy:allow:v1', ['evidence:1']);
    assert.equal(ledger.getState(id), 'enabled');
    assert.equal(ledger.isEnabled(id), true);
  });

  test('degraded state does not count as enabled', () => {
    const ledger = new CapabilityLedger();
    ledger.degrade('degrade-test', 'runtime', ['perf:low']);
    assert.equal(ledger.isEnabled('degrade-test'), false);
  });
});
