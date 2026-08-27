"""Seed a set of synthetic `test-*` Flows exercising a range of
branch/merge shapes, for manually spot-checking the ELK autolayout
algorithm. Every step is a plain, non-entity-backed "Step" node (no
`entity_ref`/`query_ref`/`event_ref`/`external_label`) so this needs no
other seeded catalog data — just a home System, created here if missing.

Non-destructive and re-runnable: only the `test-*` Flows on the dedicated
`elk-layout-tests` System are replaced; nothing else in the database is touched.
"""

from atlas_plugin_flows.models import Flow
from atlas_plugin_standard_catalog.models import GroupDetails, SystemDetails
from django.core.management.base import BaseCommand
from django.db import transaction

from server.apps.catalog.models import KIND_GROUP, KIND_SYSTEM, CatalogEntity

TEST_SYSTEM_NAME = "elk-layout-tests"
TEST_GROUP_NAME = "elk-layout-tests-owner"


def _step(
    step_id: str,
    title: str,
    next_step: str | None = None,
    next_steps: list[tuple[str, str]] | None = None,
) -> dict:
    """One plain Step node. `next_steps`, if given, is a list of
    (target_id, label) pairs."""
    step = {"id": step_id, "title": title}
    if next_step is not None:
        step["next_step"] = {"id": next_step}
    if next_steps is not None:
        step["next_steps"] = [
            {"id": target, "label": label} for target, label in next_steps
        ]
    return step


def _chain(ids: list[str], label_prefix: str = "Step") -> list[dict]:
    """A simple linear chain over `ids`, each titled `{label_prefix} {i}`."""
    steps = []
    for index, step_id in enumerate(ids):
        next_step = ids[index + 1] if index + 1 < len(ids) else None
        steps.append(
            _step(step_id, f"{label_prefix} {index + 1}", next_step=next_step)
        )
    return steps


