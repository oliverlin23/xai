import type { Metadata } from "next"
import { Press_Start_2P } from "next/font/google"
import "./globals.css"
import { Providers } from "./providers"
import { Navigation } from "@/components/Navigation"

const pressStart = Press_Start_2P({
  weight: "400",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: "Superforecaster - AI-Powered Predictions",
  description: "23-agent superforecasting system powered by Grok AI",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={pressStart.className}>
        <Providers>
          <div className="min-h-screen">
            <Navigation />
            <main>
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  )
}
