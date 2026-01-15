'use client'

interface DataPanelProps {
  title?: string
  children: React.ReactNode
  className?: string
}

export default function DataPanel({ title, children, className = '' }: DataPanelProps) {
  return (
    <div className={`border border-terminal-border bg-terminal-bg/50 p-4 my-4 ${className}`}>
      {title && (
        <div className="border-b border-terminal-border pb-2 mb-3">
          <h3 className="text-terminal-fg font-mono text-sm font-semibold">{title}</h3>
        </div>
      )}
      <div className="text-terminal-fg font-mono text-sm">{children}</div>
    </div>
  )
}



