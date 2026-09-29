/* Generated from contracts/foundation-v1.schema.json. Do not edit. */

/**
 * Transport shape only. No order authority. UTC milliseconds; money and quantity use bounded decimal strings.
 */
export type FoundationEnvelope =
  | {
      schema_version: "1.0.0";
      event_id: ID;
      correlation_id: ID;
      occurred_at_ms: Timestamp;
      mode: Mode;
      tenant_id?: ID;
      account_id?: ID;
      source: {
        kind: "FOUNDATION" | "FIXTURE";
        name: string;
      };
      event_type: "HEALTH";
      payload: Health;
    }
  | {
      schema_version: "1.0.0";
      event_id: ID;
      correlation_id: ID;
      occurred_at_ms: Timestamp;
      mode: Mode;
      tenant_id?: ID;
      account_id?: ID;
      source: {
        kind: "FOUNDATION" | "FIXTURE";
        name: string;
      };
      event_type: "ERROR";
      payload: Error;
    }
  | {
      schema_version: "1.0.0";
      event_id: ID;
      correlation_id: ID;
      occurred_at_ms: Timestamp;
      mode: Mode;
      tenant_id?: ID;
      account_id?: ID;
      source: {
        kind: "FOUNDATION" | "FIXTURE";
        name: string;
      };
      event_type: "INSTRUMENT";
      payload: Instrument;
    }
  | {
      schema_version: "1.0.0";
      event_id: ID;
      correlation_id: ID;
      occurred_at_ms: Timestamp;
      mode: Mode;
      tenant_id?: ID;
      account_id?: ID;
      source: {
        kind: "FOUNDATION" | "FIXTURE";
        name: string;
      };
      event_type: "FORECAST";
      payload: Forecast;
    }
  | {
      schema_version: "1.0.0";
      event_id: ID;
      correlation_id: ID;
      occurred_at_ms: Timestamp;
      mode: Mode;
      tenant_id: ID;
      account_id: ID;
      source: {
        kind: "FOUNDATION" | "FIXTURE";
        name: string;
      };
      event_type: "POSITION_INTENT";
      payload: PositionIntent;
    }
  | {
      schema_version: "1.0.0";
      event_id: ID;
      correlation_id: ID;
      occurred_at_ms: Timestamp;
      mode: Mode;
      tenant_id: ID;
      account_id: ID;
      source: {
        kind: "FOUNDATION" | "FIXTURE";
        name: string;
      };
      event_type: "EXECUTION_EVENT";
      payload: ExecutionEvent;
    }
  | {
      schema_version: "1.0.0";
      event_id: ID;
      correlation_id: ID;
      occurred_at_ms: Timestamp;
      mode: Mode;
      tenant_id: ID;
      account_id: ID;
      source: {
        kind: "FOUNDATION" | "FIXTURE";
        name: string;
      };
      event_type: "CREDENTIAL_METADATA";
      payload: CredentialMetadata;
    }
  | {
      schema_version: "1.0.0";
      event_id: ID;
      correlation_id: ID;
      occurred_at_ms: Timestamp;
      mode: Mode;
      tenant_id?: ID;
      account_id?: ID;
      source: {
        kind: "FOUNDATION" | "FIXTURE";
        name: string;
      };
      event_type: "PING";
      payload: Ping;
    };
export type ID = string;
export type Timestamp = number;
export type Mode = "REPLAY" | "PAPER" | "TESTNET" | "SHADOW" | "LIVE";
export type Decimal = string;

export interface Health {
  service: "control-api" | "trading-core";
  status: "UP" | "READY" | "NOT_READY";
  profile: "FOUNDATION";
  trading_enabled: false;
  dependencies: {
    core: "UP" | "DOWN" | "NOT_REQUIRED";
    mongodb: "UP" | "DOWN" | "NOT_REQUIRED";
    redis: "UP" | "DOWN" | "NOT_REQUIRED";
  };
}
export interface Error {
  code:
    | "INVALID_REQUEST"
    | "NOT_FOUND"
    | "METHOD_NOT_ALLOWED"
    | "TOO_LARGE"
    | "TIMEOUT"
    | "OVERLOADED"
    | "INTERNAL"
    | "NOT_READY";
  message:
    | "Request rejected"
    | "Route is unavailable"
    | "Method is unavailable"
    | "Request exceeds limit"
    | "Request timed out"
    | "Service is busy"
    | "Internal failure"
    | "Dependencies unavailable";
}
export interface Instrument {
  venue: "BINANCE";
  symbol: string;
  contract_type: "PERPETUAL";
  margin_asset: "USDT";
}
export interface Forecast {
  instrument: Instrument;
  horizon_seconds: number;
  outcome_at_ms: Timestamp;
  probabilities: {
    up: number;
    down: number;
    range: number;
  };
  expected_return: Decimal;
  uncertainty: Decimal;
  versions: Versions;
}
export interface Versions {
  model: string;
  data: string;
  config: string;
  features: string;
}
export interface PositionIntent {
  intent_id: ID;
  instrument: Instrument;
  action: "HOLD" | "REDUCE" | "TAKE_PROFIT" | "CLOSE" | "FLAT" | "NO_TRADE" | "REVERSE" | "OPEN";
  quantity: Decimal;
  versions: Versions;
}
export interface ExecutionEvent {
  intent_id: ID;
  state: "INTENT_DURABLE" | "UNKNOWN" | "ACKNOWLEDGED" | "PARTIALLY_FILLED" | "FILLED" | "CANCELED" | "REJECTED";
  quantity: Decimal;
  price: Decimal;
  versions: Versions;
}
export interface CredentialMetadata {
  credential_id: ID;
  provider: "BINANCE";
  status: "DISCONNECTED" | "UNVERIFIED" | "CONNECTED" | "REVOKED";
  key_version: number;
  display_label: string;
}
export interface Ping {
  message: "PING";
}
