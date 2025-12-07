"use client"

import Image from "next/image"
import { Press_Start_2P } from "next/font/google"
import { useRouter } from "next/navigation"
import { useState, useEffect } from "react"

const pressStart = Press_Start_2P({ weight: "400", subsets: ["latin"] })

export default function Page() {
  const router = useRouter()
  const [query, setQuery] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [loadStarted, setLoadStarted] = useState(false)
  const [overlayVisible, setOverlayVisible] = useState(false)
  const [overlayFadeOut, setOverlayFadeOut] = useState(false)

  const handleSubmit = () => {
    if (!query.trim() || isLoading) return
    setIsLoading(true)
    setLoadStarted(true)
    // next frame so CSS transition can detect the change
    requestAnimationFrame(() => setOverlayVisible(true))
    // Start fade to black before navigating
    setTimeout(() => setOverlayFadeOut(true), 1500)
    setTimeout(() => {
      router.push("/office")
    }, 2400) // allow fade-out before routing
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (e.key === "Enter") {
      handleSubmit()
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="fixed inset-0">
        <Image
          src="/nycskyline.png"
          alt="NYC skyline at night in pixel art"
          fill
          priority
          sizes="100vw"
          className="object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/45 via-black/20 to-transparent" />
      </div>

      <div className="relative z-10 flex items-center justify-center min-h-screen text-white px-6">
        <div className="w-full max-w-3xl flex flex-col items-center gap-8">
          <div
            className="relative w-full rounded-xl border-4 border-[#2d3748] shadow-[0_20px_50px_rgba(0,0,0,0.45)] overflow-hidden"
            style={{
              backgroundImage: `
                linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0) 40%),
                linear-gradient(90deg, rgba(37,46,61,0.9) 0%, rgba(30,38,50,0.9) 100%),
                repeating-linear-gradient(0deg, rgba(255,255,255,0.04), rgba(255,255,255,0.04) 4px, rgba(0,0,0,0.05) 4px, rgba(0,0,0,0.05) 8px)
              `,
            }}
          >
            {/* Faux rivets */}
            <div className="absolute inset-3 flex justify-between">
              {[...Array(2)].map((_, i) => (
                <div key={i} className="w-3 h-3 rounded-full bg-white/70 shadow-inner shadow-black/60" />
              ))}
            </div>
            <div className="absolute inset-3 flex flex-col justify-between">
              {[...Array(2)].map((_, i) => (
                <div key={i} className="w-3 h-3 rounded-full bg-white/70 shadow-inner shadow-black/60" />
              ))}
            </div>

            <div className="relative px-8 py-10 text-center">
              <div
                className={`${pressStart.className} text-4xl sm:text-5xl tracking-[0.2em] text-[#f7f5f0] uppercase select-none`}
                style={{
                  textShadow: `
                    4px 4px 0 #0f172a,
                    -2px 2px 0 #0f172a,
                    2px -2px 0 #0f172a,
                    -2px -2px 0 #0f172a,
                    0 8px 12px rgba(0,0,0,0.55)
                  `,
                  imageRendering: "pixelated",
                }}
              >
                Cassandra
              </div>
            </div>
          </div>

          <div className="w-full flex justify-center">
            <div className="w-full max-w-2xl">
              <div className="relative w-full border-4 border-[#2d3748] rounded-lg bg-white shadow-[0_12px_30px_rgba(0,0,0,0.45)] focus-within:border-[#2d7dd2] transition-colors">
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="What do you want to know?"
                  className="w-full resize-none bg-transparent text-[#0f172a] placeholder:text-slate-500 px-5 py-4 rounded-lg focus:outline-none"
                  rows={3}
                  autoCorrect="off"
                  spellCheck={false}
                  style={{ minHeight: "64px", maxHeight: "260px", overflow: "hidden" }}
                  onInput={(e) => {
                    const target = e.target as HTMLTextAreaElement
                    target.style.height = "auto"
                    const maxHeight = 260 // ~8 lines
                    target.style.height = Math.min(target.scrollHeight, maxHeight) + "px"
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Loading screen overlay */}
      {loadStarted && (
        <div
          className={`fixed inset-0 z-50 transition-opacity duration-2000 ease-in-out ${
            overlayVisible ? "opacity-100" : "opacity-0"
          }`}
        >
          <Image
            src="/sprites/subwaystation.png"
            alt="Loading..."
            fill
            sizes="100vw"
            className="object-cover brightness-115"
            priority
          />
          <div className="absolute inset-0 bg-black/20 backdrop-blur-[1.5px] transition-opacity duration-1200 ease-in-out" />
          <div
            className={`absolute inset-0 bg-black transition-opacity duration-1200 ease-in-out ${
              overlayFadeOut ? "opacity-100" : "opacity-0"
            }`}
          />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex flex-col items-center gap-3 text-[#f7f5f0] drop-shadow-[0_4px_12px_rgba(0,0,0,0.55)]">
              <div className="text-xl tracking-[0.18em] uppercase flex items-center gap-1">
                <span>Departing</span>
                <span className="inline-flex w-10 justify-between text-lg">
                  <span className="animate-[blink_1s_infinite]">.</span>
                  <span className="animate-[blink_1.1s_infinite]">.</span>
                  <span className="animate-[blink_1.2s_infinite]">.</span>
                </span>
              </div>
              <div className="h-1.5 w-28 overflow-hidden rounded-full bg-white/20 relative">
                <div className="absolute inset-y-0 left-0 w-1/3 animate-[slide_1.8s_ease-in-out_infinite] bg-white/60 rounded-full" />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
