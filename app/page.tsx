'use client';

import ChatInterface from '@/components/chat-interface';
import GlobalErrorBoundary from '@/components/error-boundary';

export default function Home() {
  return (
    <GlobalErrorBoundary>
      <ChatInterface />
    </GlobalErrorBoundary>
  );
}