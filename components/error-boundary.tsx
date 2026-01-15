'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export default class GlobalErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(_: Error): State {
    return { hasError: true };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // 1. Log the REAL error to console for you (Hidden from user)
    console.group("🚨 CRITICAL UI CRASH");
    console.error("Error:", error.message);
    console.error("Stack:", errorInfo.componentStack);
    console.groupEnd();
  }

  public render() {
    if (this.state.hasError) {
      // 2. Show clean UI to user
      return (
        <div className="flex flex-col h-screen w-full items-center justify-center bg-black text-gray-100 p-6 font-sans">
          <div className="max-w-md text-center space-y-6 p-8 border border-gray-800 rounded-2xl bg-gray-900/50 backdrop-blur">
            <div className="mx-auto w-16 h-16 bg-red-900/20 rounded-full flex items-center justify-center border border-red-500/30">
              <AlertTriangle className="w-8 h-8 text-red-500" />
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-semibold text-white">System Encountered an Error</h2>
              <p className="text-gray-400 text-sm leading-relaxed">
                An unexpected condition occurred. The technical details have been logged for review.
              </p>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2.5 bg-white text-black text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors"
            >
              Refresh Application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}