/**
 * Preprocess text to convert various LaTeX math delimiters to $$...$$ and $...$
 * so they can be rendered by remark-math + rehype-katex.
 *
 * Supported input formats:
 *   \[ ... \]  →  $$ ... $$
 *   \( ... \)  →  $ ... $
 *   [ ... ]    →  $$ ... $$  (only when content contains LaTeX commands like \int, \frac, \sum, etc.)
 */
export function preprocessMath(text: string): string {
  if (!text) return text;

  // Step 1: Handle \[...\] (standard LaTeX display math) — no regex, just .split().join()
  text = text.split("\\[").join("$$").split("\\]").join("$$");

  // Step 2: Handle \(...\) (standard LaTeX inline math)
  text = text.split("\\(").join("$").split("\\)").join("$");

  // Step 3: Handle bare [...] where content looks like math (contains \commands)
  // Use a simple indexOf-based approach to avoid complex regex
  let result = "";
  let i = 0;
  while (i < text.length) {
    if (text[i] === "[") {
      const close = text.indexOf("]", i + 1);
      if (close === -1) {
        result += text[i];
        i++;
        continue;
      }
      const content = text.slice(i + 1, close);
      // Check: content contains backslash (LaTeX commands) AND not a markdown link [...](...)
      const isMath = content.includes("\\");
      const isLink = close + 1 < text.length && text[close + 1] === "(";
      if (isMath && !isLink) {
        result += "$$" + content.trim() + "$$";
        i = close + 1;
        continue;
      }
    }
    result += text[i];
    i++;
  }

  return result;
}
