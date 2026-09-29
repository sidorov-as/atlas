# catalog-branding Specification

## Purpose

Defines how a deployment sets its catalog identity (title, tagline, logo, and icon) through a single committed frontend configuration file.

## Requirements

### Requirement: Deployment identity is configured via a committed frontend file
The system SHALL source the catalog's title, tagline, logo, and icon from a single committed frontend configuration file (`core/frontend/src/atlas.config.ts`), not from a backend endpoint, environment variable, or database record.

#### Scenario: Header displays the configured identity
- **WHEN** the application shell renders its sidebar header
- **THEN** it shows the title and logo from `atlas.config.ts`, not a hardcoded literal

#### Scenario: Homepage displays the configured identity
- **WHEN** an authenticated user opens the homepage
- **THEN** it shows the title and tagline from `atlas.config.ts`, rendered synchronously with no network request for identity

#### Scenario: Changing branding requires editing the file and rebuilding
- **WHEN** an operator wants to change the catalog's title, tagline, logo, or icon
- **THEN** they edit `atlas.config.ts` and rebuild the frontend; no running deployment can change these values without a rebuild
