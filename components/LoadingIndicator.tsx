'use client'

import { useState, useEffect } from 'react'

const BRAILLE_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
const STATUS_MESSAGES = [
  'Accessing Materials Project...',
  'Normalizing Crystal Structure...',
  'Running Hypothesis Engine...',
  'Streaming Response...',
]

export default function LoadingIndicator() {
  const [brailleFrame, setBrailleFrame] = useState(0)
  const [statusMessage, setStatusMessage] = useState(0)

  // Animate Braille spinner (80ms interval)
  useEffect(() => {
    const interval = setInterval(() => {
      setBrailleFrame((prev) => (prev + 1) % BRAILLE_FRAMES.length)
    }, 80)

    return () => clearInterval(interval)
  }, [])

  // Cycle through status messages (800ms interval)
  useEffect(() => {
    const interval = setInterval(() => {
      setStatusMessage((prev) => (prev + 1) % STATUS_MESSAGES.length)
    }, 800)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex justify-start">
      <div className="bg-terminal-bg border border-terminal-border p-4 rounded">
        <div className="flex items-center gap-3 text-terminal-fg/60">
          <span className="font-mono text-lg">{BRAILLE_FRAMES[brailleFrame]}</span>
          <span className="font-mono text-sm">{STATUS_MESSAGES[statusMessage]}</span>
        </div>
      </div>
    </div>
  )
}



