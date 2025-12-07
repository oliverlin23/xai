"use client"

import { useEffect, useState } from "react"
import { useTradingStore } from "@/lib/store"
import { useDemoMode } from "@/hooks/useDemoMode"
import Image from "next/image"

const workerSprites = [
  "/sprites/worker1.png",
  "/sprites/worker2.png",
  "/sprites/worker4.png",
  "/sprites/worker1.png",
  "/sprites/worker4.png",
  "/sprites/worker2.png",
  "/sprites/worker1.png",
  "/sprites/worker2.png",
]

const roles = ["Trader", "Quant", "Analyst", "Execution"]

const statusStyles = {
  idle: { label: "Active", className: "bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.45)]" },
  analyzing: { label: "Processing", className: "bg-yellow-400 shadow-[0_0_10px_rgba(234,179,8,0.45)]" },
  "submitting-order": { label: "Submitting", className: "bg-sky-400 shadow-[0_0_10px_rgba(56,189,248,0.45)]" },
  offline: { label: "Offline", className: "bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.45)]" },
}

const demoOrderBook = {
  asks: [
    { price: 0.44, size: 1200 },
    { price: 0.36, size: 950 },
    { price: 0.35, size: 820 },
    { price: 0.33, size: 640 },
  ],
  bids: [
    { price: 0.30, size: 1180 },
    { price: 0.29, size: 980 },
    { price: 0.28, size: 840 },
    { price: 0.27, size: 710 },
  ],
}

const PartitionFrame = () => (
  <>
    <img
      src="/sprites/office-partitions-1.png"
      className="absolute -top-6 left-0 w-full h-full object-contain pixelated opacity-80pointer-events-none z-10"
      alt="partition top"
    />
    <img
      src="/sprites/office-partitions-2.png"
      className="absolute -top-6 right-1/2 w-full h-full object-contain pixelated opacity-80pointer-events-none z-10"
      alt="partition left"
    />
  </>
)

const Cubicle = ({
  sprite,
  name,
  role,
  status,
  community,
  lastTrade,
  hasPlant = false,
  hasTrash = false,
}: {
  sprite: string
  name: string
  role: string
  status: keyof typeof statusStyles
  community?: string
  lastTrade?: {
    side: "buy" | "sell"
    symbol: string
    quantity: number
    price: number
  }
  hasPlant?: boolean
  hasTrash?: boolean
}) => {
  const statusMeta = statusStyles[status]

  const tradeLine = lastTrade
    ? `${lastTrade.side.toUpperCase()} ${lastTrade.quantity} ${lastTrade.symbol} @ $${lastTrade.price}`
    : "No trades yet"

  return (
    <div className="relative w-[180px] h-[180px]">
      <PartitionFrame />

      {/* Smaller hover target to reduce accidental triggers */}
      <div className="absolute inset-4 group">
        {/* Hover card */}
        <div className="pointer-events-none absolute -top-2 left-1/2 -translate-x-1/2 -translate-y-full z-40 px-3 py-2 rounded-md bg-slate-900/90 border border-white/10 shadow-lg text-xs text-slate-100 opacity-0 transition-opacity duration-150 group-hover:opacity-100 whitespace-nowrap">
          <div className="font-semibold">{name}</div>
          <div className="text-[11px] text-slate-300">Role: {role}</div>
          <div className="text-[11px] text-slate-300">
            Community: {community || "TBD"}
          </div>
          <div className="text-[11px] text-slate-200 mt-1">
            Last trade: {tradeLine}
          </div>
        </div>

        {/* Worker */}
        <img
          src={sprite}
          className="absolute top-4 left-1/2 -translate-x-1/2 w-[76px] h-[76px] object-contain pixelated z-20 drop-shadow-[0_10px_12px_rgba(0,0,0,0.25)] transition-transform group-hover:-translate-y-1"
          alt={name}
        />

        {/* Optional decor */}
        {hasPlant && (
          <img
            src="/sprites/plant.png"
            className="absolute bottom-3 right-2 w-10 h-10 object-contain pixelated z-10 opacity-90"
            alt="plant"
          />
        )}
        {hasTrash && (
          <img
            src="/sprites/Trash.png"
            className="absolute bottom-3 left-2 w-10 h-10 object-contain pixelated z-10 opacity-80"
            alt="trash"
          />
        )}

        {/* Status dot */}
        <div className="absolute top-1 left-1 z-30 flex items-center gap-2">
          <div className={`h-3 w-3 rounded-full ${statusMeta.className}`} title={statusMeta.label} />
        </div>
      </div>
    </div>
  )
}

