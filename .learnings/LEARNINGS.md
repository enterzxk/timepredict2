# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice

---

## 2026-05-14 - Prefer dependency-free smoke tests for fresh local scaffolds

- Category: best_practice
- When creating a new minimal Python project in an unknown local environment, start with `unittest` smoke tests unless the project already declares and installs `pytest`.

