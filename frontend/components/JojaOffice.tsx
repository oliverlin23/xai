"use client"

import { useEffect, useState } from "react"
import { Agent } from "@/types/agent"
import { cn } from "@/lib/utils"

interface JojaOfficeProps {
  agents: Agent[]
}

// --- Constants & Configuration ---

// Colors extracted from the Joja palette
const COLORS = {
  wall: "bg-[#444444]",
  floorMain: "bg-[#a8c6fa]",
  floorAlt: "bg-[#89adeb]",
  desk: "bg-[#9c7c5d]",
  deskShadow: "bg-[#7a5f45]",
  cubicleWall: "bg-[#cfd8dc]",
  monitorOff: "bg-[#2d3748]",
}

// Sprite Configuration
const SPRITE_SHEET = "/assets/zzzzjojacorps.png"
const SPRITE_WIDTH = 16
const SPRITE_HEIGHT = 32

// --- Sub-Components ---

const PixelText = ({ children, className, size = "sm" }: { children: React.ReactNode, className?: string, size?: "sm" | "md" | "lg" }) => {
  const sizes = {
    sm: "text-[10px]",
    md: "text-[14px]",
    lg: "text-[24px]"
  }
  return (
    <div className={cn("font-mono tracking-tighter leading-none select-none", sizes[size], className)} style={{ imageRendering: "pixelated" }}>
      {children}
    </div>
  )
}

const OverheadLight = ({ delay = 0 }: { delay?: number }) => (
  <div className="relative flex flex-col items-center">
    {/* Light Fixture */}
    <div className="w-8 h-4 bg-gray-200 rounded-b-lg z-20 relative shadow-sm" />
    {/* Light Glow (Cone) */}
    <div 
      className="absolute top-2 w-24 h-48 bg-gradient-to-b from-white/30 to-transparent pointer-events-none z-10"
      style={{ clipPath: "polygon(40% 0, 60% 0, 100% 100%, 0% 100%)" }}
    />
    {/* Bulb Pulse */}
    <div 
      className="absolute top-2 w-6 h-6 bg-white rounded-full blur-md animate-pulse opacity-50" 
      style={{ animationDelay: `${delay}ms` }}
    />
  </div>
)

