# StoreMemory token comparison (2026-11-27)

Method: tiktoken cl100k_base; three retrieval runs per task, averaged.

| Task | Full tokens | Retrieved tokens (avg) | Saved | Savings |
|---|---:|---:|---:|---:|
| topic_recommendation | 871 | 358 | 513 | 58.9% |
| copy_draft | 880 | 230 | 650 | 73.86% |
| review_conclusion | 872 | 328 | 544 | 62.39% |
| **Average** | **874.33** | **305.33** | **569.0** | **65.08%** |

Synthetic PawCare Demo Clinic data only. The full prompt contains the whole synthetic dataset; the retrieved prompt contains Meko memory snippets filtered by metadata kind for the task.
