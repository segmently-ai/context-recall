#!/bin/zsh
# Builds the self-test's synthetic host repository: a small JavaScript service (ES modules, JSDoc types, Node 18+) that books
# lab equipment, with one doc of rules per area (docs/*.md) and a git history of three real tasks. Each task is one
# implementation commit that respects the docs' rules; lightweight tags name the commits the cases pin: d01-before, d01,
# d02-before, d02, d03-before, d03. Fixed author, committer and dates make every build produce the same commits.
# Usage: make_demo_repo.sh <new dir>
set -eu
R=$1
[ -e $R ] && { echo "$R exists" >&2; exit 2; }
mkdir -p $R && cd $R
git init -q
export GIT_AUTHOR_NAME=demo GIT_AUTHOR_EMAIL=demo@example.com GIT_COMMITTER_NAME=demo GIT_COMMITTER_EMAIL=demo@example.com
n=0
commit() {   # message; every commit one day after the last, at noon UTC
  n=$((n + 1)); export GIT_AUTHOR_DATE="2026-01-0${n}T12:00:00Z" GIT_COMMITTER_DATE="2026-01-0${n}T12:00:00Z"
  git add -A && git -c commit.gpgsign=false commit -q --no-verify -m "$1"
}
mkdir -p docs src/api src/reservations src/equipment src/audit src/mailer tests tasks
task_file() {   # <id> <title> <read paths, space-separated or ""> <run text>: the operator's task file, written before the work
  { print -r -- "# Task: $2"; print
    [ -n "$3" ] && { print -r -- "## Read"; print; for p in ${(s: :)3}; do print -r -- $p; done; print; }
    print -r -- "## Run"; print; print -r -- "$4"; } > tasks/$1.md
}

# ---- the base: the service, its docs and tests ----
cat > README.md <<'EOF'
# labdesk

Book lab equipment by the hour. Members book and cancel their own slots; admins manage every booking and the equipment
registry. Plain JavaScript (ES modules, JSDoc types), no framework: handlers in `src/api/`, one folder per area, the rules
of each area in `docs/`.
EOF
cat > CLAUDE.md <<'EOF'
# Notes for coding agents

This repository is a small JavaScript service that books lab equipment. Docs with the rules of each area are in `docs/`.
Run the tests with `npm test`. Keep changes small and covered by a test.
EOF
cat > package.json <<'EOF'
{
  "name": "labdesk",
  "private": true,
  "type": "module",
  "scripts": { "test": "node --test" }
}
EOF
cat > docs/reservations.md <<'EOF'
# Reservations

A reservation books one piece of equipment for a time slot. The code lives in `src/reservations/`.

## Rules

- A slot is end-exclusive, [start, end): two slots overlap only when a.start < b.end and b.start < a.end.
- Never compare times as local `Date` objects; every time is a UTC ISO string and is compared with `toMillis()`.
- Never change a stored reservation in place; every change goes through `ReservationService`, which checks overlaps.
- A cancelled reservation is never deleted: set `status = "cancelled"` so the audit trail stays complete.
EOF
cat > docs/api.md <<'EOF'
# API handlers

Handlers live in `src/api/handlers.js`, one function per route.

## Rules

- Every handler parses its input with `parse()` from `src/api/schema.js`; never read `req.body` fields directly.
- A handler never throws: it returns `{ status, body }`, and an error body is `{ error: <code> }` with a code from `ERRORS`.
- Only the handler checks permissions: a member may change only their own reservations; an admin may change any.
EOF
cat > docs/audit.md <<'EOF'
# Audit

Every state change of a reservation is recorded for the lab's safety log.

## Rules

- Every state change calls `audit.record(action, reservationId, actorId)` after the change is stored, never before.
- Never write to `auditLog` directly; it is append-only and only `audit.record` appends to it.
EOF
cat > docs/mailer.md <<'EOF'
# Mailer

Mail goes out from a background worker that drains the queue.

## Rules

