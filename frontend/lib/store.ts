import { create } from "zustand"

export interface Order {
  id: string
  agentId: string
  side: "buy" | "sell"
  symbol: string
  quantity: number
  price: number
  timestamp: number
}

export interface Agent {
  id: string
  name: string
  role: string
  status: "idle" | "analyzing" | "submitting-order" | "offline"
  prediction?: number
  confidence?: number
}

interface TradingState {
  agents: Agent[]
  orders: Order[]
  addOrder: (order: Order) => void
  removeOrder: (orderId: string) => void
  updateAgent: (agentId: string, updates: Partial<Agent>) => void
  initializeDemoAgents: (count: number) => void
}

const roles = ["Trader", "Quant", "Analyst", "Execution"]
const names = [
  "Conservative", "Momentum", "Historical", "Balanced", "Realtime",
  "eacc_sovereign", "america_first", "blue_establishment", "progressive_left",
  "optimizer_idw", "fintwit_market", "builder_engineering", "academic_research", "osint_intel",
  "Oliver", "Owen", "Skylar", "Tyler"
]

export const useTradingStore = create<TradingState>((set) => ({
  agents: [],
  orders: [],

  addOrder: (order) =>
    set((state) => ({
      orders: [...state.orders.slice(-99), order], // Keep last 100 orders
    })),

  removeOrder: (orderId) =>
    set((state) => ({
      orders: state.orders.filter((o) => o.id !== orderId),
    })),

  updateAgent: (agentId, updates) =>
    set((state) => ({
      agents: state.agents.map((agent) =>
        agent.id === agentId ? { ...agent, ...updates } : agent
      ),
    })),

  initializeDemoAgents: (count) =>
    set(() => ({
      agents: Array.from({ length: count }, (_, i) => ({
        id: `agent-${i}`,
        name: names[i] || `Agent ${i + 1}`,
        role: roles[i % roles.length],
        status: "idle" as const,
      })),
    })),
}))
