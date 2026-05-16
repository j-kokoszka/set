# Project Workflow & Conventions

## Parallel Development with Git Worktrees
To support multiple concurrent tasks (e.g., security hardening and feature development) without workspace interference, follow these rules:

1.  **Isolation via Worktrees**: Always use `git worktree` to create isolated environments for new features or fixes that are being worked on in parallel sessions.
2.  **Naming Convention**: Create worktrees in subdirectories within the project root, using descriptive names (e.g., `feature-name-worktree`).
3.  **Branching**: Every worktree must track a unique feature branch. Never work directly on `main` within a specialized worktree.
4.  **Workflow**:
    *   Create a worktree: `git worktree add <directory-name> -b <branch-name> main`
    *   Perform all work (installing deps, running tests, editing files) within that directory.
    *   Commit and push from within the worktree directory.
5.  **Workspace Protection**: Do not modify files in the project root or switch branches in the root directory if other sessions are active.

## Testing Standards
*   **E2E Testing**: All new features must include Playwright E2E tests located in `frontend/e2e/`.
*   **CI/CD**: The CI/CD pipeline (`.github/workflows/deploy.yml`) requires both unit/backend tests and E2E tests to pass before any infrastructure changes or deployments.
