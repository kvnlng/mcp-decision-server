# Listing a deployment in an MCP registry

An MCP registry is a catalogue clients and people search to find MCP servers. Each deployment of the decision server,
with its own scenario or environment, address and key, is a server of its own, so list the deployment, not the
framework.

**Most decision servers belong in a private registry.** A deployment on a private network, as most will be, is listed
in a registry your organisation runs, so nothing about it leaves the network. It is the same software and API as the
public registry, and the same steps, with `--registry <its address>` when you log in. The public registry is for a
deployment anyone may reach, such as a demonstration; for it, this page gives the steps that differ and the registry's
[quickstart](https://modelcontextprotocol.io/registry/quickstart) the rest.

## The entry

A deployment is a **remote** server: an address clients reach over Streamable HTTP. Its entry, `server.json`, lists
that address under `remotes` and no `packages`: a client does not install a deployment, so the quickstart's package
steps and ownership markers do not apply. A registry checks that you control the entry's name, not its address.

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
| `--name` | `namespace/name`, such as `io.github.you/offsite`. The namespace must match how you log in |
| `--url` | HTTPS, a host name and a path ending in `/mcp`. An internal name (`decisions.corp.internal`) is fine, as is a path before `/mcp` (`https://gateway.corp/tools/decisions/mcp`, behind a gateway). `localhost` and `127.0.0.1` are refused by the registry, and every other bare IP address by `decision-registry`, since an entry names a host other computers can find. A user, password, query or fragment is refused too: an entry is published as written and never fully removed, and the key belongs in the header. One address belongs to one entry: a registry refuses an address another name already lists |
| `--version` | Such as `1.0.0` or `1.0.0-1`: a version, never a range |
| `--auth key` (default) | Says a client must send a secret `Authorization` header (`Bearer <the server's key>`); the key itself is never in the entry |
| `--auth oauth` | Names no header; the client learns which issuer to ask from the server's protected resource metadata ([serving.md](serving.md#with-tokens-from-your-identity-provider-oauth)) |
| `--title` | A display name, 1 to 100 characters; left out unless given |
| `--description` | At most 100 characters, the registry's limit; defaults to an environment's name, and a CLM scenario has none, so give one |
| `--repository` | A GitHub or GitLab project's home page, all the registry takes; leave it out for any other forge |
| `--out` | Where to write the entry; `server.json` by default |

## Publishing it

`mcp-publisher` comes from the registry's releases: `brew install mcp-publisher`, or the binaries on
[GitHub](https://github.com/modelcontextprotocol/registry/releases), checked against the release's checksums file.
With the entry written:

```bash
mcp-publisher login <method> --registry <the registry's address>   # leave out --registry for the public one
mcp-publisher validate server.json
mcp-publisher publish server.json
curl "<the registry's address>/v0.1/servers?search=io.github.you/offsite"
```

`validate` reports every problem at once without publishing; the search answers with the entry, its address and the
header it needs.

**Updating.** A published version, and everything in it, cannot be changed, and the same version cannot be published
twice: a new address, description or authentication means a new `--version`. Entries are never fully removed:
`mcp-publisher status --status deprecated --message "Use 0.2.0" io.github.you/offsite 0.1.0` keeps a version listed with
a warning, and `--status deleted` hides it until `--status active`.

**When publishing fails:** `You do not have permission to publish this server` means the name's namespace does not
match how you logged in; `cannot publish duplicate version`, that the version is published already; `remote URL ... is
already used by server ...`, that another entry lists the address. The quickstart lists the others.

## A private registry

Who may publish to a private registry depends on how it is run: with GitHub login, any GitHub user who can reach it,
under their own `io.github.<user>/` name, not only an organisation's members; with your own identity provider (OIDC),
whoever holds the claims a token must carry; with DNS or HTTP proof, whoever holds a domain's key. Clients inside the
network search it as they would the public one.

### A private registry on this computer

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

## The public registry

`registry.modelcontextprotocol.io` lists only what anyone can reach, so give `--url` a public address. It is in
preview, and its data may be reset. How you log in decides the names you may publish:

- **`io.github.<you>/...`:** `mcp-publisher login github`, then enter the code it prints.
- **`io.github.<an organisation>/...`:** `login github` cannot grant these yet; use a token with `read:org`, or GitHub
  Actions with `login github-oidc`.
- **Your own domain, such as `com.example/...`:** `login dns` or `login http`, with a key whose public half is in your
  domain's DNS or at its `/.well-known/mcp-registry-auth`. Keep the key out of git: whoever holds it can publish under
  the domain.

The quickstart covers the rest: installing `mcp-publisher` on each platform, the proofs and tokens step by step
([authentication](https://modelcontextprotocol.io/registry/authentication)), publishing from GitHub Actions
([GitHub Actions](https://modelcontextprotocol.io/registry/github-actions)) and what each error means.
