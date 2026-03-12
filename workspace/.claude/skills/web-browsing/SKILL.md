---
name: web-browsing
description: Browse the web using agent-browser CLI. Use for any web task - searching, reading pages, filling forms, extracting data, downloading files, taking screenshots. Triggers on requests like "search the web", "open this URL", "check this website", "fill out this form", "screenshot this page", "download this file", "what does this page say".
---

# Web Browsing with agent-browser

Browse the web, extract data, fill forms, take screenshots, and download files.

## Critical Rules

1. **ALWAYS open + wait before anything else:**
   ```bash
   agent-browser open URL && agent-browser wait --load networkidle
   ```

2. **ALWAYS snapshot before clicking.** Never guess selectors or @refs — they change on every page load:
   ```bash
   agent-browser snapshot -i    # See what's clickable with current @refs
   agent-browser click @e5      # Use the ref you just saw
   ```

3. **ALWAYS wait after navigation** — after clicking a link that loads a new page:
   ```bash
   agent-browser click @e5 && agent-browser wait --load networkidle
   ```

4. **If a click fails, recover with snapshot:**
   ```bash
   # Click failed? Don't retry blindly — take a new snapshot first
   agent-browser snapshot -i    # Re-examine the page, get fresh @refs
   # Then click the correct ref from the new snapshot
   ```

5. **Never use CSS selectors for clicking** — prefer @refs from snapshot

6. **For content extraction, prefer `get text` over snapshot** — it's faster and gives clean text:
   ```bash
   agent-browser get text              # All visible text on the page
   agent-browser get text "main"       # Text within <main> element
   agent-browser get text "article"    # Article content only
   ```

## Standard Pattern for Any Page

Always follow this sequence:

```bash
# Step 1: Open and wait
agent-browser open https://example.com && agent-browser wait --load networkidle

# Step 2: Read content (choose one based on need)
agent-browser get text              # If you just need to read the page
agent-browser snapshot -i           # If you need to interact with elements

# Step 3: Interact (only after snapshot)
agent-browser click @e5             # Use @ref from step 2's snapshot

# Step 4: Wait after any navigation
agent-browser wait --load networkidle

# Step 5: Read the new page
agent-browser get text
```

## Quick Reference

### Navigate and Read

```bash
# Open a URL and wait for it to load
agent-browser open https://example.com && agent-browser wait --load networkidle

# Get the accessibility tree (best for understanding page content)
agent-browser snapshot -i           # Interactive elements only (with @refs)
agent-browser snapshot -c           # Compact (remove empty elements)
agent-browser snapshot              # Full tree

# Get page text or HTML
agent-browser get text              # All visible text
agent-browser get text "article"    # Text within a CSS selector
agent-browser get html ".content"   # HTML of an element
agent-browser get title             # Page title
agent-browser get url               # Current URL
```

### Interact with Pages

```bash
# Click elements (use @ref from snapshot output)
agent-browser click @e5

# Type and fill forms
agent-browser fill @e3 "search query"          # Clear field and type
agent-browser type @e3 "additional text"       # Append text
agent-browser press Enter                      # Press a key
agent-browser select @e4 "option-value"        # Select dropdown

# Find and interact by role/label
agent-browser find role button click --name "Submit"
agent-browser find label "Email" fill "user@example.com"
agent-browser find placeholder "Search..." fill "query"

# Scroll
agent-browser scroll down 500
agent-browser scrollintoview ".footer"
```

### Capture and Save

```bash
# Screenshots
agent-browser screenshot page.png              # Viewport screenshot
agent-browser screenshot --full page.png       # Full page
agent-browser screenshot --annotate page.png   # Labeled with numbered refs

# Save as PDF
agent-browser pdf output.pdf

# Download a file
agent-browser download @e7 /path/to/save/file.pdf
```

### Search the Web

```bash
# Google search workflow
agent-browser open "https://www.google.com/search?q=your+search+query" && agent-browser wait --load networkidle
agent-browser snapshot -i     # See search results with clickable refs
agent-browser click @e12      # Click a result
agent-browser wait --load networkidle
agent-browser get text        # Read the page
```

### Tabs and Sessions

```bash
# Manage tabs
agent-browser tab new          # Open new tab
agent-browser tab list         # List open tabs
agent-browser tab 2            # Switch to tab 2
agent-browser tab close        # Close current tab

# Named sessions (isolated browser contexts)
agent-browser --session research open https://example.com

# Persistent state (cookies, localStorage survive restarts)
agent-browser --session-name myapp open https://example.com
```

## Common Workflows

### Read a news site or article
```bash
agent-browser open https://cnn.com && agent-browser wait --load networkidle
agent-browser get text "main"        # Extract main content directly
# If you need to navigate to a section:
agent-browser snapshot -i            # See navigation links
agent-browser click @e15 && agent-browser wait --load networkidle
agent-browser get text "main"        # Read the new section
```

### Research a topic
```bash
agent-browser open "https://www.google.com/search?q=topic" && agent-browser wait --load networkidle
agent-browser snapshot -i           # Read results
agent-browser click @e8             # Click first result
agent-browser wait --load networkidle
agent-browser get text "article"    # Extract article text
```

### Fill out a form
```bash
agent-browser open https://example.com/form && agent-browser wait --load networkidle
agent-browser snapshot -i                    # See form fields with refs
agent-browser fill @e1 "John Doe"            # Name
agent-browser fill @e2 "john@example.com"    # Email
agent-browser select @e3 "option1"           # Dropdown
agent-browser check @e4                      # Checkbox
agent-browser click @e5                      # Submit button
```

### Extract data from a page
```bash
agent-browser open https://example.com && agent-browser wait --load networkidle
agent-browser get text ".price"              # Get specific element text
agent-browser get attr href "a.link"         # Get link URLs
agent-browser eval "JSON.stringify([...document.querySelectorAll('.item')].map(e => e.textContent))"
```

## Tips

- **Chain commands with `&&`** — the browser daemon persists between commands
- **Use `--headed` to watch** — `agent-browser --headed open url` shows the browser window
- **Screenshots with `--annotate`** — adds numbered labels, useful for visual debugging
- **Save files to `files/`** — screenshots, PDFs, and downloads go in the workspace files directory
- **If a page is slow**, increase the wait: `agent-browser wait 5000` (5 seconds)
- **Modern SPAs may not trigger networkidle** — use `agent-browser wait 3000` as fallback
