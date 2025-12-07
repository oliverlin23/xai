-- Migration: Refactor to support multiple forecaster responses per session
-- A session can now have multiple forecaster responses (one per personality/class)
-- This allows comparing different forecasting approaches for the same question

-- =============================================================================
-- STEP 1: Create forecaster_responses table
-- =============================================================================

CREATE TABLE IF NOT EXISTS forecaster_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    forecaster_class VARCHAR(50) NOT NULL,  -- e.g., 'conservative', 'momentum', 'balanced', etc.
    prediction_result JSONB,  -- Full prediction output (prediction, reasoning, key_factors, etc.)
    prediction_probability DECIMAL(5, 4),  -- Probability of event (0.0-1.0)
    confidence DECIMAL(5, 4),  -- Confidence in probability estimate (0.0-1.0)
    total_duration_seconds DECIMAL(10, 2),  -- Total execution time in seconds
    total_duration_formatted VARCHAR(50),  -- Human-readable duration (e.g., "2m 30s")
    phase_durations JSONB,  -- Duration breakdown by phase
    status VARCHAR(50) NOT NULL DEFAULT 'running',  -- running, completed, failed
    error_message TEXT,  -- Error message if failed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(session_id, forecaster_class)  -- One response per forecaster class per session
);

-- Indexes for common queries
CREATE INDEX idx_forecaster_responses_session ON forecaster_responses(session_id);
CREATE INDEX idx_forecaster_responses_class ON forecaster_responses(forecaster_class);
CREATE INDEX idx_forecaster_responses_status ON forecaster_responses(status);
CREATE INDEX idx_forecaster_responses_probability ON forecaster_responses(prediction_probability);
CREATE INDEX idx_forecaster_responses_confidence ON forecaster_responses(confidence);

-- Comments for documentation
COMMENT ON TABLE forecaster_responses IS 'Individual forecaster responses for a session. One session can have multiple responses from different forecaster classes.';
COMMENT ON COLUMN forecaster_responses.forecaster_class IS 'Forecaster personality/class: conservative, momentum, historical, realtime, balanced';
COMMENT ON COLUMN forecaster_responses.prediction_result IS 'Full prediction output JSONB with prediction, reasoning, key_factors, etc.';
COMMENT ON COLUMN forecaster_responses.prediction_probability IS 'Probability of the event occurring (0.0-1.0)';
COMMENT ON COLUMN forecaster_responses.confidence IS 'Confidence in the probability estimate, based on evidence quality (0.0-1.0)';
COMMENT ON COLUMN forecaster_responses.total_duration_seconds IS 'Total execution time for this forecaster response in seconds';

-- =============================================================================
-- STEP 2: Migrate existing data from sessions to forecaster_responses
-- =============================================================================

-- Migrate existing sessions that have prediction results
-- Use 'balanced' as default forecaster_class for existing data
INSERT INTO forecaster_responses (
    session_id,
    forecaster_class,
    prediction_result,
    prediction_probability,
    confidence,
    total_duration_seconds,
    total_duration_formatted,
    phase_durations,
    status,
    error_message,
    created_at,
    completed_at
)
SELECT 
    id as session_id,
    'balanced' as forecaster_class,  -- Default for existing data
    prediction_result,
    prediction_probability,
    confidence,
    total_duration_seconds,
    CASE 
        WHEN total_duration_seconds IS NOT NULL THEN
            CASE 
                WHEN total_duration_seconds >= 60 THEN
                    FLOOR(total_duration_seconds / 60)::TEXT || 'm ' || 
                    FLOOR(total_duration_seconds % 60)::TEXT || 's'
                ELSE
                    FLOOR(total_duration_seconds)::TEXT || 's'
            END
        ELSE NULL
    END as total_duration_formatted,
    CASE 
        WHEN prediction_result IS NOT NULL AND prediction_result ? 'phase_durations' 
        THEN prediction_result->'phase_durations'
        ELSE NULL
    END as phase_durations,
    status,
    NULL as error_message,  -- Sessions table doesn't have error_message column
    created_at,
    completed_at
FROM sessions
WHERE 
    prediction_result IS NOT NULL 
    OR prediction_probability IS NOT NULL 
    OR confidence IS NOT NULL
    OR total_duration_seconds IS NOT NULL;

-- =============================================================================
-- STEP 3: Drop forecaster-specific columns from sessions table
-- =============================================================================

-- Drop columns that are now in forecaster_responses
ALTER TABLE sessions 
    DROP COLUMN IF EXISTS prediction_result,
    DROP COLUMN IF EXISTS prediction_probability,
    DROP COLUMN IF EXISTS confidence,
    DROP COLUMN IF EXISTS total_duration_seconds;

-- Drop indexes that are no longer needed
DROP INDEX IF EXISTS idx_sessions_prediction_probability;
DROP INDEX IF EXISTS idx_sessions_confidence;
DROP INDEX IF EXISTS idx_sessions_duration;

-- =============================================================================
-- STEP 4: Enable Realtime for new table
-- =============================================================================

ALTER PUBLICATION supabase_realtime ADD TABLE forecaster_responses;

