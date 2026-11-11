// Shapes of the JSON files written by scripts/export_web_data.py.
// Every file carries `available`; when false the UI shows a "data not available" state.

export interface Avail {
  available: boolean;
}

export interface SourceData extends Avail {
  kind?: "real" | "synthetic" | string;
  lines?: string[];
}

export interface PriceSeries {
  ticker: string;
  dates: string[];
  close: number[];
}

export interface PriceBank {
  bank_id: number;
  name: string | null;
  sector: string | null;
  start: string;
  end: string;
  n_rows: number;
  series: PriceSeries[];
}

export interface PricesData extends Avail {
  n_tickers: number;
  n_trading_days: number;
  start: string;
  end: string;
  banks: PriceBank[];
}

export interface SplitStats {
  n_samples: number;
  mean: number;
  std: number;
  skewness: number;
  kurtosis: number;
  min: number;
  max: number;
}

export interface BankInfo {
  bank_id: number;
  name: string | null;
  sector: string | null;
  tickers: string[];
  period: [string | null, string | null];
  description: string | null;
  correlation_type: string | null;
  vol_scale: number | null;
  regime_switch: boolean | null;
  n_sequences: { train?: number; val?: number; test?: number };
  statistics: { train?: SplitStats; val?: SplitStats; test?: SplitStats };
}

export interface BanksData extends Avail {
  sequence_length: number;
  banks: BankInfo[];
}

export interface RoundRow {
  round: number;
  n_results?: number | null;
  n_failures?: number | null;
  train_loss?: number | null;
  val_loss?: number | null;
  [k: string]: number | null | undefined | boolean;
}

export interface StrategyRun {
  run_id: string;
  mu: number | null;
  n_clients: number | null;
  n_rounds: number | null;
  use_masking: boolean | null;
  local_epochs: number | null;
  rounds: RoundRow[];
}

export interface FederatedData extends Avail {
  strategies: Partial<Record<"fedavg" | "fedprox", StrategyRun>>;
}

export type ModelKey = "local" | "garch" | "centralized" | "fedavg" | "fedprox" | "zero";

export interface MetricRow {
  key: ModelKey;
  name: string;
  scope: "pooled" | "bank";
  bank_id: number | null;
  n: number;
  mse: number | null;
  mae: number | null;
  rmse: number | null;
  var_95_error: number | null;
  var_99_error: number | null;
  kurtosis_error: number | null;
  skewness_error: number | null;
  acf_error: number | null;
  ks_statistic: number | null;
  wasserstein_distance: number | null;
  direction_accuracy: number | null;
}

export interface ResultsData extends Avail {
  metrics: string[];
  rows: MetricRow[];
  models: Partial<Record<ModelKey, { label: string; description: string }>>;
  federated_runs: Partial<Record<"fedavg" | "fedprox", string>>;
  evaluate_py: Record<string, string | number | null>[] | null;
  n_test_pooled: number;
}

export interface PredictionBank {
  bank_id: number;
  name: string | null;
  actual: number[];
  dates: string[] | null;
  tickers: string[] | null;
  models: Partial<Record<ModelKey, number[]>>;
}

export interface PredictionsData extends Avail {
  labels: Partial<Record<ModelKey, string>>;
  banks: PredictionBank[];
}

export interface MaskingBank {
  bank_id: number;
  num_examples: number;
  n_train: number;
  real: number[];
  weighted: number[];
  masked: number[];
  masked_rel_distance: number;
}

export interface MaskingData extends Avail {
  source: string;
  server_round: number;
  mask_scale: number;
  n_values_total: number;
  n_values_shown: number;
  value_labels: string[];
  banks: MaskingBank[];
  total_examples: number;
  plain_avg: number[];
  masked_avg: number[];
  plain_sum: number[];
  masked_sum: number[];
  max_abs_diff_avg: number;
  max_abs_diff_sum: number;
}

export interface Comparison {
  vs_centralized_pct: number | null;
  vs_local_ensemble_pct: number | null;
  vs_zero_pct: number | null;
  vs_garch_pct: number | null;
}

export interface SummaryData extends Avail {
  best_federated: "fedavg" | "fedprox" | null;
  comparisons: Record<
    string,
    Partial<Record<"fedavg" | "fedprox", Comparison>> & {
      centralized_vs_zero_pct?: number | null;
      local_vs_zero_pct?: number | null;
    }
  >;
  rounds: Partial<Record<"fedavg" | "fedprox", { n_rounds: number; all_results: boolean | null; total_failures: number | null }>>;
}

export interface CodeStep {
  title: string;
  command: string;
  file: string;
  symbols: string[];
  code: string;
}

export interface CodeData extends Avail {
  steps: Record<string, CodeStep>;
}

export interface SettingsData extends Avail {
  project: string;
  title?: string;
  team?: string | null;
  config: {
    data: { n_banks: number; sequence_length: number; train_ratio: number; val_ratio: number; test_ratio: number };
    model: { embed_dim: number; n_heads: number; n_layers: number; ff_dim: number; dropout: number };
    federated: { n_rounds: number; strategy: string; mu: number; min_fit_clients: number };
    training: { batch_size: number; local_epochs: number; lr: number; loss_type: string };
    random_seed: number;
  };
  n_parameters?: number | null;
}

export interface ManifestData extends Avail {
  generated_at: string;
  files: Record<string, boolean>;
}

export interface DataFiles {
  "source.json": SourceData;
  "prices.json": PricesData;
  "banks.json": BanksData;
  "federated.json": FederatedData;
  "results.json": ResultsData;
  "predictions.json": PredictionsData;
  "masking.json": MaskingData;
  "summary.json": SummaryData;
  "code.json": CodeData;
  "settings.json": SettingsData;
  "manifest.json": ManifestData;
}
export type DataFile = keyof DataFiles;
