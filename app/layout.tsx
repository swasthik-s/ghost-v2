import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'GHOST | Trading Intelligence', description: 'GHOST automated trading and research terminal' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
