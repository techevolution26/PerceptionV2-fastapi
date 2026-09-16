# Discovery 30 — Private Investigation Notebook

## Purpose
Turn an investigation path into a user-owned, private follow-up thread without turning Perception into a task manager or evidence repository.

## Product rule
A saved investigation thread is a user note derived from an existing investigation path. It creates no new evidence and never strengthens the originating observation.

## Lifecycle
- open — saved for later
- in_progress — user is actively investigating
- verified — user records that their independent investigation is complete
- dismissed — user chose not to pursue it

The product does not independently label a question as verified. `verified` is a user-controlled status, not an AI or platform truth claim.

## Privacy
- Threads are private to their owner.
- The API scopes every read/update/delete by authenticated user ID.
- No participant identities or private geographic data are copied into the thread.
- The originating evidence trace ID is retained only as a provenance pointer.

## Evidence boundary
The notebook stores the question, rationale, evidence basis, validation step, and trace pointer supplied by the existing intelligence response. It does not store or manufacture new semantic evidence.

## UX
The notebook is reached from Perception Intelligence and is otherwise a quiet personal workspace. Saving is explicit. Nothing is automatically saved from a conversation.
