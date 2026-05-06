/**
 * CapabilityLedger — single source of truth for all capability state.
 *
 * Each capability flag/state change emits a receipt that records:
 *   - capabilityId, state, owner, timestamp
 *   - policyDecisionRef, evidenceRefs, conflictWarnings
 *
 * Reconciliation occurs at runtime startup, on feature toggle, and on
 * plugin load/unload.
 *
 * Aligned with SourceOS-Linux/sourceos-spec#99.
 */

import { CAPABILITY_STATES, CAPABILITY_OWNERS } from './schema.js';

/**
 * @typedef {'declared'|'requested'|'negotiating'|'available'|'enabled'|
 *   'degraded'|'blocked_by_policy'|'unsupported_by_runtime'|
 *   'unsupported_by_server'|'missing_plugin'|'missing_schema'|'failed'} CapabilityState
 */

/**
 * @typedef {'UI'|'runtime'|'server'|'plugin'|'policy'} CapabilityOwner
 */

/**
 * @typedef {Object} CapabilityReceipt
 * @property {string}          capabilityId
 * @property {CapabilityState} state
 * @property {CapabilityOwner} owner
 * @property {string}          timestamp        ISO-8601
 * @property {string|null}     policyDecisionRef
 * @property {string[]}        evidenceRefs
 * @property {string[]}        conflictWarnings
 */

/**
 * @param {string} capabilityId
 * @param {CapabilityState} state
 * @param {CapabilityOwner} owner
 * @param {Partial<Omit<CapabilityReceipt,'capabilityId'|'state'|'owner'|'timestamp'>>} [opts]
 * @returns {CapabilityReceipt}
 */
function buildReceipt(capabilityId, state, owner, opts = {}) {
  if (!CAPABILITY_STATES.includes(state)) {
    throw new TypeError(`Invalid capability state: "${state}"`);
  }
  if (!CAPABILITY_OWNERS.includes(owner)) {
    throw new TypeError(`Invalid capability owner: "${owner}"`);
  }
  return {
    capabilityId,
    state,
    owner,
    timestamp: new Date().toISOString(),
    policyDecisionRef: opts.policyDecisionRef ?? null,
    evidenceRefs: opts.evidenceRefs ?? [],
    conflictWarnings: opts.conflictWarnings ?? [],
  };
}

export class CapabilityLedger {
  constructor() {
    /** @type {Map<string, CapabilityReceipt>} */
    this._receipts = new Map();
  }

  // ── internal helper ──────────────────────────────────────────────────────

  /**
   * Emit and store a receipt, preserving existing conflictWarnings.
   * @param {string} capabilityId
   * @param {CapabilityState} state
   * @param {CapabilityOwner} owner
   * @param {Partial<Omit<CapabilityReceipt,'capabilityId'|'state'|'owner'|'timestamp'>>} [opts]
   * @returns {CapabilityReceipt}
   */
  _emit(capabilityId, state, owner, opts = {}) {
    const existing = this._receipts.get(capabilityId);
    const conflictWarnings = [
      ...(existing?.conflictWarnings ?? []),
      ...(opts.conflictWarnings ?? []),
    ];
    const receipt = buildReceipt(capabilityId, state, owner, {
      ...opts,
      conflictWarnings,
    });
    this._receipts.set(capabilityId, receipt);
    return receipt;
  }

  // ── state-transition methods ─────────────────────────────────────────────

  /** Move capability to "declared" state. */
  declare(capabilityId, owner, opts = {}) {
    return this._emit(capabilityId, 'declared', owner, opts);
  }

  /** Move capability to "requested" state. */
  request(capabilityId, owner, opts = {}) {
    return this._emit(capabilityId, 'requested', owner, opts);
  }

  /** Move capability to "negotiating" state. */
  negotiate(capabilityId, owner, opts = {}) {
    return this._emit(capabilityId, 'negotiating', owner, opts);
  }

  /** Move capability to "available" state. */
  setAvailable(capabilityId, owner, opts = {}) {
    return this._emit(capabilityId, 'available', owner, opts);
  }

  /**
   * Enable a capability.
   * @param {string} capabilityId
   * @param {CapabilityOwner} owner
   * @param {string|null} policyDecisionRef
   * @param {string[]} [evidenceRefs]
   */
  enable(capabilityId, owner, policyDecisionRef = null, evidenceRefs = []) {
    return this._emit(capabilityId, 'enabled', owner, { policyDecisionRef, evidenceRefs });
  }