const OfficeScene = () => {
  const { agents } = useTradingStore()
  const activeAgents = Array.from({ length: 18 }, (_, i) => {
    if (agents[i]) return agents[i]
    return {
      id: `seed-${i}`,
      name: `Agent ${i + 1}`,
      status: "idle" as const,
      cubicleIndex: i,
      mood: "neutral" as const,
      community: "TBD",
      lastTrade: undefined,
    }
  })

  return (
    <div className="relative w-full h-full flex items-center justify-center p-0">
      <div className="relative z-10 w-full h-full flex flex-col justify-between">
        {/* Main Office Floor */}
        <div className="flex-1 flex items-center justify-center gap-52 px-6 pt-48">
          {/* Left Bank */}
          <div className="grid grid-cols-3 gap-x-0 gap-y-0">
            {activeAgents.slice(0, 9).map((agent, i) => (
              <div key={agent.id} className="flex justify-center">
                <Cubicle
                  sprite={workerSprites[i % workerSprites.length]}
                  name={agent.name}
                  role={roles[i % roles.length]}
                  status={agent.status}
                  community={agent.community}
                  lastTrade={agent.lastTrade}
                  hasPlant={false}
                  hasTrash={i % 4 === 1}
                />
              </div>
            ))}
          </div>

          {/* Right Bank */}
          <div className="grid grid-cols-3 gap-x-0 gap-y-0">
            {activeAgents.slice(9, 18).map((agent, i) => {
              const idx = i + 9
              return (
                <div key={agent.id} className="flex justify-center">
                  <Cubicle
                    sprite={workerSprites[idx % workerSprites.length]}
                    name={agent.name}
                    role={roles[idx % roles.length]}
                  status={agent.status}
                  community={agent.community}
                  lastTrade={agent.lastTrade}
                    hasPlant={false}
                    hasTrash={idx % 4 === 1}
                  />
                </div>
              )
            })}
          </div>
        </div>

        {/*
        <div className="relative pt-6 mt-6 flex justify-center pb-6">

          <div className="relative">
            <Cubicle
              sprite="/sprites/boss.png"
              name="Director Joja"
              role="Overseer"
              status="analyzing"
              hasPlant
            />
          </div>
        </div>
        */}
      </div>
    </div>
  )
}

