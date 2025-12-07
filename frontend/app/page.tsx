"use client"

import Image from "next/image"
import Link from "next/link"
import { Press_Start_2P } from "next/font/google"
import { useRouter } from "next/navigation"
import { type FormEvent, type KeyboardEvent, useEffect, useState } from "react"
import { api } from "@/lib/api"

const pressStart = Press_Start_2P({ weight: "400", subsets: ["latin"] })

export default function Page() {
  const router = useRouter()
  const [query, setQuery] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [loadStarted, setLoadStarted] = useState(false)
  const [overlayVisible, setOverlayVisible] = useState(false)
  const [overlayFadeOut, setOverlayFadeOut] = useState(false)
  const [previousOpen, setPreviousOpen] = useState(false)
  const [previousLoading, setPreviousLoading] = useState(false)
  const [previousError, setPreviousError] = useState<string | null>(null)
  const [previousForecasts, setPreviousForecasts] = useState<Array<{
    id: string
    question_text: string
    status: string
    prediction_result?: { prediction?: string; prediction_probability?: number; confidence?: number }
    completed_at?: string
  }>>([])

  const handleSubmit = () => {
    if (!query.trim() || isLoading) return
    setIsLoading(true)
    setLoadStarted(true)
    // next frame so CSS transition can detect the change
    requestAnimationFrame(() => setOverlayVisible(true))
    // Start fade to black before navigating
    setTimeout(() => setOverlayFadeOut(true), 1500)
    setTimeout(() => {
      // Navigate to office with query as URL parameter
      router.push(`/office?q=${encodeURIComponent(query.trim())}`)
    }, 2400) // allow fade-out before routing
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter to submit (prevent newline); allow Shift+Enter to newline
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleFormSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    handleSubmit()
  }

  useEffect(() => {
    if (!previousOpen) return
    const load = async () => {
      setPreviousLoading(true)
      setPreviousError(null)
      try {
        const res = await api.forecasts.list(10, 0)
        setPreviousForecasts(res?.forecasts ?? [])
      } catch (err: any) {
        setPreviousError(err?.message || "Failed to load previous forecasts")
      } finally {
        setPreviousLoading(false)
      }
    }
    load()
  }, [previousOpen])

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
            {/* Ensure bottom-right rivet is present */}
            <div className="absolute bottom-3 right-3 w-3 h-3 rounded-full bg-white/70 shadow-inner shadow-black/60" />

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
            <form
              onSubmit={handleFormSubmit}
              className="w-full max-w-2xl flex flex-col items-center gap-3"
            >
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
                  aria-label="Ask Cassandra a question"
                />
              </div>
              <button
                type="submit"
                disabled={!query.trim() || isLoading}
                className={`${pressStart.className} w-full sm:w-auto self-center px-6 py-3 rounded-lg border-4 border-[#2d3748] bg-[#2d7dd2] text-[#f7f5f0] uppercase tracking-[0.15em] shadow-[0_12px_30px_rgba(0,0,0,0.45)] transition-transform hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-60 disabled:cursor-not-allowed`}
              >
                Enter
              </button>
            </form>
          </div>

          <button
            onClick={() => setPreviousOpen(true)}
            className="px-4 py-2 rounded-lg border border-white/30 bg-white/10 text-white backdrop-blur shadow hover:bg-white/20 transition-colors text-sm"
          >
            Show Previous Forecasts
          </button>
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

      {previousOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setPreviousOpen(false)} />
          <div className="relative w-full max-w-4xl bg-white rounded-xl shadow-2xl p-6 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold text-gray-900">Previous Forecasts</h3>
              <button
                onClick={() => setPreviousOpen(false)}
                className="text-gray-500 hover:text-gray-800 text-lg font-semibold"
              >
                ×
              </button>
            </div>

            {previousLoading && (
              <div className="text-center py-10 text-gray-600">Loading...</div>
            )}

            {previousError && (
              <div className="text-red-600 text-sm mb-3">{previousError}</div>
            )}

            {!previousLoading && !previousError && previousForecasts.length === 0 && (
              <div className="text-center py-10 text-gray-500">No previous forecasts found.</div>
            )}

            <div className="grid md:grid-cols-2 gap-4">
              {previousForecasts.map((item) => {
                const pred = item.prediction_result
                const probability = pred?.prediction_probability
                const confidence = pred?.confidence
                return (
                  <Link
                    key={item.id}
                    href={`/forecast/${item.id}/result`}
                    className="block border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow bg-white"
                    onClick={() => setPreviousOpen(false)}
                  >
                    <div className="text-sm text-gray-500 mb-1">
                      {item.completed_at ? new Date(item.completed_at).toLocaleString() : "In progress"}
                    </div>
                    <div className="font-semibold text-gray-900 line-clamp-2 mb-2">
                      {item.question_text || "Untitled question"}
                    </div>
                    {pred?.prediction && (
                      <div className="text-indigo-700 font-semibold mb-1">
                        {pred.prediction}
                      </div>
                    )}
                    <div className="text-sm text-gray-700 flex flex-wrap gap-3">
                      {typeof probability === "number" && (
                        <span className="px-2 py-1 rounded bg-indigo-50 text-indigo-700 text-xs font-semibold">
                          Prob: {Math.round(probability * 100)}%
                        </span>
                      )}
                      {typeof confidence === "number" && (
                        <span className="px-2 py-1 rounded bg-slate-100 text-slate-700 text-xs font-semibold">
                          Conf: {Math.round(confidence * 100)}%
                        </span>
                      )}
                      <span className="px-2 py-1 rounded bg-gray-100 text-gray-700 text-xs font-semibold capitalize">
                        {item.status || "unknown"}
                      </span>
                    </div>
                  </Link>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
