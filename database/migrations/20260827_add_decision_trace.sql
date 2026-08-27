-- Backward-compatible persistence for explainable automated decisions.
ALTER TABLE decisions ADD COLUMN IF NOT EXISTS decision_trace JSONB;
