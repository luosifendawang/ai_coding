# Architecture

GitPulse uses a layered architecture:

- CLI layer: argument parsing, display, and confirmation.
- Service layer: business workflows.
- Git layer: subprocess-based Git data access.
- Security layer: file filtering, truncation, scanning, and masking.
- AI layer: provider abstraction and structured response parsing.
- Storage layer: SQLite persistence through repository classes.
- Integrations layer: Feishu application authentication and bot message delivery.