  /**
   * Deny a capability via policy.
   * @param {string} capabilityId
   * @param {CapabilityOwner} owner
   * @param {string|null} policyDecisionRef
   * @param {string[]} [evidenceRefs]
   */
  deny(capabilityId, owner, policyDecisionRef = null, evidenceRefs = []) {
    return this._emit(capabilityId, 'blocked_by_policy', owner, { policyDecisionRef, evidenceRefs });
  }

  /** Mark capability as degraded. */
  degrade(capabilityId, owner, evidenceRefs = []) {
    return this._emit(capabilityId, 'degraded', owner, { evidenceRefs });
  }

  /** Mark capability as unsupported by the runtime. */
  setUnsupportedByRuntime(capabilityId, owner, evidenceRefs = []) {
    return this._emit(capabilityId, 'unsupported_by_runtime', owner, { evidenceRefs });
  }

  /** Mark capability as unsupported by the server. */
  setUnsupportedByServer(capabilityId, owner, evidenceRefs = []) {
    return this._emit(capabilityId, 'unsupported_by_server', owner, { evidenceRefs });
  }

  /** Mark capability as missing required plugin. */
  setMissingPlugin(capabilityId, owner, evidenceRefs = []) {
    return this._emit(capabilityId, 'missing_plugin', owner, { evidenceRefs });
  }

  /** Mark capability as missing required schema. */
  setMissingSchema(capabilityId, owner, evidenceRefs = []) {
    return this._emit(capabilityId, 'missing_schema', owner, { evidenceRefs });
  }

  /** Mark capability as failed. */
  fail(capabilityId, owner, evidenceRefs = []) {
    return this._emit(capabilityId, 'failed', owner, { evidenceRefs });
  }

  // ── conflict logging ─────────────────────────────────────────────────────

  /**
   * Append a conflict warning to an existing receipt without changing state.
   * Logs the warning and creates a minimal "declared" receipt if none exists.
   * @param {string} capabilityId
   * @param {string} warning
   */
  logConflict(capabilityId, warning) {
    const existing = this._receipts.get(capabilityId);
    if (existing) {
      existing.conflictWarnings.push(warning);
    } else {
      // No receipt yet — create one so the warning is attached.
      this._emit(capabilityId, 'declared', 'runtime', { conflictWarnings: [warning] });
    }
  }

  // ── reconciliation ───────────────────────────────────────────────────────

  /**
   * Reconcile all tracked capabilities.
   *
   * Any capability not yet in "enabled" state is flagged. Conflicts between
   * receipts that claim incompatible states produce logged warnings.
   *
   * Returns a summary object suitable for runtime startup, feature toggle,
   * and plugin load/unload hooks.
   *
   * @returns {{ enabled: string[], pending: string[], conflicted: string[] }}
   */
  reconcile() {
    const enabled = [];
    const pending = [];
    const conflicted = [];

    for (const [capabilityId, receipt] of this._receipts) {
      if (receipt.state === 'enabled') {
        enabled.push(capabilityId);
      } else {
        pending.push(capabilityId);
      }
      if (receipt.conflictWarnings.length > 0) {
        conflicted.push(capabilityId);
      }
    }

    return { enabled, pending, conflicted };
  }

  // ── query methods ────────────────────────────────────────────────────────

  /**
   * Get the current state for a capability.
   * Returns `null` if the capability has not been declared.
   * @param {string} capabilityId
   * @returns {CapabilityState|null}
   */
  getState(capabilityId) {
    return this._receipts.get(capabilityId)?.state ?? null;
  }

  /**
   * Get the full receipt for a capability.
   * Returns `null` if the capability has not been declared.
   * @param {string} capabilityId
   * @returns {CapabilityReceipt|null}
   */
  getReceipt(capabilityId) {
    return this._receipts.get(capabilityId) ?? null;
  }

  /**
   * Return all receipts as an array.
   * @returns {CapabilityReceipt[]}
   */
  getAll() {
    return Array.from(this._receipts.values());
  }

  /**
   * Returns true only when the ledger reports the capability as "enabled".
   * Feature use must be gated on this before proceeding.
   * @param {string} capabilityId
   * @returns {boolean}
   */
  isEnabled(capabilityId) {
    return this.getState(capabilityId) === 'enabled';
  }
}
