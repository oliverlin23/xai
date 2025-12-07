-- Migration: Add separate columns for prediction_probability, confidence, and total_duration_seconds
-- This allows easier querying and analysis without parsing JSONB

-- Add new columns to sessions table
ALTER TABLE sessions 
ADD COLUMN IF NOT EXISTS prediction_probability DECIMAL(5, 4),
ADD COLUMN IF NOT EXISTS confidence DECIMAL(5, 4),
ADD COLUMN IF NOT EXISTS total_duration_seconds DECIMAL(10, 2);

-- Add comments for documentation
COMMENT ON COLUMN sessions.prediction_probability IS 'Probability of the event occurring (0.0-1.0)';
COMMENT ON COLUMN sessions.confidence IS 'Confidence in the probability estimate, based on evidence quality (0.0-1.0)';
COMMENT ON COLUMN sessions.total_duration_seconds IS 'Total execution time for the forecast session in seconds';

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sessions_prediction_probability ON sessions(prediction_probability);
CREATE INDEX IF NOT EXISTS idx_sessions_confidence ON sessions(confidence);
CREATE INDEX IF NOT EXISTS idx_sessions_duration ON sessions(total_duration_seconds);

-- Migrate existing data from prediction_result JSONB (if any exists)
-- This is a one-time migration for existing records
UPDATE sessions
SET 
    prediction_probability = (prediction_result->>'prediction_probability')::DECIMAL(5, 4),
    confidence = (prediction_result->>'confidence')::DECIMAL(5, 4),
    total_duration_seconds = (prediction_result->>'total_duration_seconds')::DECIMAL(10, 2)
WHERE 
    prediction_result IS NOT NULL
    AND (
        prediction_result ? 'prediction_probability' 
        OR prediction_result ? 'confidence'
        OR prediction_result ? 'total_duration_seconds'
    )
    AND (
        prediction_probability IS NULL 
        OR confidence IS NULL 
        OR total_duration_seconds IS NULL
    );

-- For backward compatibility: if prediction_probability is NULL but confidence exists in JSONB,
-- use confidence as prediction_probability (old format)
UPDATE sessions
SET prediction_probability = (prediction_result->>'confidence')::DECIMAL(5, 4)
WHERE 
    prediction_result IS NOT NULL
    AND prediction_result ? 'confidence'
    AND prediction_probability IS NULL
    AND (prediction_result->>'confidence')::DECIMAL(5, 4) IS NOT NULL;