const OrderBookModal = ({
  open,
  onClose,
}: {
  open: boolean
  onClose: () => void
}) => {
  if (!open) return null

  const maxAskSize = Math.max(...demoOrderBook.asks.map((a) => a.size), 1)
  const maxBidSize = Math.max(...demoOrderBook.bids.map((b) => b.size), 1)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
      <div className="relative w-full max-w-3xl rounded-xl border-4 border-[#2d3748] bg-[#0f172a]/95 text-[#f7f5f0] shadow-[0_20px_40px_rgba(0,0,0,0.55)] p-6">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 px-3 py-1 bg-red-500 text-white text-xs rounded-md shadow"
        >
          Close
        </button>

        <div className="text-center text-2xl mb-4 tracking-[0.15em]">Order Book</div>

        <div className="space-y-4">
          <div className="border border-red-400/40 rounded-lg p-4 bg-red-900/25 shadow-inner">
            <div className="text-red-300 text-lg mb-2 tracking-[0.1em]">Asks</div>
            <div className="space-y-2">
              {demoOrderBook.asks.map((ask, idx) => {
                const widthPct = Math.max((ask.size / maxAskSize) * 100, 6)
                return (
                  <div
                    key={idx}
                    className="relative flex items-center text-sm bg-red-900/35 border border-red-500/30 rounded px-3 py-2 overflow-hidden"
                  >
                    <div
                      className="absolute left-0 top-0 h-full bg-red-600/30"
                      style={{ width: `${widthPct}%` }}
                    />
                    <div className="relative flex-1 flex justify-between items-center">
                      <span className="text-red-200 font-semibold">{Math.round(ask.price * 100)}¢</span>
                      <span className="text-red-100">{ask.size.toLocaleString()}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          <div className="border border-emerald-400/40 rounded-lg p-4 bg-emerald-900/25 shadow-inner">
            <div className="text-emerald-300 text-lg mb-2 tracking-[0.1em]">Bids</div>
            <div className="space-y-2">
              {demoOrderBook.bids.map((bid, idx) => {
                const widthPct = Math.max((bid.size / maxBidSize) * 100, 6)
                return (
                  <div
                    key={idx}
                    className="relative flex items-center text-sm bg-emerald-900/35 border border-emerald-500/30 rounded px-3 py-2 overflow-hidden"
                  >
                    <div
                      className="absolute left-0 top-0 h-full bg-emerald-600/30"
                      style={{ width: `${widthPct}%` }}
                    />
                    <div className="relative flex-1 flex justify-between items-center">
                      <span className="text-emerald-200 font-semibold">{Math.round(bid.price * 100)}¢</span>
                      <span className="text-emerald-100">{bid.size.toLocaleString()}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Page() {
  const { initializeDemoAgents } = useTradingStore()
  const [orderBookOpen, setOrderBookOpen] = useState(false)

  useEffect(() => {
    initializeDemoAgents(18)
  }, [initializeDemoAgents])

  useDemoMode(true)

  return (
    <div className="h-screen w-full flex flex-col items-center justify-center relative overflow-hidden font-pixel">
      <style jsx global>{`
        .pixelated {
          image-rendering: pixelated;
        }
      `}</style>

      {/* Background image */}
      <div className="absolute inset-0 z-0">
        <Image
          src="/officebackground3.png"
          alt="Office floor background"
          fill
          priority
          sizes="100vw"
          className="object-fill"
          style={{ imageRendering: "pixelated" }}
        />
        <div className="absolute inset-0 bg-black/10" />
      </div>

      {/* Main Scene */}
      <div className="relative z-10 w-full h-full">
        <OfficeScene />

        {/* Central desk / terminal in the aisle */}
        <div className="absolute inset-0 flex items-center justify-center z-30 pointer-events-none">
          <button
            onClick={() => setOrderBookOpen(true)}
            className="relative group p-4 rounded-lg bg-transparent pointer-events-auto"
            aria-label="Open order book terminal"
          >
            <img
              src="/sprites/desk-with-pc.png"
              alt="Desk terminal"
              className="w-24 h-24 object-contain pixelated drop-shadow-[0_10px_15px_rgba(0,0,0,0.45)] transition-transform duration-150 group-hover:-translate-y-1"
            />
            <div className="pointer-events-none absolute left-1/2 -translate-x-1/2 -top-10 px-3 py-1 rounded-md bg-slate-900/90 text-[11px] text-slate-100 border border-white/10 shadow opacity-0 group-hover:opacity-100 transition-opacity duration-150 whitespace-nowrap">
              View Order Book
            </div>
          </button>
        </div>
      </div>

      <OrderBookModal open={orderBookOpen} onClose={() => setOrderBookOpen(false)} />

      {/* CRT/Scanline Effects */}
      <div className="fixed inset-0 pointer-events-none z-50 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.12)_50%),linear-gradient(90deg,rgba(255,0,0,0.05),rgba(0,255,0,0.02),rgba(0,0,255,0.05))] bg-[length:100%_2px,3px_100%] opacity-25 mix-blend-overlay" />
      <div className="fixed inset-0 pointer-events-none z-50 shadow-[inset_0_0_120px_rgba(0,0,0,0.82)]" />
    </div>
  )
}

