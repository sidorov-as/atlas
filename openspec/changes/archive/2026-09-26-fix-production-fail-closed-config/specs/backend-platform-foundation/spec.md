## MODIFIED Requirements

### Requirement: Baseline operational and security configuration
The backend SHALL include health reporting, structured logging, production
serving, security middleware, and explicit SPA session/CSRF configuration.
In a production environment (`DJANGO_ENV=production`), the backend SHALL
fail closed on unsafe or non-functional configuration rather than silently
falling back to development-safe defaults: it SHALL refuse to start with a
missing, placeholder, or insufficiently random `SECRET_KEY`, and it SHALL
NOT allow password-recovery to silently discard mail through a non-functional
mail backend.

#### Scenario: Health endpoint is available
- **WHEN** the backend service runs
- **THEN** its health endpoint reports success

#### Scenario: SPA session request remains valid
- **WHEN** the SPA sends an authenticated unsafe request from a configured origin
- **THEN** CSRF and origin validation accept the valid request

#### Scenario: Production startup rejects an unset or placeholder secret key
- **WHEN** the backend starts with `DJANGO_ENV=production` and `DJANGO_SECRET_KEY`
  is unset, equal to a known example/placeholder value, or shorter than the
  configured minimum length
- **THEN** startup fails with an error identifying the invalid setting, rather
  than falling back to a development secret

#### Scenario: Production startup accepts an explicit, sufficiently random secret key
- **WHEN** the backend starts with `DJANGO_ENV=production` and `DJANGO_SECRET_KEY`
  is explicitly set to a value that is not a known placeholder and meets the
  minimum length
- **THEN** startup proceeds normally

#### Scenario: Password recovery does not silently no-op in production
- **WHEN** the backend runs with `DJANGO_ENV=production` and no real mail
  backend is configured
- **THEN** password-recovery is not offered as a working feature (it is
  disabled or startup fails, rather than accepting requests and silently
  discarding the resulting email)

#### Scenario: Deployment checks pass with a correctly configured production environment
- **WHEN** `python manage.py check --deploy` runs with `DJANGO_ENV=production`,
  an explicit non-placeholder `SECRET_KEY`, and a real mail backend configured
- **THEN** it reports no errors related to secret key or mail configuration
