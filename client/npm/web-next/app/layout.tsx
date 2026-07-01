import type { Metadata } from 'next';
import { ThemeProvider } from 'next-themes';
import { Providers } from './providers';
import { Header } from '@/components/shell/Header';
import { DetailPanel } from '@/components/shared/DetailPanel';
import '../styles/globals.css';

export const metadata: Metadata = {
  title: 'LoSeMe · Dashboard',
  description: 'Local Semantic Memory — search, ingest, and browse your indexed sources.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="h-screen overflow-hidden">
        <ThemeProvider attribute="data-theme" defaultTheme="dark" enableSystem={false}>
          <Providers>
            <div className="flex h-full flex-col">
              <Header />
              <main className="flex-1 overflow-y-auto">{children}</main>
            </div>
            <DetailPanel />
          </Providers>
        </ThemeProvider>
      </body>
    </html>
  );
}
