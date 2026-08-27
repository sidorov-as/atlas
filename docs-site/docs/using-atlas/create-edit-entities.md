---
title: Create or edit catalog entities
description: Create owner-scoped manual entities through the supported Atlas UI and maintain Teams and Actors through Django admin.
audience:
  - catalog-user
  - operator
page-type: task
---

# Create or edit catalog entities

Use Atlas's catalog forms for manually maintained Systems, Components,
Resources, and APIs. Teams and Actors are also manual catalog data, but their
supported maintenance surface is Django admin rather than the catalog UI.

## Outcome

You will create or update a supported manual entity, verify its detail and
history, and know which maintenance surface applies to each kind.

## Prerequisites

- You are signed in to Atlas.
- Standard Catalog is selected. Creating APIs additionally requires the APIs
  plugin.
- The owner Team already exists. Components and APIs also require a parent
  System; a Resource may optionally have one.
- To maintain Teams or Actors, you can sign in to `/admin/` and have the
  required Django admin access.

## Permissions

Creating a System, Component, Resource, or API requires either a superuser or
an Actor account that belongs to the selected owner Group. Updating the entity
uses the same ownership rule against its current owner. YAML-managed and
unavailable entities reject manual writes even for a superuser.

Groups (shown as Teams) and Actors have no owner, so the Entity Service accepts
their admin writes only from a superuser. Django admin access by itself does
not bypass that rule. See [Permissions](../concepts/permissions.md).

## Supported maintenance surfaces

| Kind | Supported manual surface | Required kind fields |
| --- | --- | --- |
| System | **Systems** list: **Add System**; detail page: **Edit** | Owner |
| Component | **Components** list: **Add Component**; detail page: **Edit** | Type, lifecycle, owner, System |
| Resource | **Resources** list: **Add Resource**; detail page: **Edit** | Type, owner; System is optional |
| API | **APIs** list: **Add API**; detail page: **Edit** | Type, owner, System; spec source is optional |
| Team (`Group`) | Django admin: **Group details** | Type; members are optional |
| Actor (`User` on the wire) | Django admin: **Actor details** | Display name, email, and login account are optional |

Flows and declared Architecture Relationships are not variants of the shared
entity form. Use [feature-specific catalog views](use-feature-views.md) for
Flows and [Inspect entity details](inspect-entity-details.md#4-distinguish-the-two-relationship-sections)
for relationships.

## 1. Select the owner and parent records

Before opening the form, verify the target Team and, when required, System.
Reference selectors only offer records of the expected kind:

- **Owner** resolves to a Team/Group.
- **System** resolves to a System.
- A Component's **Provides APIs** and **Consumes APIs** selectors resolve to
  APIs; **Depends on** resolves to Resources.

These are catalog references, not free-form labels. If the target does not
exist, create or correct it before continuing. Review
[Entity references](../concepts/entity-references.md) when ownership,
containment, and dependency edges are easy to confuse.

## 2. Open the create form

Open the relevant kind list and select **Add System**, **Add Component**,
**Add Resource**, or **Add API**.

Every form includes this common metadata:

- **Name** — the stable machine name. The catalog UI disables this field after
  creation, so an edit cannot silently change the entity reference.
- **Title**, **Description**, and **Documentation** — human-facing content;
  documentation is Markdown.
- **Tags** — a comma-separated list; whitespace around each value is removed.

Labels and external links are part of the common API/YAML envelope but are not
currently exposed by these manual UI forms.

## 3. Complete the kind-specific fields

### System

Choose the **Owner** Team.

### Component

Choose a type (`service`, `website`, `library`, or `worker`), a lifecycle
(`experimental`, `production`, or `deprecated`), the **Owner**, and the parent
**System**. Optionally select provided APIs, consumed APIs, and Resource
dependencies. These selections become derived Catalog Relations.

### Resource

Choose a type (`database`, `cache`, `bucket`, `queue`, or `cluster`) and the
**Owner**. Choose a **System** only when the Resource belongs to one.

### API

Choose a type (`openapi`, `grpc`, `asyncapi`, or `graphql`), **Owner**, and
**System**. For the specification choose **None**, **Paste text**, or **URL**.
The inline path also accepts an uploaded JSON, YAML, or text file. The
Specification and Operations tabs depend on the type and successfully resolved
content; follow the [APIs guide](../features/apis.md) for
that feature-specific behavior.

## 4. Create and verify

Select **Create**. Atlas returns to the new detail page.

Verify the result after saving:

1. Confirm the title and description in the header.
2. Follow the owner and System links in the **About** rail.
3. Confirm Markdown on **Overview** and the selected tags in the header.
4. Open **Relations** and confirm the expected owner, containment, and
   dependency relations.
5. Open **History** and confirm a **Created** record with the acting account.

## 5. Edit a manual entity

Open the detail page and select **Edit**. Change the supported metadata or
kind-specific fields, then select **Save**. The Name field remains disabled.
Repeat the relevant detail, relation, and History checks.

If **Edit** is absent and the page names a `catalog-info.yaml` repository, the
entity is repository-managed. Use
[Choose the correct entity workflow](choose-entity-workflow.md) instead of
trying to override its provenance.

## 6. Maintain Teams and Actors

Sign in to `/admin/` as a superuser:

1. Open **Group details** to create or edit a Team. Set its machine name,
   optional title and description, type (`team`, `business-unit`,
   `product-area`, or `root`), and Actor members.
2. Open **Actor details** to create or edit a person record. The optional
   **Account** link connects that Actor to a Django login principal used by
   ownership checks.
3. Return to Atlas **Teams**, open the Team, and verify **Members** and the
   owned Systems, Components, Resources, and APIs.

The catalog frontend has no Team or Actor create/edit route. Direct ordinary
catalog users to Django admin instead of a nonexistent **Add Team** control.

## Common problems

### The save says the owner is required

Choose a Team in **Owner**. For a Component or API, also choose a parent
System. A Resource is the only one of these four kinds whose System is
optional.

### The server says you are not a member of the owner Group

Use an owner Team containing your linked Actor, or ask a superuser to perform
the write. Merely being authenticated is enough to read, not to edit.

### The form or detail page is read-only

A `managed by catalog-info.yaml` banner means the repository is authoritative.
An unavailable banner means the kind's plugin is inactive. Correct that source
state; manual forms cannot bypass either restriction.

### A reference cannot be resolved

Confirm that the target exists with the expected kind and machine name. Create
owners and parent Systems first, then retry the form.

### The server rejects a field as too long or too large

Atlas bounds free-text fields and lists. A title is limited to 255 characters, a
description to 4,096, and Markdown documentation to 1 MiB. An entity can carry at most 100
labels, 100 tags, and 50 links; a link URL is limited to 2,048 characters. An inline API
specification or a database schema's SQL source is limited to 2 MiB, and a Flow to 500 steps.
The error names the field that exceeded its limit. Shorten the value or split long
documentation across entities. To load an API specification larger than 2 MiB, publish it at a
`specUrl` instead of pasting it inline.

## Next steps

- [Inspect entity details](inspect-entity-details.md) and confirm the result.
- [Choose the correct entity workflow](choose-entity-workflow.md) before
  switching to repository management or lifecycle actions.
- Use the [HTTP API reference](../api-reference/index.md) for the generated
  create and update operations of the active distribution.
