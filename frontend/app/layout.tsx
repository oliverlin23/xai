import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { Providers } from "./providers"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Superforecaster - AI-Powered Predictions",
  description: "24-agent superforecasting system powered by Grok AI",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
            <nav className="border-b bg-white/80 backdrop-blur-sm">
              <div className="container mx-auto px-4 py-4">
                <div className="flex items-center justify-between">
                  <h1 className="text-2xl font-bold text-indigo-600">
                    Superforecaster
                  </h1>
                  <nav className="flex gap-6">
                    <a href="/" className="text-gray-700 hover:text-indigo-600">
                      New Forecast
                    </a>
                    <a href="/history" className="text-gray-700 hover:text-indigo-600">
                      History
                    </a>
                  </nav>
                </div>
              </div>
            </nav>
            <main className="container mx-auto px-4 py-8">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  )
}
