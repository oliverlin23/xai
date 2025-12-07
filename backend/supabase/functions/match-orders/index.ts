// Supabase Edge Function: Order Matching Engine
// Matches buy orders with sell orders using price-time priority
//
// Called via:
// 1. Database webhook on orderbook_live INSERT
// 2. Direct HTTP POST with { session_id: string }

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

// Types matching our database schema
interface Order {
  id: string;
  session_id: string;
  trader_name: string;
  side: "buy" | "sell";
  price: number;
  quantity: number;
  filled_quantity: number;
  status: "open" | "filled" | "partially_filled" | "cancelled";
  created_at: string;
}

interface Trade {
  session_id: string;
  buyer_name: string;
  seller_name: string;
  price: number;
  quantity: number;
}

interface MatchResult {
  trades_executed: number;
  orders_updated: number;
  total_volume: number;
}

// Match orders for a given session
async function matchOrders(
  supabase: ReturnType<typeof createClient>,
  sessionId: string
): Promise<MatchResult> {
  let tradesExecuted = 0;
  let ordersUpdated = 0;
  let totalVolume = 0;

  // Get open buy orders (bids) - highest price first, then oldest first
  const { data: bids, error: bidsError } = await supabase
    .from("orderbook_live")
    .select("*")
    .eq("session_id", sessionId)
    .eq("side", "buy")
    .in("status", ["open", "partially_filled"])
    .order("price", { ascending: false })
    .order("created_at", { ascending: true });

  if (bidsError) {
    console.error("Error fetching bids:", bidsError);
    throw bidsError;
  }

  // Get open sell orders (asks) - lowest price first, then oldest first
  const { data: asks, error: asksError } = await supabase
    .from("orderbook_live")
    .select("*")
    .eq("session_id", sessionId)
    .eq("side", "sell")
    .in("status", ["open", "partially_filled"])
    .order("price", { ascending: true })
    .order("created_at", { ascending: true });

  if (asksError) {
    console.error("Error fetching asks:", asksError);
    throw asksError;
  }

  if (!bids?.length || !asks?.length) {
    console.log("No matching opportunities - bids:", bids?.length, "asks:", asks?.length);
    return { trades_executed: 0, orders_updated: 0, total_volume: 0 };
  }

  // Track remaining quantities (mutable copies)
  const bidRemaining = new Map<string, number>();
  const askRemaining = new Map<string, number>();

  for (const bid of bids) {
    bidRemaining.set(bid.id, bid.quantity - bid.filled_quantity);
  }
  for (const ask of asks) {
    askRemaining.set(ask.id, ask.quantity - ask.filled_quantity);
  }

  const trades: Trade[] = [];
  const orderUpdates: { id: string; filled_quantity: number; status: string }[] = [];

  // Match orders: iterate through bids (highest first) and match with asks (lowest first)
  for (const bid of bids) {
    const bidRem = bidRemaining.get(bid.id) || 0;
    if (bidRem <= 0) continue;

    for (const ask of asks) {
      const askRem = askRemaining.get(ask.id) || 0;
      if (askRem <= 0) continue;

      // Match condition: bid price >= ask price
      if (bid.price >= ask.price) {
        // Don't match same trader with themselves
        if (bid.trader_name === ask.trader_name) continue;

        // Calculate fill quantity
        const currentBidRem = bidRemaining.get(bid.id) || 0;
        const currentAskRem = askRemaining.get(ask.id) || 0;
        const fillQty = Math.min(currentBidRem, currentAskRem);

        if (fillQty <= 0) continue;

        // Execution price is the resting order's price (price-time priority)
        // The ask was there first if we're iterating through bids
        const execPrice = ask.price;

        // Create trade
        trades.push({
          session_id: sessionId,
          buyer_name: bid.trader_name,
          seller_name: ask.trader_name,
          price: execPrice,
          quantity: fillQty,
        });

        // Update remaining quantities
        bidRemaining.set(bid.id, currentBidRem - fillQty);
        askRemaining.set(ask.id, currentAskRem - fillQty);

        totalVolume += fillQty;
        tradesExecuted++;

        console.log(
          `Matched: ${bid.trader_name} buys ${fillQty} @ ${execPrice} from ${ask.trader_name}`
        );
      }
    }
  }

  // Prepare order updates
  for (const bid of bids) {
    const originalRemaining = bid.quantity - bid.filled_quantity;
    const newRemaining = bidRemaining.get(bid.id) || 0;
    const filled = originalRemaining - newRemaining;

    if (filled > 0) {
      const newFilledQty = bid.filled_quantity + filled;
      const newStatus =
        newFilledQty >= bid.quantity
          ? "filled"
          : newFilledQty > 0
          ? "partially_filled"
          : "open";

      orderUpdates.push({
        id: bid.id,
        filled_quantity: newFilledQty,
        status: newStatus,
      });
    }
  }

  for (const ask of asks) {
    const originalRemaining = ask.quantity - ask.filled_quantity;
    const newRemaining = askRemaining.get(ask.id) || 0;
    const filled = originalRemaining - newRemaining;

    if (filled > 0) {
      const newFilledQty = ask.filled_quantity + filled;
      const newStatus =
        newFilledQty >= ask.quantity
          ? "filled"
          : newFilledQty > 0
          ? "partially_filled"
          : "open";

      orderUpdates.push({
        id: ask.id,
        filled_quantity: newFilledQty,
        status: newStatus,
      });
    }
  }

  // Insert trades
  if (trades.length > 0) {
    const { error: tradesError } = await supabase.from("trades").insert(trades);

    if (tradesError) {
      console.error("Error inserting trades:", tradesError);
      throw tradesError;
    }
    console.log(`Inserted ${trades.length} trades`);
  }

  // Update orders
  for (const update of orderUpdates) {
    const { error: updateError } = await supabase
      .from("orderbook_live")
      .update({
        filled_quantity: update.filled_quantity,
        status: update.status,
      })
      .eq("id", update.id);

    if (updateError) {
      console.error("Error updating order:", update.id, updateError);
      // Continue with other updates
    } else {
      ordersUpdated++;
    }
  }

  // Update trader states (positions and cash)
  for (const trade of trades) {
    // Update buyer: +position, -cash
    await updateTraderState(supabase, sessionId, trade.buyer_name, trade.quantity, -trade.price * trade.quantity);
    // Update seller: -position, +cash
    await updateTraderState(supabase, sessionId, trade.seller_name, -trade.quantity, trade.price * trade.quantity);
  }

  return {
    trades_executed: tradesExecuted,
    orders_updated: ordersUpdated,
    total_volume: totalVolume,
  };
}

