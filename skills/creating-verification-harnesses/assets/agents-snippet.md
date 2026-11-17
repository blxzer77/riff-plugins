## Verifying behavior

- Use the project's verify skill (`.agents/skills/verify-<app>/`) to prove a change
  in the running app: Launch, Doctor, Drive the affected feature, keep Evidence,
  Cleanup.
- Never point a verification run at real data or a shared instance.
- If the verify skill fails because the app changed, fix the skill (not the product
  code) and rerun it live.
