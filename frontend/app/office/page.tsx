"use client"

import { useEffect } from "react"
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
  hasPlant = false,
  hasTrash = false,
}: {
  sprite: string
  name: string
  role: string
  status: keyof typeof statusStyles
  hasPlant?: boolean
  hasTrash?: boolean
}) => {
  const statusMeta = statusStyles[status]

  return (
    <div className="relative w-[180px] h-[180px] group">
      {/* Background is now fully transparent to blend with floor */}
      <div className="absolute inset-0 overflow-hidden">
        {/* Subtle shadow to ground the unit, but no distinct floor tile */}
      </div>

      <PartitionFrame />

      {/* Worker */}
      <img
        src={sprite}
        className="absolute top-6 left-1/2 -translate-x-1/2 w-[80px] h-[80px] object-contain pixelated z-20 drop-shadow-[0_10px_12px_rgba(0,0,0,0.25)] transition-transform group-hover:-translate-y-1"
        alt={name}
      />

      {/* Optional decor */}
      {hasPlant && (
        <img
          src="/sprites/plant.png"
          className="absolute bottom-4 right-3 w-10 h-10 object-contain pixelated z-10 opacity-90"
          alt="plant"
        />
      )}
      {hasTrash && (
        <img
          src="/sprites/Trash.png"
          className="absolute bottom-4 left-3 w-10 h-10 object-contain pixelated z-10 opacity-80"
          alt="trash"
        />
      )}

      {/* Status */}
      <div className="absolute top-2 left-2 z-30 flex items-center gap-2">
        
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

export default function Page() {
  const { initializeDemoAgents } = useTradingStore()

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
      </div>



      {/* CRT/Scanline Effects */}
      <div className="fixed inset-0 pointer-events-none z-50 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.12)_50%),linear-gradient(90deg,rgba(255,0,0,0.05),rgba(0,255,0,0.02),rgba(0,0,255,0.05))] bg-[length:100%_2px,3px_100%] opacity-25 mix-blend-overlay" />
      <div className="fixed inset-0 pointer-events-none z-50 shadow-[inset_0_0_120px_rgba(0,0,0,0.82)]" />
    </div>
  )
}

