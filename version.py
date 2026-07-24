__version__ = "5.3.0"
VERSION = "5.3.0"

# Semantic Versioning Scheme (v5 — Field Test Phase)
# ===================================================
# v<major>.<minor>.<patch>
#
# MAJOR (vX.0.0): Major Personality Rewrite / Breaking Changes
#   - Complete persona restructure
#   - Breaking prompt format changes
#   - New architecture
#   - Phase transitions (e.g., Field Test → Production)
#
# MINOR (v5.X.0): Feature Release
#   - New persona modules
#   - New capabilities (e.g., cultural knowledge, language expansion)
#   - Evaluation improvements
#   - Dataset additions
#   - Scoring system changes
#   - NO breaking changes to core personality
#
# PATCH (v5.0.X): Behavior Tweak
#   - بهبود شوخی‌های تکراری
#   - بهبود تشخیص احساسات
#   - Bug fixes
#   - Prompt tweaks
#   - Small behavior adjustments
#   - Based on personality_failures.md learnings
#
# Rule: هر بار کل شخصیت را زیر و رو نکن.
# تغییرات کوچک → PATCH. تغییرات جدید → MINOR. بازنویسی → MAJOR.
#
# History:
# v3.0.0 — Architecture Update
# v4.0.0 — Behavior Improvement
# v4.1.0 — Language Expansion
# v5.0.0 — Complete persona restructure + evaluation pack (field test start)
# v5.1.0 — Hallucination Guard, Developer Dashboard, Score Card, Datasets v1, Regression Test
# v5.2.0 — Production Ready: Live Behavior Analytics, User Relationship Model,
#           Character Evolution, Group Personality Modes, Quality Gate, Persona Signature
# v5.3.0 — Architecture Upgrade: Modular prompt (core+contextual+examples tiers),
#           Intelligent Router (intent→provider), Quality-based Failover, Model Benchmark
