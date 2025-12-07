"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Press_Start_2P } from "next/font/google"

const pressStart = Press_Start_2P({ weight: "400", subsets: ["latin"] })

export function Navigation() {
  const pathname = usePathname()

  const tabs = [
    { name: "Cassandra", href: "/" },
    { name: "Superforecast", href: "/superforecast" },
  ]

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#1a1f2e] border-b-4 border-[#2d3748] shadow-[0_4px_12px_rgba(0,0,0,0.45)]">
      <div className="w-full px-4 sm:px-6">
        <div className="flex items-center gap-8">
          {tabs.map((tab) => {
            const isActive = tab.href === "/" 
              ? pathname === "/" 
              : pathname?.startsWith(tab.href)
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={`${pressStart.className} text-sm tracking-[0.15em] uppercase py-4 px-6 transition-colors relative ${
                  isActive
                    ? "text-[#f7f5f0]"
                    : "text-gray-400 hover:text-gray-300"
                }`}
              >
                {tab.name}
                {isActive && (
                  <div className="absolute bottom-0 left-0 right-0 h-1 bg-[#2d7dd2]" />
                )}
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}

