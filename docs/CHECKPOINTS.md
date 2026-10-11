# Hardening checkpoints

Historical development notes, newest first. Each stage has its own document.

| Stage | Focus | Document |
| --- | --- | --- |
| 7 | Session-aware DAY modeling: explicit broker calendar, regular-session fills, visible DAY-protection expiry, read-only calendar export (255 offline tests) | [STAGE7_SESSIONS_EL.md](STAGE7_SESSIONS_EL.md) |
| Data | Read-only historical-data exporter | [DOWNLOAD_RESEARCH_DATA_EL.md](DOWNLOAD_RESEARCH_DATA_EL.md) |
| 4 | Unified offline fixed-rule evaluation: non-overlapping windows, baselines, volume-gate ablation | [STAGE4_RESEARCH_EL.md](STAGE4_RESEARCH_EL.md), [migration](MIGRATION_STAGE4_EL.md) |
| 3 | Data providers and an independent ledger-backed crypto exit supervisor (194 offline tests) | [STAGE3_DATA_EXITS_EL.md](STAGE3_DATA_EXITS_EL.md), [migration](MIGRATION_STAGE3_EL.md) |
| 2 | Durable SQLite execution ledger and broker reconciliation | [STAGE2_EXECUTION_EL.md](STAGE2_EXECUTION_EL.md), [migration](MIGRATION_STAGE2_EL.md) |
| 1 | Monitoring-first hardening: entries locked by default, crypto entries and ML overlays disabled | [HARDENING_STATUS_EL.md](HARDENING_STATUS_EL.md), [migration](MIGRATION_STAGE1_EL.md) |

Across all stages: no profitability claim, no broker-integration validation and no unattended live trading. The legacy research CLIs now require `--calendar` or an explicit `--legacy-all-sessions`.