const Cubicle = ({ id, agent }: { id: number, agent?: Agent }) => {
  const [frame, setFrame] = useState(0)
  
  // Animation Loop for Agent
  useEffect(() => {
    const interval = setInterval(() => setFrame(f => (f + 1) % 2), 500 + Math.random() * 200)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="relative w-full h-full flex items-end justify-center group perspective-[500px]">
      {/* Cubicle Walls (U-Shape) */}
      <div className="absolute inset-0 border-l-4 border-r-4 border-t-0 border-slate-300 bg-slate-100/10 rounded-sm pointer-events-none h-[90%] bottom-0" />
      <div className="absolute bottom-[60%] w-full h-[40%] border-t-4 border-slate-300 pointer-events-none" />

      {/* Desk */}
      <div className={cn("absolute bottom-2 w-[80%] h-[24px] rounded-sm shadow-sm z-10", COLORS.desk)}>
        {/* Desk Shadow/Detail */}
        <div className="absolute top-full w-full h-1 bg-black/20" />
      </div>

      {/* Monitor */}
      <div className="absolute bottom-[28px] z-10 flex flex-col items-center">
        <div className={cn("w-8 h-6 rounded-sm border-2 border-gray-600 relative overflow-hidden transition-colors duration-300", COLORS.monitorOff)}>
          {/* Screen Content / Glow */}
          {agent && (
            <div className={cn("absolute inset-0 animate-pulse opacity-80", 
              agent.status === 'working' ? 'bg-green-500/80' : 
              agent.status === 'break' ? 'bg-yellow-500/80' : 'bg-red-900/50'
            )} />
          )}
        </div>
        <div className="w-4 h-2 bg-gray-700" /> {/* Stand */}
      </div>

      {/* Agent Sprite */}
      {agent && (
        <div className="absolute bottom-[10px] z-20 transform scale-[1.5] origin-bottom">
           <div 
             className="w-[16px] h-[32px] [image-rendering:pixelated]"
             style={{
                backgroundImage: `url(${SPRITE_SHEET})`,
                // Default to first sprite for now, or use a calculated offset if we knew the layout
                // Using a generic "sitting" look if possible, or just the standing sprite cropped
                backgroundPosition: `-${0 + (frame * 16)}px -0px`, 
                backgroundSize: '1200px 800px',
             }}
           />
           {/* Tooltip */}
           <div className="hidden group-hover:block absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-black/90 text-white text-[10px] px-2 py-1 rounded border border-white/20 whitespace-nowrap z-50">
             <div className="font-bold text-blue-300">{agent.name}</div>
             <div className="opacity-75">{agent.role} • {agent.status}</div>
           </div>
        </div>
      )}

      {/* Chair Back (if agent exists, show chair behind slightly?) */}
      {!agent && (
        <div className="absolute bottom-2 w-6 h-8 bg-gray-700 rounded-t-md opacity-50" />
      )}

      {/* Status LED on Cubicle Wall */}
      <div className={cn("absolute top-[45%] right-1 w-1.5 h-1.5 rounded-full shadow-[0_0_4px_currentcolor]",
        !agent ? "bg-gray-500 text-gray-500" :
        agent.status === 'working' ? "bg-green-500 text-green-500" :
        agent.status === 'break' ? "bg-yellow-400 text-yellow-400" : "bg-red-500 text-red-500"
      )} />
    </div>
  )
}

export function JojaOffice({ agents }: JojaOfficeProps) {
  
  // Helper to get agent
  const getAgent = (i: number) => agents.find(a => a.cubicleId === i)

  return (
    <div className="w-full max-w-[1200px] mx-auto p-4">
      {/* Main Office Container (Fixed Aspect Ratio Wrapper) */}
      <div className="relative w-full aspect-[16/9] bg-[#333333] rounded-xl overflow-hidden shadow-2xl border-4 border-[#2a2a2a]">
        
        {/* --- WALLS --- */}
        <div className="absolute inset-0 flex flex-col">
            {/* Back Wall */}
            <div className={cn("h-[35%] w-full relative border-b-8 border-black/20", COLORS.wall)}>
                
                {/* Overhead Lights Container */}
                <div className="absolute top-0 left-0 w-full flex justify-between px-12 -mt-2">
                    {Array.from({ length: 8 }).map((_, i) => (
                        <OverheadLight key={i} delay={i * 100} />
                    ))}
                </div>

                {/* Center Branding */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-2 z-0">
                    <div className="flex items-center gap-2">
                        <PixelText size="lg" className="text-blue-300 font-bold drop-shadow-md">Joja</PixelText>
                        <div className="w-6 h-6 grid grid-cols-2 gap-[2px] rotate-45"> {/* Logo Icon */}
                            <div className="bg-blue-300 rounded-sm" /> <div className="bg-blue-300 rounded-sm" />
                            <div className="bg-blue-300 rounded-sm" /> <div className="bg-blue-300 rounded-sm" />
                        </div>
                    </div>
                    <PixelText className="text-blue-200/50">Join us. Thrive.</PixelText>
                    
                    {/* Global Status Board */}
                    <div className="flex gap-4 mt-2 bg-black/20 p-2 rounded">
                        <div className="flex items-center gap-1">
                            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                            <PixelText className="text-white/70">work</PixelText>
                        </div>
                        <div className="flex items-center gap-1">
                            <div className="w-2 h-2 bg-red-900 rounded-full" />
                            <PixelText className="text-white/30">rest</PixelText>
                        </div>
                    </div>
                </div>

                {/* Side Windows (Manager Offices) */}
                <div className="absolute top-8 left-8 w-32 h-24 bg-blue-900/30 border-4 border-gray-600 rounded shadow-inner overflow-hidden group">
                    <div className="absolute inset-0 bg-[url('/assets/jojaoffice.png')] bg-cover opacity-20" /> {/* Reflection hint */}
                    <div className="absolute bottom-0 left-8 w-4 h-8 bg-black/50 rounded-t-lg" /> {/* Silhouette */}
                </div>
                <div className="absolute top-8 right-8 w-32 h-24 bg-blue-900/30 border-4 border-gray-600 rounded shadow-inner overflow-hidden">
                    <div className="absolute inset-0 bg-[url('/assets/jojaoffice.png')] bg-cover opacity-20" />
                </div>
            </div>

            {/* Floor */}
            <div className="flex-1 w-full relative perspective-[1000px] overflow-hidden">
                 {/* Floor Pattern (CSS Checkerboard) */}
                <div className="absolute inset-0 w-full h-full opacity-20"
                    style={{
                        backgroundImage: `linear-gradient(45deg, #ccc 25%, transparent 25%), 
                                          linear-gradient(-45deg, #ccc 25%, transparent 25%), 
                                          linear-gradient(45deg, transparent 75%, #ccc 75%), 
                                          linear-gradient(-45deg, transparent 75%, #ccc 75%)`,
                        backgroundSize: '40px 40px',
                        backgroundColor: '#fff'
                    }} 
                />
                
                {/* Central Aisle */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-blue-100/10 to-transparent pointer-events-none" />
            </div>
        </div>

        {/* --- CUBICLE GRID --- */}
        {/* 
           We position the grid strictly over the floor area.
           Using a grid layout with a gap for the central aisle.
        */}
        <div className="absolute top-[35%] bottom-0 left-0 right-0 p-8 flex justify-center gap-16 overflow-visible">
            
            {/* Left Block */}
            <div className="grid grid-cols-3 gap-2 gap-y-8 w-full max-w-[400px]">
                {Array.from({ length: 12 }).map((_, i) => (
                    <Cubicle key={i} id={i} agent={getAgent(i)} />
                ))}
            </div>

            {/* Right Block */}
            <div className="grid grid-cols-3 gap-2 gap-y-8 w-full max-w-[400px]">
                {Array.from({ length: 12 }).map((_, i) => (
                    <Cubicle key={i + 12} id={i + 12} agent={getAgent(i + 12)} />
                ))}
            </div>

        </div>
        
        {/* Overlay Vignette */}
        <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle,transparent_50%,rgba(0,0,0,0.4)_100%)]" />

      </div>
    </div>
  )
}
