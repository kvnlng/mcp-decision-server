# Listing a deployment in an MCP registry

An MCP registry is a catalogue clients and people search to find MCP servers. Each deployment of the decision server,
with its own scenario or environment, address and key, is a server of its own, so list the deployment, not the
framework. The steps follow the registry's [quickstart](https://modelcontextprotocol.io/registry/quickstart) for a
remote server: install the publisher, write `server.json`, log in, publish, and check that it is listed.

## What you publish

A deployment is a **remote** server: an address clients reach over Streamable HTTP. The entry lists that address under
`remotes` and no `packages`, so the quickstart's npm steps, and the ownership markers that npm, PyPI, NuGet, Cargo,
Docker and MCPB packages need, do not apply: a client does not install a deployment. The registry holds only the entry;
it checks that you control the name, not the address.

## 1. Install the publisher

`mcp-publisher` comes from the registry's releases. On macOS or Linux:

```bash
brew install mcp-publisher
# or
curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" | tar xz mcp-publisher && sudo mv mcp-publisher /usr/local/bin/
mcp-publisher --help
```

On Windows, download `mcp-publisher_windows_amd64.tar.gz` (or `_arm64`) from [the
releases](https://github.com/modelcontextprotocol/registry/releases) and put `mcp-publisher.exe` on your `PATH`. In
automation, pin a release (`releases/download/v1.8.6/...`) rather than `latest`, and check it against the release's
checksums file.

## 2. Write server.json

`decision-registry` writes the entry; it takes the place of the quickstart's `mcp-publisher init`, which guesses a
package entry from a `package.json`:

```bash
uv run decision-registry my_environment/environment.toml --name io.github.you/offsite \
    --url https://decisions.example.org/mcp --version 0.1.0 [--auth key|oauth] [--title "Offsite planner"] \
    [--description "..."] [--repository https://github.com/you/repo] [--out server.json]
```

| Field | Takes |
|---|---|
| File | The scenario or `environment.toml` served; it is read and checked even with `--description`, so a mistyped path is refused |
| `--name` | `namespace/name`, such as `io.github.you/offsite`. The namespace must match how you log in (step 3) |
| `--url` | HTTPS, a host name and a path ending in `/mcp`. An internal name (`decisions.corp.internal`) is fine, as is a path before `/mcp` (`https://gateway.corp/tools/decisions/mcp`, behind a gateway). `localhost` and `127.0.0.1` are refused by the registry, and every other bare IP address by `decision-registry`, since an entry names a host other computers can find. A user, password, query or fragment is refused too: an entry is published as written and never fully removed, and the key belongs in the header. One address belongs to one entry: the registry refuses an address another name already lists |
| `--version` | Such as `1.0.0` or `1.0.0-1`: a version, never a range |
| `--auth key` (default) | Says a client must send a secret `Authorization` header; the key itself is never in the entry |
| `--auth oauth` | Names no header; the client learns which issuer to ask from the server's protected resource metadata ([serving.md](serving.md#with-tokens-from-your-identity-provider-oauth)) |
| `--title` | A display name, 1 to 100 characters; left out unless given |
| `--description` | At most 100 characters, the registry's limit; defaults to an environment's name, and a CLM scenario has none, so give one |
| `--repository` | A GitHub or GitLab project's home page, all the registry takes; leave it out for any other forge |
| `--out` | Where to write the entry; `server.json` by default |

For a server started with a key, the entry is:

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "io.github.you/offsite",
  "title": "Offsite planner",
  "description": "Where a team should hold its offsite",
  "version": "0.1.0",
  "repository": {"url": "https://github.com/you/repo", "source": "github"},
  "remotes": [
    {
      "type": "streamable-http",
      "url": "https://decisions.example.org/mcp",
      "headers": [{"name": "Authorization", "description": "Bearer <the server's key>",
                   "isRequired": true, "isSecret": true}]
    }
  ]
}
```

## 3. Log in

How you log in decides which names you may publish:

| Name | Log in with |
|---|---|
| `io.github.<your user>/...` | `mcp-publisher login github`: open the address it prints and enter its code |
| `io.github.<an organisation>/...` | `mcp-publisher login github --token <token>`, a token with `read:org` (fine-grained: organisation Members, read-only), as an owner of the organisation; or GitHub Actions (below). `login github` alone cannot grant organisation names yet |
| `com.example/...` or `com.example.team/...`, for your domain `example.com` | A DNS or HTTP proof (below) |

**DNS proof.** Make a key, publish its public half as a TXT record on the domain itself (not a subdomain such as
`_mcp-auth`), then log in with the private half. On macOS this needs OpenSSL 3 (`brew install openssl@3`, called by its
full path):

```bash
MY_DOMAIN="example.com"
openssl genpkey -algorithm Ed25519 -out key.pem
PUBLIC_KEY="$(openssl pkey -in key.pem -pubout -outform DER | tail -c 32 | base64)"
echo "${MY_DOMAIN}. IN TXT \"v=MCPv1; k=ed25519; p=${PUBLIC_KEY}\""      # add this record, then:
PRIVATE_KEY="$(openssl pkey -in key.pem -noout -text | grep -A3 "priv:" | tail -n +2 | tr -d ' :\n')"
mcp-publisher login dns --domain "${MY_DOMAIN}" --private-key "${PRIVATE_KEY}"
```

**HTTP proof.** The same key, served instead as plain text at `https://example.com/.well-known/mcp-registry-auth`,
answering with 200 and no redirect:

