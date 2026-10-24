# CSS Insight Engine: Design & Architecture Explanation

### What Was Extracted and Why

We extracted hierarchical rule ASTs (selectors, declarations, and at-rule contexts) alongside source coordinates to preserve the full cascading structure rather than flattening declarations into disconnected property bags.
We extracted custom properties, dimensional tokens (spacing, radii, font sizes), and color expressions to map design system primitives and identify un-tokenized literal repetitions.
We extracted declaration occurrences and `!important` flags in strict document order to detect dead-code shadowing, progressive enhancement fallbacks, and specificity debt.
This structured representation transforms unstructured CSS text into an explainable design intelligence graph that distinguishes intentional compatibility patterns from accidental overrides.

---

### Key Edge Case: Top-Level Selector Splitting vs. Functional Arguments

**The Risk:**  
In CSS, commas demarcate discrete selectors in a list (e.g., `h1, h2, .title`). However, commas also appear inside functional pseudo-classes (e.g., `:is(h1, h2)`, `:not(.a, .b)`), nth-expressions (e.g., `:nth-child(2n+1 of .card, .featured)`), and attribute selectors (e.g., `[data-tags="ai,ml"]`). Naive string splitting on commas or regex heuristics incorrectly fragments these composite selectors, corrupting the rule tree and producing invalid selectors.

**How It Was Handled:**  
Rather than text-based regex, the parser operates directly on `tinycss2`'s Component Value token stream in the rule prelude. Because `tinycss2` automatically balances parentheses, brackets, and strings into composite AST tokens (`FunctionBlock`, `ParenthesesBlock`, `SquareBracketsBlock`), commas inside these constructs are encapsulated as internal children. Our splitter iterates through the top-level token stream and splits *only* on top-level `LiteralToken(',')` nodes. Commas inside `:is(...)` or attribute brackets remain untouched, preserving spec-compliant selector boundaries deterministically.
