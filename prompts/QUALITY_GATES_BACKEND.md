# Backend Quality Gates (Must Pass)

Use this checklist before declaring completion:

## Architecture
- [ ] Separation of concerns maintained
- [ ] No tight coupling introduced
- [ ] Config externalized

## API Quality
- [ ] Input validation enforced
- [ ] Stable response contract
- [ ] Proper HTTP status codes
- [ ] Consistent error schema

## Security
- [ ] AuthN/AuthZ checks correct
- [ ] Secrets not hardcoded
- [ ] Injection-safe data access
- [ ] Rate limit / abuse controls considered

## Data Layer
- [ ] Migrations reversible (if possible)
- [ ] Indexes for critical queries
- [ ] Transaction boundaries correct

## Reliability
- [ ] Retries/timeouts where needed
- [ ] Idempotency for retriable endpoints/jobs
- [ ] Failure paths handled

## Observability
- [ ] Structured logs at key points
- [ ] Metrics/trace points for critical flows
- [ ] Actionable error messages

## Testing
- [ ] Unit tests for core logic
- [ ] Integration tests for DB/API behavior
- [ ] Regression test for bug fixes

## Delivery
- [ ] Lint/build passes
- [ ] Changelog/notes updated (if needed)
- [ ] Rollback plan mentioned for risky changes