- Never send mail inside a request handler or a service call; push a job with `mailQueue.push(template, to, data)`.
- Every kind of mail is a template in `src/mailer/templates.js`; never build mail text inline.
EOF
cat > docs/equipment.md <<'EOF'
# Equipment

The registry of lab equipment, in `src/equipment/registry.js`.

## Rules

- Equipment is keyed by its slug (`"microscope-2"`); never key a map or a lookup by the display name, which staff rename.
- Retired equipment stays in the registry with `retired: true`; lists for members hide it, lists for admins show it.
EOF
cat > src/reservations/reservation.js <<'EOF'
/**
 * @typedef {"active" | "cancelled"} Status
 * @typedef {{ id: string, equipmentId: string, memberId: string, start: string, end: string, status: Status }} Reservation
 * start and end are UTC ISO strings; end is exclusive.
 */

/** @param {string} iso */
export function toMillis(iso) {
  return Date.parse(iso);
}

/** @param {{start: string, end: string}} a @param {{start: string, end: string}} b */
export function overlaps(a, b) {
  return toMillis(a.start) < toMillis(b.end) && toMillis(b.start) < toMillis(a.end);
}
EOF
cat > src/reservations/service.js <<'EOF'
import { overlaps } from "./reservation.js";
import { audit } from "../audit/audit.js";

/** @typedef {import("./reservation.js").Reservation} Reservation */

export class ReservationService {
  /** @type {Map<string, Reservation>} */
  #items = new Map();
  #seq = 0;

