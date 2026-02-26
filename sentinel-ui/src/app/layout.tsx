import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Sidebar } from '@/components/Sidebar'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'NxGraph Fraud Analytics',
  description: 'Enterprise Fraud Detection System',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-slate-50 flex min-h-screen text-slate-900`}>
        <Sidebar />
        <main className="flex-1 ml-64 flex flex-col">
          {children}
        </main>
      </body>
    </html>
  )
}