FLOWS = [
    {
        "name": "test-linear-6",
        "description": "Plain 6-step linear chain, no branching.",
        "steps": _chain([f"s{i}" for i in range(1, 7)]),
    },
    {
        "name": "test-linear-12-deep",
        "description": (
            "Long, narrow 12-step linear chain — tests spacing on a deep "
            "single-column flow."
        ),
        "steps": _chain([f"s{i}" for i in range(1, 13)]),
    },
    {
        "name": "test-single-node",
        "description": (
            "A single, unconnected step — the degenerate one-node case."
        ),
        "steps": [_step("s1", "Lone Step")],
    },
    {
        "name": "test-diamond-2way",
        "description": (
            "Classic diamond: one root fans out to 2 parallel steps that "
            "reconverge on one merge step."
        ),
        "steps": [
            _step("a", "Root", next_steps=[("b", "path 1"), ("c", "path 2")]),
            _step("b", "Branch 1", next_step="d"),
            _step("c", "Branch 2", next_step="d"),
            _step("d", "Merge"),
        ],
    },
    {
        "name": "test-triangle-fanout-3",
        "description": (
            "One root fans out to 3 parallel steps that all reconverge "
            "on one merge step."
        ),
        "steps": [
            _step(
                "a",
                "Root",
                next_steps=[("b", "path 1"), ("c", "path 2"), ("d", "path 3")],
            ),
            _step("b", "Branch 1", next_step="e"),
            _step("c", "Branch 2", next_step="e"),
            _step("d", "Branch 3", next_step="e"),
            _step("e", "Merge"),
        ],
    },
    {
        "name": "test-fanout-6-wide",
        "description": (
            "One root fans out to 6 parallel steps that all reconverge on "
            "one merge step — a wide single-stage fan."
        ),
        "steps": [
            _step(
                "a",
                "Root",
                next_steps=[(f"b{i}", f"path {i}") for i in range(1, 7)],
            ),
            *[
                _step(f"b{i}", f"Branch {i}", next_step="z")
                for i in range(1, 7)
            ],
            _step("z", "Merge"),
        ],
    },
    {
        "name": "test-uneven-branch-lengths",
        "description": (
            "Two branches of very different length (1 step vs. 4 steps) "
            "reconverging on a shared merge step."
        ),
        "steps": [
            _step(
                "a",
                "Root",
                next_steps=[("b1", "short path"), ("c1", "long path")],
            ),
            _step("b1", "Short Branch", next_step="z"),
            _step("c1", "Long Branch 1", next_step="c2"),
            _step("c2", "Long Branch 2", next_step="c3"),
            _step("c3", "Long Branch 3", next_step="c4"),
            _step("c4", "Long Branch 4", next_step="z"),
            _step("z", "Merge"),
        ],
    },
    {
        "name": "test-nested-diamonds",
        "description": (
            "A diamond whose merge step immediately opens into a second "
            "diamond — nested reconvergence."
        ),
        "steps": [
            _step("a", "Root", next_steps=[("b", "path 1"), ("c", "path 2")]),
            _step("b", "Branch 1", next_step="d"),
            _step("c", "Branch 2", next_step="d"),
            _step(
                "d", "Mid Merge", next_steps=[("e", "path 1"), ("f", "path 2")]
            ),
            _step("e", "Branch 3", next_step="g"),
            _step("f", "Branch 4", next_step="g"),
            _step("g", "Final Merge"),
        ],
    },
    {
        "name": "test-3-stage-diamonds",
        "description": (
            "Three diamonds chained end to end — repeated "
            "diverge/reconverge across multiple stages."
        ),
        "steps": [
            _step("a", "Root", next_steps=[("b1", "path 1"), ("b2", "path 2")]),
            _step("b1", "Stage 1 Branch A", next_step="c"),
            _step("b2", "Stage 1 Branch B", next_step="c"),
            _step(
                "c", "Merge 1", next_steps=[("d1", "path 1"), ("d2", "path 2")]
            ),
            _step("d1", "Stage 2 Branch A", next_step="e"),
            _step("d2", "Stage 2 Branch B", next_step="e"),
            _step(
                "e", "Merge 2", next_steps=[("f1", "path 1"), ("f2", "path 2")]
            ),
            _step("f1", "Stage 3 Branch A", next_step="g"),
            _step("f2", "Stage 3 Branch B", next_step="g"),
            _step("g", "Final Merge"),
        ],
    },
    {
        "name": "test-4way-multisource-merge",
        "description": (
            "Four independent 2-step chains with no common ancestor, all "
            "reconverging on one shared final step."
        ),
        "steps": [
            *[
                step
                for i in range(1, 5)
                for step in [
                    _step(f"r{i}a", f"Root {i}", next_step=f"r{i}b"),
                    _step(f"r{i}b", f"Root {i} Step 2", next_step="z"),
                ]
            ],
            _step("z", "Shared Final Step"),
        ],
    },
    {
        "name": "test-branch-within-branch",
        "description": (
            "A 5-way fan-out where two of the five branches themselves "
            "fan out again before every branch reconverges on one shared "
            "merge step."
        ),
        "steps": [
            _step(
                "a",
                "Root",
                next_steps=[(f"b{i}", f"path {i}") for i in range(1, 6)],
            ),
            _step(
                "b1",
                "Branch 1",
                next_steps=[("c1", "sub-path 1"), ("c2", "sub-path 2")],
            ),
            _step(
                "b2",
                "Branch 2",
                next_steps=[("c3", "sub-path 1"), ("c4", "sub-path 2")],
            ),
            _step("b3", "Branch 3", next_step="z"),
            _step("b4", "Branch 4", next_step="z"),
            _step("b5", "Branch 5", next_step="z"),
            _step("c1", "Sub-branch 1", next_step="z"),
            _step("c2", "Sub-branch 2", next_step="z"),
            _step("c3", "Sub-branch 3", next_step="z"),
            _step("c4", "Sub-branch 4", next_step="z"),
            _step("z", "Merge (7 incoming)"),
        ],
    },
    {
        "name": "test-binary-tree-depth3",
        "description": (
            "A full binary tree, 3 levels deep (1 -> 2 -> 4 -> 8), pure "
            "divergence with no reconvergence at all."
        ),
        "steps": [
            _step("r", "Root", next_steps=[("l2a", "left"), ("l2b", "right")]),
            _step(
                "l2a",
                "Level 2 A",
                next_steps=[("l3a", "left"), ("l3b", "right")],
            ),
            _step(
                "l2b",
                "Level 2 B",
                next_steps=[("l3c", "left"), ("l3d", "right")],
            ),
            _step(
                "l3a",
                "Level 3 A",
                next_steps=[("l4a", "left"), ("l4b", "right")],
            ),
            _step(
                "l3b",
                "Level 3 B",
                next_steps=[("l4c", "left"), ("l4d", "right")],
            ),
            _step(
                "l3c",
                "Level 3 C",
                next_steps=[("l4e", "left"), ("l4f", "right")],
            ),
            _step(
                "l3d",
                "Level 3 D",
                next_steps=[("l4g", "left"), ("l4h", "right")],
            ),
            *[_step(f"l4{c}", f"Leaf {c.upper()}") for c in "abcdefgh"],
        ],
    },
    {
        "name": "test-hub-and-spoke",
        "description": (
            "Three independent roots converge on one hub step, which "
            "then diverges out to three independent leaves."
        ),
        "steps": [
            _step("r1", "Root 1", next_step="hub"),
            _step("r2", "Root 2", next_step="hub"),
            _step("r3", "Root 3", next_step="hub"),
            _step(
                "hub",
                "Hub",
                next_steps=[
                    ("l1", "leaf 1"),
                    ("l2", "leaf 2"),
                    ("l3", "leaf 3"),
                ],
            ),
            _step("l1", "Leaf 1"),
            _step("l2", "Leaf 2"),
            _step("l3", "Leaf 3"),
        ],
    },
    {
        "name": "test-skip-level-bypass",
        "description": (
            "A 6-step linear chain plus one extra edge from step 2 "
            "straight to step 5 — a long-range bypass reconverging "
            "several ranks ahead."
        ),
        "steps": [
            _step("s1", "Step 1", next_step="s2"),
            _step(
                "s2",
                "Step 2",
                next_steps=[("s3", "normal path"), ("s5", "bypass")],
            ),
            _step("s3", "Step 3", next_step="s4"),
            _step("s4", "Step 4", next_step="s5"),
            _step("s5", "Step 5 (reconverge)", next_step="s6"),
            _step("s6", "Step 6"),
        ],
    },
    {
        "name": "test-lattice-3x3",
        "description": (
            "A dense 3x3 crisscrossing lattice (3 stages of 3 nodes, each "
            "cross-connected to 2 nodes in the next stage) — stresses "
            "edge-crossing minimization."
        ),
        "steps": [
            _step("a1", "Stage 1 - A", next_steps=[("b1", ""), ("b2", "")]),
            _step("a2", "Stage 1 - B", next_steps=[("b2", ""), ("b3", "")]),
            _step("a3", "Stage 1 - C", next_steps=[("b1", ""), ("b3", "")]),
            _step("b1", "Stage 2 - A", next_steps=[("c1", ""), ("c2", "")]),
            _step("b2", "Stage 2 - B", next_steps=[("c2", ""), ("c3", "")]),
            _step("b3", "Stage 2 - C", next_steps=[("c1", ""), ("c3", "")]),
            _step("c1", "Stage 3 - A"),
            _step("c2", "Stage 3 - B"),
            _step("c3", "Stage 3 - C"),
        ],
    },
    {
        "name": "test-disconnected-pair",
        "description": (
            "Two entirely separate linear chains with no connection "
            "between them, inside one Flow — tests layout of "
            "disconnected components."
        ),
        "steps": [
            *_chain(["p1", "p2", "p3"], label_prefix="Chain A Step"),
            *_chain(["q1", "q2", "q3", "q4"], label_prefix="Chain B Step"),
        ],
    },
]