// Update trader state (position and cash)
async function updateTraderState(
  supabase: ReturnType<typeof createClient>,
  sessionId: string,
  traderName: string,
  positionDelta: number,
  cashDeltaCents: number
): Promise<void> {
  // First, try to get existing state
  const { data: existing } = await supabase
    .from("trader_state_live")
    .select("*")
    .eq("session_id", sessionId)
    .eq("name", traderName)
    .single();

  const cashDeltaDollars = cashDeltaCents / 100;

  if (existing) {
    // Update existing
    const { error } = await supabase
      .from("trader_state_live")
      .update({
        position: existing.position + positionDelta,
        cash: parseFloat(existing.cash) + cashDeltaDollars,
        updated_at: new Date().toISOString(),
      })
      .eq("id", existing.id);

    if (error) {
      console.error("Error updating trader state:", error);
    }
  } else {
    // Determine trader type from name
    const fundamentalTraders = ["conservative", "momentum", "historical", "balanced", "realtime"];
    const noiseTraders = [
      "eacc_sovereign", "america_first", "blue_establishment", "progressive_left",
      "optimizer_idw", "fintwit_market", "builder_engineering", "academic_research", "osint_intel"
    ];
    
    let traderType = "user";
    if (fundamentalTraders.includes(traderName)) {
      traderType = "fundamental";
    } else if (noiseTraders.includes(traderName)) {
      traderType = "noise";
    }

    // Insert new state
    const { error } = await supabase.from("trader_state_live").insert({
      session_id: sessionId,
      trader_type: traderType,
      name: traderName,
      position: positionDelta,
      cash: 1000 + cashDeltaDollars, // Starting cash + delta
    });

    if (error) {
      console.error("Error inserting trader state:", error);
    }
  }
}

// Main handler
Deno.serve(async (req) => {
  try {
    // Create Supabase client with service role key (bypasses RLS)
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    // Parse request body
    const body = await req.json();
    
    // Handle webhook payload (has 'record' field) or direct call (has 'session_id')
    let sessionId: string;
    
    if (body.record) {
      // Called from database webhook
      sessionId = body.record.session_id;
      console.log("Triggered by webhook for order:", body.record.id);
    } else if (body.session_id) {
      // Direct call
      sessionId = body.session_id;
      console.log("Direct call for session:", sessionId);
    } else {
      return new Response(
        JSON.stringify({ error: "Missing session_id or record in request body" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      );
    }

    // Run matching
    const result = await matchOrders(supabase, sessionId);

    return new Response(
      JSON.stringify({
        success: true,
        session_id: sessionId,
        ...result,
      }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  } catch (error) {
    console.error("Error in match-orders:", error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
});
