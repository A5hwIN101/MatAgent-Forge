'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import DataPanel from './DataPanel'

interface MarkdownRendererProps {
  content: string
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // Style tables with retro theme
        table: ({ children }) => (
          <div className="overflow-x-auto my-4">
            <table className="border-collapse border border-terminal-border w-full">
              {children}
            </table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-terminal-border/30">{children}</thead>
        ),
        tbody: ({ children }) => (
          <tbody>{children}</tbody>
        ),
        tr: ({ children }) => (
          <tr className="border-b border-terminal-border hover:bg-terminal-border/10">
            {children}
          </tr>
        ),
        th: ({ children }) => (
          <th className="border border-terminal-border px-4 py-2 text-left font-semibold text-terminal-fg">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="border border-terminal-border px-4 py-2 text-terminal-fg">
            {children}
          </td>
        ),
        // Style headings
        h1: ({ children }) => (
          <h1 className="text-2xl font-bold mt-6 mb-4 text-terminal-fg">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-xl font-bold mt-5 mb-3 text-terminal-fg">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-lg font-semibold mt-4 mb-2 text-terminal-fg">{children}</h3>
        ),
        // Style lists
        ul: ({ children }) => (
          <ul className="list-disc list-inside my-3 space-y-1 text-terminal-fg">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal list-inside my-3 space-y-1 text-terminal-fg">{children}</ol>
        ),
        li: ({ children }) => (
          <li className="ml-4">{children}</li>
        ),
        // Style paragraphs
        p: ({ children }) => (
          <p className="my-2 text-terminal-fg leading-relaxed">{children}</p>
        ),
        // Style code blocks
        code: ({ className, children, ...props }) => {
          const isInline = !className
          return isInline ? (
            <code className="bg-terminal-border/30 px-1 py-0.5 rounded text-terminal-fg" {...props}>
              {children}
            </code>
          ) : (
            <code className={className} {...props}>
              {children}
            </code>
          )
        },
        pre: ({ children }) => (
          <pre className="bg-terminal-border/20 p-4 rounded my-4 overflow-x-auto border border-terminal-border">
            {children}
          </pre>
        ),
        // Style blockquotes
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-terminal-border pl-4 my-4 italic text-terminal-fg/80">
            {children}
          </blockquote>
        ),
        // Style strong/bold
        strong: ({ children }) => (
          <strong className="font-semibold text-terminal-fg">{children}</strong>
        ),
        // Style emphasis/italic
        em: ({ children }) => (
          <em className="italic text-terminal-fg">{children}</em>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  )
}



