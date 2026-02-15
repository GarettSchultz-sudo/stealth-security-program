import type { Metadata } from 'next'
import './globals.css'
import { Providers } from './providers'
import { AppLayout } from '@/components/ui'

export const metadata: Metadata = {
  title: 'ClawShell - AI Cost Control & Security',
  description: 'The protective shell for your AI agents. Track, budget, and optimize AI spending with security scanning.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">
        <Providers>
          <AppLayout>{children}</AppLayout>
        </Providers>
      </body>
    </html>
  )
}
