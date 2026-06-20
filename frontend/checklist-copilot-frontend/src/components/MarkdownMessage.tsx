import styles from './MarkdownMessage.module.css'

type MarkdownMessageProps = {
  text: string
}

type MarkdownBlock =
  | { type: 'heading'; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'unorderedList'; items: string[] }
  | { type: 'orderedList'; items: string[] }

// Renders the small markdown subset typically returned by the LLM in chat replies.
// It intentionally avoids a dependency while supporting headings, paragraphs, and lists.
export function MarkdownMessage({ text }: MarkdownMessageProps) {
  const blocks = parseMarkdownBlocks(text)

  return (
    <div className={styles.markdownMessage}>
      {blocks.map((block, index) => renderBlock(block, index))}
    </div>
  )
}

function renderBlock(block: MarkdownBlock, index: number) {
  if (block.type === 'heading') return <h3 key={index}>{renderInlineMarkdown(block.text)}</h3>
  if (block.type === 'unorderedList') return <ul key={index}>{block.items.map(renderListItem)}</ul>
  if (block.type === 'orderedList') return <ol key={index}>{block.items.map(renderListItem)}</ol>

  return <p key={index}>{renderInlineMarkdown(block.text)}</p>
}

function renderListItem(item: string, index: number) {
  return <li key={`${item}-${index}`}>{renderInlineMarkdown(item)}</li>
}

function parseMarkdownBlocks(rawText: string): MarkdownBlock[] {
  const lines = normalizeMarkdownText(rawText).split('\n')
  const blocks: MarkdownBlock[] = []
  let paragraph: string[] = []
  let unorderedItems: string[] = []
  let orderedItems: string[] = []

  function flushParagraph() {
    if (paragraph.length === 0) return
    blocks.push({ type: 'paragraph', text: paragraph.join(' ') })
    paragraph = []
  }

  function flushLists() {
    if (unorderedItems.length > 0) blocks.push({ type: 'unorderedList', items: unorderedItems })
    if (orderedItems.length > 0) blocks.push({ type: 'orderedList', items: orderedItems })
    unorderedItems = []
    orderedItems = []
  }

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) {
      flushParagraph()
      flushLists()
      continue
    }

    const heading = line.match(/^#{1,4}\s+(.+)$/)
    if (heading) {
      flushParagraph()
      flushLists()
      blocks.push({ type: 'heading', text: heading[1] })
      continue
    }

    const ordered = line.match(/^\d+[.)]\s+(.+)$/)
    if (ordered) {
      flushParagraph()
      unorderedItems = []
      orderedItems.push(ordered[1])
      continue
    }

    const unordered = line.match(/^[-*]\s+(.+)$/)
    if (unordered) {
      flushParagraph()
      orderedItems = []
      unorderedItems.push(unordered[1])
      continue
    }

    flushLists()
    paragraph.push(line)
  }

  flushParagraph()
  flushLists()
  return blocks.length > 0 ? blocks : [{ type: 'paragraph', text: rawText }]
}

function normalizeMarkdownText(text: string) {
  return text
    .replace(/\s+(#{1,4}\s+)/g, '\n$1')
    .replace(/\s+(\d+[.)]\s+)/g, '\n$1')
    .replace(/\s+([-*]\s+)/g, '\n$1')
}

function renderInlineMarkdown(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, index) => {
    const strong = part.match(/^\*\*([^*]+)\*\*$/)
    return strong ? <strong key={index}>{strong[1]}</strong> : part
  })
}
