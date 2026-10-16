# memory/README.md template

Write this as `memory/README.md`, unchanged apart from the spelling choice.

```markdown
# Memory

What Claude and I have learned about running this business, written down so nobody has to
explain it twice. Plain markdown, one file per thing, named so a search finds it.

## decisions/

One file per decision that should outlast the conversation it was made in.
Name: `YYYY-MM-DD-short-title.md`.

    # Short title
    Date: YYYY-MM-DD
    Decision: one sentence.
    Why: one to three sentences.
    Revisit: a date or a trigger ("if refunds pass 5% of orders"), or "never".

Check here before proposing anything that might contradict a decision. To reverse one,
write a new file that says which one it replaces; do not edit history.

## people/

One file per customer, supplier or teammate who comes up more than once.
Name: `firstname-lastname.md` or `company-name.md`.

    # Name
    Role: customer / supplier / teammate, and what they do.
    Prefers: how they like to be contacted, tone, timing.
    History: dated one-liners, newest first.

Only what helps the next conversation. Nothing sensitive that they would not expect a
small business to keep (no health details, no personal finances, no ID numbers).

## playbooks/

One file per process that happens more than twice. Write it from a real run, not from
memory of how it should go.
Name: `verb-noun.md`, for example `send-monthly-invoices.md`.

    # Send monthly invoices
    Owner: who runs it.   When: trigger or schedule.   Review: date.
    Steps: numbered, one action each, with the tool named.
    Done when: the check that proves it worked.

## reviews/

The Friday weekly reviews, one file per week: `YYYY-MM-DD.md`. Created by the
weekly-review routine; no need to make it by hand.
```
