# shadcn/ui Components List for DataBuddy AI

## Core Layout Components (Required)
- **resizable** - For the 3-panel resizable workspace layout
- **separator** - For visual dividers between panels and sections

## Data Display Components (Required)
- **table** - For displaying database tables and query results
- **card** - For organizing content panels and sections
- **badge** - For status indicators ("System Connected", query status, etc.)

## Form & Input Components (Required)
- **input** - For chat input and terminal-style prompts
- **textarea** - For SQL code display/editing
- **button** - For action buttons (Execute, Clear, etc.)
- **select** - For table selection dropdown in DB Preview panel
- **label** - For form labels

## Navigation & Interaction (Required)
- **scroll-area** - For chat history and SQL code blocks
- **tabs** - Optional: for organizing different views (if needed)

## Feedback & Status Components (Highly Recommended)
- **sonner** - For notifications (success, error, rate limit warnings) - Note: toast is deprecated, use sonner instead
- **alert** - For error messages and warnings
- **alert-dialog** - For confirmation dialogs (e.g., "Execute this SQL?")
- **skeleton** - For loading states while fetching schema/data
- **progress** - For query execution progress indicators

## Advanced Components (Optional but Useful)
- **dialog** - For modal dialogs (settings, help, etc.)
- **dropdown-menu** - For context menus and actions
- **popover** - For tooltips and additional info
- **tooltip** - For hover hints and explanations
- **accordion** - For collapsible schema browser sections
- **sheet** - For side panels (settings, history sidebar)

## Code Display (Optional)
- **code** - For inline code snippets (if not using textarea)

---

## Complete Import Command

Run this command to add all recommended components:

```bash
npx shadcn@latest add resizable separator table card badge input textarea button select label scroll-area tabs sonner alert alert-dialog skeleton progress dialog dropdown-menu popover tooltip accordion sheet
```

## Minimal Essential Set (If you want to start small)

```bash
npx shadcn@latest add resizable table scroll-area input button badge card separator select textarea sonner alert skeleton
```
