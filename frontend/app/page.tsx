import Image from "next/image"
import { Press_Start_2P } from "next/font/google"

const pressStart = Press_Start_2P({ weight: "400", subsets: ["latin"] })

export default function Page() {
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
                Supercaster
              </div>
            </div>
          </div>

          <div className="flex gap-4 items-center">
            <a
              href="/office"
              className="px-6 py-3 rounded-lg bg-[#2d7dd2] hover:bg-[#2568ae] text-white font-semibold shadow-lg shadow-black/30 transition-colors"
            >
              Enter the Floor
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