class Command(BaseCommand):
    help = (
        "Seed synthetic test-* Flows (plain Step nodes only) covering a "
        "range of branch/merge shapes, for exercising the ELK autolayout "
        "algorithm."
    )

    def handle(self, *args, **options) -> None:
        with transaction.atomic():
            owner = self._get_or_create_owner_group()
            system = self._get_or_create_system(owner)
            self._create_flows(system)

    def _get_or_create_owner_group(self) -> CatalogEntity:
        # Every System is expected to carry a non-null `owner` — the System
        # kind handler's `serialize_details` reads `entity.owner.ref`
        # unconditionally, so an ownerless System breaks the whole
        # `/api/systems/` list endpoint, not just its own row.
        group = CatalogEntity.objects.filter(
            kind=KIND_GROUP, name=TEST_GROUP_NAME
        ).first()
        if group is not None:
            return group

        group = CatalogEntity.objects.create(
            kind=KIND_GROUP,
            name=TEST_GROUP_NAME,
            title="ELK Layout Tests Owner",
            description=(
                "Owning team for the synthetic elk-layout-tests System."
            ),
        )
        GroupDetails.objects.create(entity=group, type="team")
        self.stdout.write(f"Created group {TEST_GROUP_NAME!r}")
        return group

    def _get_or_create_system(self, owner: CatalogEntity) -> CatalogEntity:
        system = CatalogEntity.objects.filter(
            kind=KIND_SYSTEM, name=TEST_SYSTEM_NAME
        ).first()
        if system is not None:
            if system.owner_id != owner.id:
                system.owner = owner
                system.save(update_fields=["owner"])
            self.stdout.write(f"Reusing existing system {TEST_SYSTEM_NAME!r}")
            return system

        system = CatalogEntity.objects.create(
            kind=KIND_SYSTEM,
            name=TEST_SYSTEM_NAME,
            title="ELK Layout Tests",
            owner=owner,
            description=(
                "Synthetic system holding test-* Flows used to exercise "
                "the ELK autolayout algorithm against a range of "
                "branch/merge shapes."
            ),
        )
        SystemDetails.objects.create(entity=system)
        self.stdout.write(f"Created system {TEST_SYSTEM_NAME!r}")
        return system

    def _create_flows(self, system: CatalogEntity) -> None:
        deleted, _ = Flow.objects.filter(
            system=system, name__startswith="test-"
        ).delete()
        if deleted:
            self.stdout.write(
                f"Removed {deleted} previously-seeded test-* flow(s)"
            )

        for spec in FLOWS:
            Flow.objects.create(
                system=system,
                name=spec["name"],
                description=spec["description"],
                steps=spec["steps"],
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(FLOWS)} test-* flows on {TEST_SYSTEM_NAME!r}"
            )
        )
