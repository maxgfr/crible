# Traceability matrix

| FR | NFRs | ADRs | Entities | Interfaces | Components | Screens |
|---|---|---|---|---|---|---|
| FR-001 | NFR-003, NFR-005, NFR-009, NFR-010 | 0001, 0003 | Company | CLI | — | — |
| FR-002 | NFR-003, NFR-005, NFR-007, NFR-009 | 0001, 0003, 0004 | RawStatement, PriceBar, CrawlTask, Provider | CLI, Provider Plugin API | Status Dashboard | Ingest & coverage status |
| FR-003 | NFR-001, NFR-010, NFR-012 | 0001, 0003 | SnapshotRow | CLI | — | — |
| FR-004 | NFR-001, NFR-008, NFR-011 | 0001, 0003 | SnapshotRow, Preset | CLI, HTTP API | Query Bar (DSL editor), Results Grid | Screener |
| FR-005 | NFR-004, NFR-005 | 0001 | SnapshotRow | CLI | — | — |
| FR-006 | NFR-001, NFR-002, NFR-008 | 0001, 0002 | SnapshotRow, Preset, Company | HTTP API | Status Dashboard, Feedback & Notifications, Empty & Error States | Ingest & coverage status |
| FR-007 | NFR-001, NFR-004, NFR-008 | 0001 | SnapshotRow, Company | Web App, HTTP API | App Shell & Navigation, Query Bar (DSL editor), Results Grid, Column Picker, Presets Menu, Company Detail Drawer, Export Button, Feedback & Notifications, Empty & Error States | Screener |
| FR-008 | NFR-003, NFR-006, NFR-009, NFR-013 | 0001, 0002, 0003 | Provider | HTTP API, CLI | — | — |
| FR-009 | NFR-004, NFR-010 | 0002 | Preset | HTTP API, Web App, CLI | Presets Menu | Screener |
| FR-010 | NFR-003, NFR-005, NFR-010 | 0003, 0004 | RawStatement, Company | Provider Plugin API | Company Detail Drawer | Company detail |
| FR-011 | NFR-003, NFR-005 | 0004 | PriceBar, Provider | Provider Plugin API | — | — |
| FR-012 | NFR-004, NFR-010 | 0002 | Company, SnapshotRow, RawStatement | Web App, HTTP API | Company Detail Drawer, Empty & Error States | Company detail |
| FR-013 | NFR-006, NFR-009, NFR-012 | 0002, 0003 | Provider, RawStatement | Provider Plugin API | Status Dashboard | Ingest & coverage status, Providers & settings |
| FR-014 | NFR-006, NFR-012 | 0002, 0004 | Provider | Provider Plugin API | — | Providers & settings |
