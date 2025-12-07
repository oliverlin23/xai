-- Migration: Create order matching SQL function
-- This provides order matching without needing an Edge Function
-- Called directly from Python via: supabase.rpc('match_orders_for_session', {'p_session_id': uuid})

-- =============================================================================
-- ORDER MATCHING FUNCTION (Pure SQL - No Edge Function Required)
-- =============================================================================

-- Function to match orders for a session using price-time priority
CREATE OR REPLACE FUNCTION match_orders_for_session(p_session_id UUID)
RETURNS TABLE(trades_count INT, volume INT)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_trades_count INT := 0;
    v_volume INT := 0;
    v_bid RECORD;
    v_ask RECORD;
    v_fill_qty INT;
    v_exec_price INT;
    v_bid_remaining INT;
    v_ask_remaining INT;
BEGIN
    -- Loop through bids (highest price first, then oldest first)
    FOR v_bid IN 
        SELECT * FROM orderbook_live 
        WHERE session_id = p_session_id 
        AND side = 'buy' 
        AND status IN ('open', 'partially_filled')
        AND quantity > filled_quantity
        ORDER BY price DESC, created_at ASC
    LOOP
        -- Calculate remaining quantity for this bid
        v_bid_remaining := v_bid.quantity - v_bid.filled_quantity;
        
        -- Loop through asks that can match (price <= bid price)
        FOR v_ask IN 
            SELECT * FROM orderbook_live 
            WHERE session_id = p_session_id 
            AND side = 'sell' 
            AND status IN ('open', 'partially_filled')
            AND quantity > filled_quantity
            AND price <= v_bid.price
            AND trader_name != v_bid.trader_name  -- Don't self-trade
            ORDER BY price ASC, created_at ASC
        LOOP
            -- Skip if bid is already fully filled
            IF v_bid_remaining <= 0 THEN
                EXIT;
            END IF;
            
            -- Calculate remaining quantity for this ask
            v_ask_remaining := v_ask.quantity - v_ask.filled_quantity;
            
            -- Calculate fill quantity (minimum of both remaining)
            v_fill_qty := LEAST(v_bid_remaining, v_ask_remaining);
            
            IF v_fill_qty > 0 THEN
                -- Execution price is the resting (ask) order's price (price-time priority)
                v_exec_price := v_ask.price;
                
                -- Insert trade
                INSERT INTO trades (session_id, buyer_name, seller_name, price, quantity)
                VALUES (p_session_id, v_bid.trader_name, v_ask.trader_name, v_exec_price, v_fill_qty);
                
                -- Update bid order
                UPDATE orderbook_live 
                SET filled_quantity = filled_quantity + v_fill_qty,
                    status = CASE 
                        WHEN filled_quantity + v_fill_qty >= quantity THEN 'filled'::order_status
                        ELSE 'partially_filled'::order_status
                    END
                WHERE id = v_bid.id;
                
                -- Update ask order
                UPDATE orderbook_live 
                SET filled_quantity = filled_quantity + v_fill_qty,
                    status = CASE 
                        WHEN filled_quantity + v_fill_qty >= quantity THEN 'filled'::order_status
                        ELSE 'partially_filled'::order_status
                    END
                WHERE id = v_ask.id;
                
                -- Update trader states
                -- Buyer: +position, -cash (price is in cents, convert to dollars)
                INSERT INTO trader_state_live (session_id, trader_type, name, position, cash)
                VALUES (
                    p_session_id,
                    (SELECT 
                        CASE 
                            WHEN v_bid.trader_name IN ('conservative', 'momentum', 'historical', 'balanced', 'realtime') THEN 'fundamental'::trader_type
                            WHEN v_bid.trader_name IN ('eacc_sovereign', 'america_first', 'blue_establishment', 'progressive_left', 'optimizer_idw', 'fintwit_market', 'builder_engineering', 'academic_research', 'osint_intel') THEN 'noise'::trader_type
                            ELSE 'user'::trader_type
                        END
                    ),
                    v_bid.trader_name,
                    v_fill_qty,
                    1000.00 - (v_exec_price * v_fill_qty / 100.0)
                )
                ON CONFLICT (session_id, name) DO UPDATE SET
                    position = trader_state_live.position + v_fill_qty,
                    cash = trader_state_live.cash - (v_exec_price * v_fill_qty / 100.0),
                    updated_at = NOW();
                
                -- Seller: -position, +cash
                INSERT INTO trader_state_live (session_id, trader_type, name, position, cash)
                VALUES (
                    p_session_id,
                    (SELECT 
                        CASE 
                            WHEN v_ask.trader_name IN ('conservative', 'momentum', 'historical', 'balanced', 'realtime') THEN 'fundamental'::trader_type
                            WHEN v_ask.trader_name IN ('eacc_sovereign', 'america_first', 'blue_establishment', 'progressive_left', 'optimizer_idw', 'fintwit_market', 'builder_engineering', 'academic_research', 'osint_intel') THEN 'noise'::trader_type
                            ELSE 'user'::trader_type
                        END
                    ),
                    v_ask.trader_name,
                    -v_fill_qty,
                    1000.00 + (v_exec_price * v_fill_qty / 100.0)
                )
                ON CONFLICT (session_id, name) DO UPDATE SET
                    position = trader_state_live.position - v_fill_qty,
                    cash = trader_state_live.cash + (v_exec_price * v_fill_qty / 100.0),
                    updated_at = NOW();
                
                -- Update counters
                v_trades_count := v_trades_count + 1;
                v_volume := v_volume + v_fill_qty;
                
                -- Update remaining for bid
                v_bid_remaining := v_bid_remaining - v_fill_qty;
            END IF;
        END LOOP;
    END LOOP;
    
    RETURN QUERY SELECT v_trades_count, v_volume;
END;
$$;

-- Grant execute permission to authenticated users and service role
GRANT EXECUTE ON FUNCTION match_orders_for_session(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION match_orders_for_session(UUID) TO service_role;

-- =============================================================================
-- HELPER: Get orderbook snapshot as JSON
-- =============================================================================

CREATE OR REPLACE FUNCTION get_orderbook_snapshot(p_session_id UUID)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_result JSON;
BEGIN
    SELECT json_build_object(
        'session_id', p_session_id,
        'bids', COALESCE((
            SELECT json_agg(json_build_object(
                'price', price,
                'quantity', SUM(quantity - filled_quantity),
                'order_count', COUNT(*)
            ) ORDER BY price DESC)
            FROM orderbook_live
            WHERE session_id = p_session_id
            AND side = 'buy'
            AND status IN ('open', 'partially_filled')
            AND quantity > filled_quantity
            GROUP BY price
        ), '[]'::json),
        'asks', COALESCE((
            SELECT json_agg(json_build_object(
                'price', price,
                'quantity', SUM(quantity - filled_quantity),
                'order_count', COUNT(*)
            ) ORDER BY price ASC)
            FROM orderbook_live
            WHERE session_id = p_session_id
            AND side = 'sell'
            AND status IN ('open', 'partially_filled')
            AND quantity > filled_quantity
            GROUP BY price
        ), '[]'::json),
        'last_price', (
            SELECT price FROM trades
            WHERE session_id = p_session_id
            ORDER BY created_at DESC
            LIMIT 1
        ),
        'volume', COALESCE((
            SELECT SUM(quantity) FROM trades
            WHERE session_id = p_session_id
        ), 0)
    ) INTO v_result;
    
    RETURN v_result;
END;
$$;

GRANT EXECUTE ON FUNCTION get_orderbook_snapshot(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_orderbook_snapshot(UUID) TO service_role;
