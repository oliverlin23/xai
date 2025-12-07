# Supabase Migrations

## 001_create_tables.sql

Core forecast tables:

- **sessions** - Forecast sessions with questions and predictions
- **agent_logs** - Real-time agent execution logs
- **factors** - Discovered factors with importance scores

## 002_add_prediction_fields.sql

Adds prediction-related fields to sessions.

## 003_create_trading_tables.sql

Trading system for prediction market simulation.

### Enums

| Type           | Values                                            |
| -------------- | ------------------------------------------------- |
| `trader_type`  | `fundamental`, `noise`, `user`                    |
| `trader_name`  | See below                                         |
| `order_side`   | `buy`, `sell`                                     |
| `order_status` | `open`, `filled`, `partially_filled`, `cancelled` |

**Trader names by type:**

| Type        | Names                                                                                                                                                                     |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| fundamental | `conservative`, `momentum`, `historical`, `balanced`, `realtime`                                                                                                          |
| noise       | `eacc_sovereign`, `america_first`, `blue_establishment`, `progressive_left`, `optimizer_idw`, `fintwit_market`, `builder_engineering`, `academic_research`, `osint_intel` |
| user        | `oliver`, `owen`, `skylar`, `tyler`                                                                                                                                       |

### Tables

#### trader_state_live

Current state of each trader in a session.

| Column        | Type        | Default | Description                   |
| ------------- | ----------- | ------- | ----------------------------- |
| session_id    | UUID        | -       | FK to sessions                |
| trader_type   | trader_type | -       | fundamental, noise, or user   |
| name          | trader_name | -       | Trader identifier             |
| system_prompt | TEXT        | NULL    | Current LLM prompt (optional) |
| position      | INTEGER     | 0       | Contracts held (+long/-short) |
| cash          | DECIMAL     | 1000.00 | Available cash                |
| pnl           | DECIMAL     | 0       | Profit/loss                   |

#### trader_prompts_history

Historical log of all system prompts.

| Column        | Type        | Description                         |
| ------------- | ----------- | ----------------------------------- |
| session_id    | UUID        | FK to sessions                      |
| trader_type   | trader_type | fundamental, noise, or user         |
| name          | trader_name | Trader identifier                   |
| prompt_number | INTEGER     | Sequential prompt # for this trader |
| system_prompt | TEXT        | The prompt content                  |

#### orderbook_live

Active orders in the order book.

| Column          | Type         | Description               |
| --------------- | ------------ | ------------------------- |
| session_id      | UUID         | FK to sessions            |
| trader_name     | trader_name  | Who placed the order      |
| side            | order_side   | buy or sell               |
| price           | INTEGER      | 0-100 (probability cents) |
| quantity        | INTEGER      | Number of contracts       |
| filled_quantity | INTEGER      | How many filled           |
| status          | order_status | Order state               |

#### orderbook_history

Archived orders (same schema as live).

#### trades

Matched trades between buyers and sellers.

| Column      | Type        | Description      |
| ----------- | ----------- | ---------------- |
| session_id  | UUID        | FK to sessions   |
| buyer_name  | trader_name | Who bought       |
| seller_name | trader_name | Who sold         |
| price       | INTEGER     | Execution price  |
| quantity    | INTEGER     | Contracts traded |

### Realtime Enabled

- `trader_state_live`
- `orderbook_live`
- `trades`
