-- Trading System Tables (Minimal)
-- Everyone trades probability of YES (0-100 cents)

-- =============================================================================
-- ENUM TYPES
-- =============================================================================

-- Trader type
CREATE TYPE trader_type AS ENUM ('fundamental', 'noise', 'user');

-- Trader names by type:
--   fundamental: conservative, momentum, historical, balanced, realtime
--   noise: sphere keys from communities.py
--   user: oliver, owen, skylar, tyler
CREATE TYPE trader_name AS ENUM (
    -- Fundamental traders
    'conservative', 'momentum', 'historical', 'balanced', 'realtime',
    -- Noise traders (spheres)
    'eacc_sovereign', 'america_first', 'blue_establishment', 'progressive_left',
    'optimizer_idw', 'fintwit_market', 'builder_engineering', 'academic_research', 'osint_intel',
    -- User traders
    'oliver', 'owen', 'skylar', 'tyler'
);

CREATE TYPE order_side AS ENUM ('buy', 'sell');
CREATE TYPE order_status AS ENUM ('open', 'filled', 'partially_filled', 'cancelled');


-- =============================================================================
-- TABLE 1: LIVE TRADER STATE (prompts + positions)
-- =============================================================================

CREATE TABLE IF NOT EXISTS trader_state_live (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    trader_type trader_type NOT NULL,
    name trader_name NOT NULL,
    system_prompt TEXT,
    -- Position & P/L
    position INTEGER NOT NULL DEFAULT 0,  -- Positive = long, negative = short
    pnl DECIMAL(12, 2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(session_id, name)
);

CREATE INDEX idx_trader_state_live_session ON trader_state_live(session_id);
CREATE INDEX idx_trader_state_live_type ON trader_state_live(session_id, trader_type);


-- =============================================================================
-- TABLE 2: HISTORICAL TRADER SYSTEM PROMPTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS trader_prompts_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    trader_type trader_type NOT NULL,
    name trader_name NOT NULL,
    prompt_number INTEGER NOT NULL,
    system_prompt TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(session_id, name, prompt_number)
);

CREATE INDEX idx_trader_prompts_history_session ON trader_prompts_history(session_id);


-- =============================================================================
-- TABLE 3: LIVE ORDER BOOK
-- =============================================================================

CREATE TABLE IF NOT EXISTS orderbook_live (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    trader_name trader_name NOT NULL,
    side order_side NOT NULL,
    price INTEGER NOT NULL CHECK (price >= 0 AND price <= 100),
    quantity INTEGER NOT NULL DEFAULT 1,
    filled_quantity INTEGER NOT NULL DEFAULT 0,
    status order_status NOT NULL DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_orderbook_live_session ON orderbook_live(session_id);
CREATE INDEX idx_orderbook_live_price ON orderbook_live(session_id, side, price);
CREATE INDEX idx_orderbook_live_trader_status ON orderbook_live(session_id, trader_name, status);


-- =============================================================================
-- TABLE 4: HISTORICAL ORDER BOOK
-- =============================================================================

CREATE TABLE IF NOT EXISTS orderbook_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    trader_name trader_name NOT NULL,
    side order_side NOT NULL,
    price INTEGER NOT NULL CHECK (price >= 0 AND price <= 100),
    quantity INTEGER NOT NULL,
    filled_quantity INTEGER NOT NULL DEFAULT 0,
    status order_status NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_orderbook_history_session ON orderbook_history(session_id);


-- =============================================================================
-- TABLE 5: TRADES
-- =============================================================================

CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    buyer_name trader_name NOT NULL,
    seller_name trader_name NOT NULL,
    price INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_trades_session ON trades(session_id);


-- =============================================================================
-- ENABLE REALTIME
-- =============================================================================

ALTER PUBLICATION supabase_realtime ADD TABLE trader_state_live;
ALTER PUBLICATION supabase_realtime ADD TABLE orderbook_live;
ALTER PUBLICATION supabase_realtime ADD TABLE trades;