  /** @param {string} equipmentId @returns {Reservation[]} */
  list(equipmentId) {
    return [...this.#items.values()].filter((r) => r.equipmentId === equipmentId && r.status === "active");
  }

  /** @param {string} id */
  get(id) {
    return this.#items.get(id);
  }

  /** @returns {Reservation | "overlap"} */
  create(equipmentId, memberId, start, end) {
    if (this.list(equipmentId).some((r) => overlaps(r, { start, end }))) return "overlap";
    const r = { id: `r${++this.#seq}`, equipmentId, memberId, start, end, status: "active" };
    this.#items.set(r.id, r);
    audit.record("create", r.id, memberId);
    return r;
  }

  /** @returns {Reservation | "not_found"} */
  cancel(id, actorId) {
    const r = this.#items.get(id);
    if (!r) return "not_found";
    r.status = "cancelled";
    audit.record("cancel", id, actorId);
    return r;
  }
}
EOF
cat > src/audit/audit.js <<'EOF'
/** @typedef {{ at: string, action: string, reservationId: string, actorId: string }} AuditEntry */

/** @type {AuditEntry[]} */
const auditLog = [];

export const audit = {
  /** @param {string} action @param {string} reservationId @param {string} actorId */
  record(action, reservationId, actorId) {
    auditLog.push({ at: new Date().toISOString(), action, reservationId, actorId });
  },
  /** @returns {readonly AuditEntry[]} */
  entries() {
    return auditLog;
  },
};
EOF
cat > src/mailer/templates.js <<'EOF'
/** @type {Record<string, (d: Record<string, string>) => string>} */
export const TEMPLATES = {
  reservationCreated: (d) => `Your booking of ${d.equipment} starts at ${d.start}.`,
};
EOF
cat > src/mailer/queue.js <<'EOF'
import { TEMPLATES } from "./templates.js";

/** @typedef {{ template: string, to: string, data: Record<string, string> }} MailJob */

/** @type {MailJob[]} */
const jobs = [];

export const mailQueue = {
  /** @param {string} template @param {string} to @param {Record<string, string>} data */
  push(template, to, data) {
    jobs.push({ template, to, data });
  },
  drain() {
    return jobs.splice(0, jobs.length);
  },
};

/** The worker's send step: it runs outside requests, after drain(). @param {MailJob} job */
export function sendNow(job) {
  console.log(`mail to ${job.to}: ${TEMPLATES[job.template](job.data)}`);
}
EOF
cat > src/equipment/registry.js <<'EOF'
/** @typedef {{ slug: string, name: string, retired: boolean }} Equipment */

/** @type {Equipment[]} */
const items = [
  { slug: "microscope-1", name: "Microscope A", retired: false },
  { slug: "microscope-2", name: "Microscope B", retired: false },
  { slug: "centrifuge-1", name: "Old centrifuge", retired: true },
];

export const registry = {
  /** @param {string} slug */
  bySlug(slug) {
    return items.find((e) => e.slug === slug);
  },
  all() {
    return [...items];
  },
};
EOF
cat > src/api/schema.js <<'EOF'
/**
 * The fields a handler expects, each "string" or "iso" (a UTC ISO time). Returns the parsed fields, or null.
 * @param {unknown} body @param {Record<string, "string" | "iso">} fields @returns {Record<string, string> | null}
 */
export function parse(body, fields) {
  if (typeof body !== "object" || body === null) return null;
  /** @type {Record<string, string>} */
  const out = {};
  for (const [key, kind] of Object.entries(fields)) {
    const v = /** @type {Record<string, unknown>} */ (body)[key];
    if (typeof v !== "string") return null;
    if (kind === "iso" && Number.isNaN(Date.parse(v))) return null;
    out[key] = v;
  }
  return out;
}
EOF
cat > src/api/handlers.js <<'EOF'
import { parse } from "./schema.js";
import { ReservationService } from "../reservations/service.js";
import { registry } from "../equipment/registry.js";

/** @typedef {{ body: unknown, user: { id: string, email: string, admin: boolean } }} Req */
/** @typedef {{ status: number, body: unknown }} Res */

export const ERRORS = { bad_input: 400, forbidden: 403, not_found: 404, overlap: 409 };

/** @param {keyof typeof ERRORS} code @returns {Res} */
const fail = (code) => ({ status: ERRORS[code], body: { error: code } });
export const service = new ReservationService();

/** @param {Req} req @returns {Res} */
export function createReservation(req) {
  const input = parse(req.body, { equipment: "string", start: "iso", end: "iso" });
  if (!input) return fail("bad_input");
  if (!registry.bySlug(input.equipment)) return fail("not_found");
  const r = service.create(input.equipment, req.user.id, input.start, input.end);
  return r === "overlap" ? fail("overlap") : { status: 201, body: r };
}

/** @param {Req} req @returns {Res} */
export function cancelReservation(req) {
  const input = parse(req.body, { id: "string" });
  if (!input) return fail("bad_input");
  const r = service.get(input.id);
  if (!r) return fail("not_found");
  if (r.memberId !== req.user.id && !req.user.admin) return fail("forbidden");
  const done = service.cancel(input.id, req.user.id);
  return done === "not_found" ? fail("not_found") : { status: 200, body: done };
}

/** @param {Req} req @returns {Res} */
export function listEquipment(req) {
  return { status: 200, body: registry.all() };
}
EOF
cat > tests/reservations.test.js <<'EOF'
import { test } from "node:test";
import assert from "node:assert/strict";
import { ReservationService } from "../src/reservations/service.js";

test("back-to-back slots do not overlap", () => {
  const s = new ReservationService();
  assert.notEqual(s.create("microscope-1", "m1", "2026-01-01T10:00:00Z", "2026-01-01T11:00:00Z"), "overlap");
  assert.notEqual(s.create("microscope-1", "m2", "2026-01-01T11:00:00Z", "2026-01-01T12:00:00Z"), "overlap");
});
EOF
cat > tests/api.test.js <<'EOF'
import { test } from "node:test";
import assert from "node:assert/strict";
import { createReservation } from "../src/api/handlers.js";

test("a bad body is a 400", () => {
  const res = createReservation({ body: { equipment: 1 }, user: { id: "m1", email: "m1@lab.test", admin: false } });
  assert.equal(res.status, 400);
});
EOF
# the d01 feature's staged history (the spec-kit layout): its spec, its plan, its tasks, written before the work
mkdir -p specs/001-extend-booking
cat > specs/001-extend-booking/spec.md <<'EOF'
# Feature Specification: Extend a booking

**Input**: User description: "Let a member extend their own booking to a later end time."

## What members need

A member whose experiment runs over makes their booking longer instead of cancelling and booking again. The extension
starts from the booking's current end and may reach the start of the next booking of the same equipment, never beyond.
An admin may extend any booking. Every extension is part of the lab's safety log.
EOF
cat > specs/001-extend-booking/plan.md <<'EOF'
# Plan: Extend a booking

1. The reservation service gains an extend step that checks the longer slot against the other active bookings of the
   same equipment and records the change.
2. A new handler takes the booking and the new end time, checks who may extend it, and maps the service's results to
   error codes.
3. A test shows a booking extends up to the next one but not into it.
EOF
cat > specs/001-extend-booking/tasks.md <<'EOF'
# Tasks: Extend a booking

- [ ] T001 Add the extend step to the reservation service in src/reservations/service.js
- [ ] T002 Add the extendReservation handler in src/api/handlers.js
EOF
task_file d01 "extend a booking" "docs/reservations.md" "Members keep asking to make a booking longer when their experiment runs over. Today they cancel and book again, and sometimes someone else takes the slot in between. Let a member extend their own booking to a later end time."
commit "labdesk: reservations, equipment, audit, mailer"
git tag d01-before

# ---- d01: extend a booking ----
python3 - <<'PY'
from pathlib import Path
p = Path("src/reservations/service.js"); s = p.read_text()
s = s.replace('''  /** @returns {Reservation | "not_found"} */
  cancel(id, actorId) {''', '''  /** @returns {Reservation | "not_found" | "overlap"} */
  extend(id, end, actorId) {
    const r = this.#items.get(id);
    if (!r || r.status !== "active") return "not_found";
    const others = this.list(r.equipmentId).filter((o) => o.id !== id);
    if (others.some((o) => overlaps(o, { start: r.start, end }))) return "overlap";
    r.end = end;
    audit.record("extend", id, actorId);
    return r;
  }

  /** @returns {Reservation | "not_found"} */
  cancel(id, actorId) {''')
p.write_text(s)
p = Path("src/api/handlers.js"); s = p.read_text()
s = s.replace('''/** @param {Req} req @returns {Res} */
export function listEquipment''', '''/** @param {Req} req @returns {Res} */
export function extendReservation(req) {
  const input = parse(req.body, { id: "string", end: "iso" });
  if (!input) return fail("bad_input");
  const r = service.get(input.id);
  if (!r) return fail("not_found");
  if (r.memberId !== req.user.id && !req.user.admin) return fail("forbidden");
  const done = service.extend(input.id, input.end, req.user.id);
  return done === "not_found" || done === "overlap" ? fail(done) : { status: 200, body: done };
}

/** @param {Req} req @returns {Res} */
export function listEquipment''')
p.write_text(s)
p = Path("tests/reservations.test.js")
p.write_text(p.read_text() + '''
test("a booking extends up to the next one, not into it", () => {
  const s = new ReservationService();
  const a = s.create("microscope-1", "m1", "2026-01-01T10:00:00Z", "2026-01-01T11:00:00Z");
  s.create("microscope-1", "m2", "2026-01-01T12:00:00Z", "2026-01-01T13:00:00Z");
  assert.notEqual(s.extend(a.id, "2026-01-01T12:00:00Z", "m1"), "overlap");
  assert.equal(s.extend(a.id, "2026-01-01T12:30:00Z", "m1"), "overlap");
});
''')
PY
commit "Members can extend a booking"
git tag d01
task_file d02 "mail on cancel" "src/mailer/queue.js" "When the lab staff cancel someone's booking, the member only finds out when they show up at the bench. Send the member an email when an admin cancels their booking."
commit "Task: mail on cancel"
git tag d02-before

# ---- d02: mail the member when an admin cancels their booking ----
python3 - <<'PY'
from pathlib import Path
p = Path("src/mailer/templates.js"); s = p.read_text()
s = s.replace('''  reservationCreated: (d) => `Your booking of ${d.equipment} starts at ${d.start}.`,''',
'''  reservationCreated: (d) => `Your booking of ${d.equipment} starts at ${d.start}.`,
  reservationCancelledByAdmin: (d) => `Your booking of ${d.equipment} at ${d.start} was cancelled by the lab.`,''')
p.write_text(s)
p = Path("src/api/handlers.js"); s = p.read_text()
s = s.replace('''import { registry } from "../equipment/registry.js";''', '''import { registry } from "../equipment/registry.js";
import { mailQueue } from "../mailer/queue.js";''')
s = s.replace('''  const done = service.cancel(input.id, req.user.id);
  return done === "not_found" ? fail("not_found") : { status: 200, body: done };''', '''  const done = service.cancel(input.id, req.user.id);
  if (done === "not_found") return fail("not_found");
  if (done.memberId !== req.user.id) {
    mailQueue.push("reservationCancelledByAdmin", memberEmail(done.memberId), { equipment: done.equipmentId, start: done.start });
  }
  return { status: 200, body: done };''')
s = s.replace('''/** @param {Req} req @returns {Res} */
export function listEquipment''', '''/** @param {string} memberId */
export const memberEmail = (memberId) => `${memberId}@lab.test`;

/** @param {Req} req @returns {Res} */
export function listEquipment''')
p.write_text(s)
p = Path("tests/api.test.js")
p.write_text(p.read_text().replace('import { createReservation } from "../src/api/handlers.js";',
  'import { cancelReservation, createReservation } from "../src/api/handlers.js";\nimport { mailQueue } from "../src/mailer/queue.js";') + '''
test("an admin's cancel queues a mail to the member", () => {
  const made = createReservation({ body: { equipment: "microscope-2", start: "2026-02-01T10:00:00Z", end: "2026-02-01T11:00:00Z" },
    user: { id: "m1", email: "m1@lab.test", admin: false } });
  cancelReservation({ body: { id: made.body.id }, user: { id: "a1", email: "a1@lab.test", admin: true } });
  assert.equal(mailQueue.drain()[0]?.template, "reservationCancelledByAdmin");
});
''')
PY
commit "Mail the member when the lab cancels their booking"
git tag d02
task_file d03 "retired equipment" "" "Members see old equipment we no longer use in the booking list and try to book it. Also the list comes in a random order; show it alphabetically."
commit "Task: retired equipment"
git tag d03-before

# ---- d03: members no longer see retired equipment; the list is sorted by name ----
python3 - <<'PY'
from pathlib import Path
p = Path("src/api/handlers.js"); s = p.read_text()
s = s.replace('''export function listEquipment(req) {
  return { status: 200, body: registry.all() };
}''', '''export function listEquipment(req) {
  const shown = registry.all().filter((e) => req.user.admin || !e.retired);
  return { status: 200, body: shown.sort((a, b) => a.name.localeCompare(b.name)) };
}''')
p.write_text(s)
p = Path("tests/api.test.js")
p.write_text(p.read_text().replace('import { cancelReservation, createReservation } from "../src/api/handlers.js";',
  'import { cancelReservation, createReservation, listEquipment } from "../src/api/handlers.js";') + '''
test("members do not see retired equipment; admins do", () => {
  const member = listEquipment({ body: {}, user: { id: "m1", email: "m1@lab.test", admin: false } }).body;
  const admin = listEquipment({ body: {}, user: { id: "a1", email: "a1@lab.test", admin: true } }).body;
  assert.ok(!member.some((e) => e.slug === "centrifuge-1"));
  assert.ok(admin.some((e) => e.slug === "centrifuge-1"));
});
''')
PY
commit "Hide retired equipment from members; sort the list by name"
git tag d03
echo "demo repository: $R ($(git rev-list --count HEAD) commits; tags $(git tag | tr '\n' ' '))"
