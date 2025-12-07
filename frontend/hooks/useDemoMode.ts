import { useTradingStore, Order } from "@/lib/store"

export function useDemoMode(enabled: boolean) {
  const { addOrder, agents, updateAgent } = useTradingStore()

  // Demo Loop
  if (!enabled) return

  // Randomly change agent states
  setInterval(() => {
    const randomAgent = agents[Math.floor(Math.random() * agents.length)]
    if (!randomAgent || randomAgent.status === "offline") return

    // 10% chance to go analyzing
    if (Math.random() < 0.1) {
      updateAgent(randomAgent.id, { status: "analyzing" })
      setTimeout(() => {
         updateAgent(randomAgent.id, { status: "idle" })
      }, 2000)
    }
  }, 1000)

  // Randomly submit orders
  setInterval(() => {
    const activeAgents = agents.filter(a => a.status !== "offline")
    if (activeAgents.length === 0) return

    const agent = activeAgents[Math.floor(Math.random() * activeAgents.length)]
    const side = Math.random() > 0.5 ? "buy" : "sell"
    const price = 20000 + Math.random() * 50000
    
    const order: Order = {
      id: Math.random().toString(36).slice(2),
      agentId: agent.id,
      side,
      symbol: Math.random() > 0.5 ? "BTC" : "ETH",
      quantity: parseFloat((Math.random() * 2).toFixed(4)),
      price: parseFloat(price.toFixed(2)),
      timestamp: Date.now()
    }

    addOrder(order)
    
    // Reset status after a bit
    setTimeout(() => {
       updateAgent(agent.id, { status: "idle" })
    }, 10000)

  }, 80000) // Every 800ms an order
}

