-- Superforecaster Database Schema
-- 3-table design optimized for hackathon speed

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Sessions table: Core forecast sessions
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) NOT NULL DEFAULT 'binary',
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    current_phase VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    prediction_result JSONB,
    total_cost_tokens INTEGER DEFAULT 0
);

CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_created_at ON sessions(created_at DESC);

-- Agent logs table: Real-time agent execution tracking
CREATE TABLE IF NOT EXISTS agent_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    phase VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    output_data JSONB,
    error_message TEXT,
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_agent_logs_session ON agent_logs(session_id, created_at DESC);
CREATE INDEX idx_agent_logs_phase ON agent_logs(phase);

-- Factors table: Discovered and researched factors
CREATE TABLE IF NOT EXISTS factors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    importance_score DECIMAL(4, 2),
    research_summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_factors_session ON factors(session_id);
CREATE INDEX idx_factors_importance ON factors(session_id, importance_score DESC);

-- Enable Realtime for all tables
ALTER PUBLICATION supabase_realtime ADD TABLE sessions;
ALTER PUBLICATION supabase_realtime ADD TABLE agent_logs;
ALTER PUBLICATION supabase_realtime ADD TABLE factors;

-- Comments for documentation
COMMENT ON TABLE sessions IS 'Forecast sessions with questions and predictions';
COMMENT ON TABLE agent_logs IS 'Real-time agent execution logs for monitoring';
COMMENT ON TABLE factors IS 'Discovered factors with importance scores and research';
