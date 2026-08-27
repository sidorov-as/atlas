# Atlas authentication examples

These examples are disposable development topologies for learning and
verification. They are not production deployment templates. Each example is
an isolated Compose project with its own database volume, configuration, and
cleanup instructions.

## Choose a topology

| Example                                   | Browser flow                                | Services                          | Principal / Actor provisioning                            | Group behavior                                                                      | Typical host resources                                | Status    |
|-------------------------------------------|---------------------------------------------|-----------------------------------|-----------------------------------------------------------|-------------------------------------------------------------------------------------|-------------------------------------------------------|-----------|
| [Local credentials](local/)               | Username and password                       | Atlas, PostgreSQL                 | Controlled bootstrap creates a Principal and linked Actor | Bootstrap Actor joins one operator-selected owner Group; later membership is manual | About 2 GB RAM and 2 CPU cores while building/running | Available |
| [Keycloak OIDC](oidc-keycloak/)           | OIDC Authorization Code + PKCE              | Atlas, PostgreSQL, Keycloak       | Automatic Principal and Actor provisioning                | Exact mapped-group reconciliation                                                   | About 4 GB RAM and 2–4 CPU cores                      | Available |
| [Gitea OAuth2](oauth2-gitea/)             | Provider-specific Authorization Code + PKCE | Atlas, PostgreSQL, Gitea          | Automatic Principal and Actor provisioning                | Manual; OAuth scopes do not grant Atlas permissions                                 | About 3 GB RAM and 2–4 CPU cores                      | Available |
| [Custom credentials](custom-credentials/) | Public credential-provider SDK              | Atlas, PostgreSQL, fixture plugin | Automatic Principal and Actor provisioning                | Exact complete, empty, and unavailable fixture snapshots                            | About 2 GB RAM and 2 CPU cores                        | Available |

All browser providers establish the same Atlas Django session. They do not
turn an upstream OAuth or OIDC token into an Atlas API bearer token. SAML,
machine-to-machine tokens, and a production LDAP provider are outside these
examples.

## Security boundary

- Every password, client secret, user, realm, and database in this tree is
  disposable development data. Never reuse an example value in another
  environment.
- Examples deliberately favor inspectability over production hardening. Use
  HTTPS, an external secret manager, protected backups, restricted networks,
  reviewed images, and production process supervision in a real deployment.
- Authentication proves a Principal's identity. Atlas permissions still come
  from Actor links, owner-Group membership, ordinary policy evaluation, and
  independent account restrictions such as read-only access.
- Provider claims, groups, roles, and OAuth scopes never directly grant staff,
  superuser, Purge Grant, or catalog permissions.
- Atlas logout always ends the local Atlas session. Whether an upstream IdP
  session also ends is provider-specific and is stated in each guide.

Start with the [local credentials example](local/) for the smallest topology,
the [Keycloak OIDC example](oidc-keycloak/) for standards-based federation,
the [Gitea OAuth2 example](oauth2-gitea/) for a provider-specific OAuth flow,
or the [custom credential example](custom-credentials/) to implement and test
the public provider SDK without an external directory dependency.
