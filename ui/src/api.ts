// FR-007 — compatibility shim: the implementation lives in data/api-client
// (see data/index.ts for the api/static seam). Kept so existing imports and
// tests keep working; new code should import from "./data".

export {
  apiClient,
  company,
  exportCsvUrl,
  presets,
  providers,
  screen,
  search,
  status,
} from "./data/api-client";
export { DslApiError } from "./data/types";
export type {
  CompanyDetail,
  DslErrorDetail,
  IngestHeartbeat,
  Preset,
  ProviderInfo,
  ScreenResponse,
  SearchHit,
  StatusResponse,
} from "./data/types";