```bash
echo "v=MCPv1; k=ed25519; p=${PUBLIC_KEY}" > mcp-registry-auth          # serve this file, then:
mcp-publisher login http --domain "${MY_DOMAIN}" --private-key "${PRIVATE_KEY}"
```

Keep `key.pem` out of git, as every key: whoever holds it can publish under the domain. The registry also takes ECDSA
P-384 keys and keys held in Google Cloud KMS or Azure Key Vault
([authentication](https://modelcontextprotocol.io/registry/authentication)).

**GitHub Actions.** A workflow with `permissions: id-token: write` can log in as its repository's owner, organisation
names included, with `mcp-publisher login github-oidc`. Run `decision-registry`, then `mcp-publisher login github-oidc`
and `mcp-publisher publish`, on a tag such as `v0.1.0`, passing the tag as `--version`
([GitHub Actions](https://modelcontextprotocol.io/registry/github-actions)).

To use a registry other than the public one, add `--registry <its address>` to `login`; later commands go to the
registry you logged in to.

## 4. Publish

```bash
mcp-publisher validate server.json
mcp-publisher publish server.json
```

`validate` reports every problem at once without publishing. `publish` prints `✓ Successfully published`.

## 5. Check that it is listed

```bash
curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.you/offsite"
```

The answer holds the entry under `servers`, with its address and the header it needs.

## Updating an entry

- **A new version for every change.** A published version, and everything in it, cannot be changed, and the same
  version cannot be published twice. Changing the address, the description or the authentication means a new
  `--version`; the registry marks the highest version as the latest.
- **Retiring a version.** Entries are never fully removed. `mcp-publisher status --status deprecated --message "Use
  0.2.0" io.github.you/offsite 0.1.0` keeps it listed with a warning; `--status deleted` hides it from listings and can
  be undone with `--status active`. `--all-versions` in place of the version changes every one.

## When publishing fails

| Message | Meaning |
|---|---|
| `You do not have permission to publish this server` | The name's namespace does not match how you logged in (step 3) |
| `Invalid or expired Registry JWT token` | Log in again |
| `cannot publish duplicate version` | That version is published already; give a new `--version` |
| `remote URL ... is already used by server ...` | Another entry lists the address; reuse that entry's name or give this deployment its own address |
| `token exchange failed with status 401`, with an HTTP proof | Often a firewall or CDN refusing the registry's request for `/.well-known/mcp-registry-auth` |

## Public or private

**The public registry** (`registry.modelcontextprotocol.io`) is for a deployment meant for the public, such as a
demonstration, and lists only what anyone can reach: a public remote address, or a package on a public index. It is in
preview, so its data may be reset.

**A private registry** suits a deployment on a private network, as most decision servers will be. It is the same
software and API, run by your organisation; clients inside the network search it, and nothing about the deployment
leaves the network. Who may publish depends on how it is run: with GitHub login, any GitHub user who can reach it, under
their own `io.github.<user>/` name, not only an organisation's members; with your own identity provider (OIDC), whoever
holds the claims a token must carry; with DNS or HTTP proof, whoever holds a domain's key.

## A private registry on this computer

This was checked on a Mac with the registry's release 1.8.6 and PostgreSQL 18 from Homebrew, both run natively.

1. Download `registry_darwin_arm64.tar.gz` and `mcp-publisher_darwin_arm64.tar.gz` from
   [the registry's releases](https://github.com/modelcontextprotocol/registry/releases), and check them against the
   release's checksums file.
2. Start PostgreSQL with its own data folder (`initdb`, then `postgres -D <folder> -p 5433`, with `LC_ALL` set to a
   locale such as `en_US.UTF-8`), and create a database `mcp-registry`.
3. Start the registry:

   ```bash
   MCP_REGISTRY_SERVER_ADDRESS=127.0.0.1:8090 \
   MCP_REGISTRY_DATABASE_URL="postgres://mcpregistry@localhost:5433/mcp-registry?sslmode=disable" \
   MCP_REGISTRY_JWT_PRIVATE_KEY=$(openssl rand -hex 32) \
   MCP_REGISTRY_SEED_FROM= MCP_REGISTRY_ENABLE_ANONYMOUS_AUTH=true MCP_REGISTRY_OIDC_ENABLED=false \
   ./registry
   ```

   Anonymous publishing is for trying it out only: anyone who can reach the registry can publish, change or deprecate
   names under `io.modelcontextprotocol.anonymous/`, including an entry that sends clients, and their key, to another
   host. Listen on `127.0.0.1` only, as above, and never turn it on for a registry others use.
4. Write and publish the entry:

   ```bash
   uv run decision-registry my_environment/environment.toml \
       --name io.modelcontextprotocol.anonymous/decision-offsite --title "Offsite planner" \
       --url https://decisions.corp.internal/mcp --version 0.1.0 \
       --description "Where a team should hold its offsite"
   mcp-publisher login none --registry http://localhost:8090
   mcp-publisher validate server.json
   mcp-publisher publish server.json
   ```

5. Find it: `curl "http://localhost:8090/v0.1/servers?search=decision-offsite"` gives the entry, with its address and
   the header it needs. The MCP Inspector lists the server's tools with that header
   (`--cli <address> --transport http --header "Authorization: Bearer <the key>" --method tools/list`;
   [serving](serving.md#inspecting-a-server)); with the key in `DECISION_SERVER_KEY`,
   `decision-agent <address> "QUESTION"` asks a model to use them. The internal host name does not resolve on a laptop,
   so in the check the client was pointed at the local server for that name.
