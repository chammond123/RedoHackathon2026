/**
 * BugFixer API Gateway
 *
 * The Node.js backend is the ONLY public-facing service.
 *
 * Responsibilities:
 *  1. External Chat API   – /api/chat/*   (PUBLIC visibility only)
 *  2. Internal GUI API    – /api/*        (all visibility levels)
 *  3. WebSocket hub       – /ws/chat/:id  (public), /ws (internal)
 *  4. API-key auth        – configurable via GATEWAY_API_KEY env var
 *  5. Proxy to Python agent container (never exposed externally)
 */

import express from "express";
import { createServer } from "node:http";
import { WebSocketServer, WebSocket } from "ws";
import { v4 as uuidv4 } from "uuid";
import { EventSource } from "eventsource";

// ── Config ───────────────────────────────────────────────

const PORT = parseInt(process.env.GATEWAY_PORT || "3001", 10);
const AGENT_URL = process.env.AGENT_URL || "http://agent:8000";
const API_KEY = process.env.GATEWAY_API_KEY || ""; // empty = no auth
const INTERNAL_TOKEN = process.env.INTERNAL_TOKEN || "internal-dev"; // shared secret for internal API

// ── App ──────────────────────────────────────────────────

const app = express();
app.use(express.json());

const server = createServer(app);

// ── Helpers ──────────────────────────────────────────────

function now() {
  return new Date().toISOString();
}

async function agentFetch(path, opts = {}) {
  const url = `${AGENT_URL}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Agent ${res.status}: ${body || res.statusText}`);
  }
  return res.json();
}

// ── Auth middleware ──────────────────────────────────────

function requirePublicAuth(req, res, next) {
  if (!API_KEY) return next(); // no key configured = open
  const key =
    req.headers["x-api-key"] ||
    req.headers["authorization"]?.replace(/^Bearer\s+/i, "");
  if (key !== API_KEY) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  next();
}

function requireInternalAuth(req, res, next) {
  // Internal requests: accept INTERNAL_TOKEN or GATEWAY_API_KEY
  const key =
    req.headers["x-api-key"] ||
    req.headers["authorization"]?.replace(/^Bearer\s+/i, "");
  if (!INTERNAL_TOKEN && !API_KEY) return next();
  if (key === INTERNAL_TOKEN || key === API_KEY) return next();
  return res.status(401).json({ error: "Unauthorized" });
}

// ── Health ───────────────────────────────────────────────

app.get("/healthz", (_req, res) => res.json({ status: "ok", service: "gateway" }));

// ═══════════════════════════════════════════════════════════
//  EXTERNAL CHAT API  (PUBLIC visibility only)
// ═══════════════════════════════════════════════════════════

/**
 * POST /api/chat/start
 * Body: { bug_report, repo_path? }
 * Returns: { chat_id, status }
 */
app.post("/api/chat/start", requirePublicAuth, async (req, res) => {
  try {
    const { bug_report, repo_path = "." } = req.body;
    if (!bug_report) return res.status(400).json({ error: "bug_report is required" });

    const result = await agentFetch("/api/runs", {
      method: "POST",
      body: JSON.stringify({ bug_report, repo_path }),
    });
    res.status(201).json({ chat_id: result.id, status: result.status });
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

/**
 * POST /api/chat/:id/message
 * Body: { content }
 * Placeholder for future interactive messaging
 */
app.post("/api/chat/:id/message", requirePublicAuth, async (req, res) => {
  const { id } = req.params;
  const { content } = req.body;
  // For now, acknowledge the message (agent is not interactive yet)
  res.json({
    id: uuidv4(),
    role: "system",
    content: "Message received. The agent is currently working autonomously.",
    timestamp: now(),
  });
});

/**
 * GET /api/chat/:id/status
 * Returns PUBLIC-safe status summary
 */
app.get("/api/chat/:id/status", requirePublicAuth, async (req, res) => {
  try {
    const run = await agentFetch(`/api/runs/${req.params.id}`);
    res.json({
      chat_id: run.id,
      status: run.status,
      attempt_count: run.agent_state?.attempt_count ?? 0,
      max_attempts: run.agent_state?.max_attempts ?? 5,
      created_at: run.created_at,
    });
  } catch (err) {
    if (err.message.includes("404")) return res.status(404).json({ error: "Chat not found" });
    res.status(502).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════
//  INTERNAL GUI API  (all visibility levels)
//  Proxied straight through to the Python agent
// ═══════════════════════════════════════════════════════════

// Catch-all proxy: forward any /api/* (except /api/chat/*) to the agent
app.all("/api/{*splat}", requireInternalAuth, async (req, res) => {
  // Skip chat routes (already handled by explicit routes above)
  // req.params.splat is an array in Express 5, join with "/" to reconstruct path
  const splatPath = Array.isArray(req.params.splat)
    ? req.params.splat.join("/")
    : req.params.splat;
  const fullPath = "/api/" + splatPath;
  if (fullPath.startsWith("/api/chat")) return res.status(404).json({ error: "Not found" });

  try {
    const url = `${AGENT_URL}${fullPath}`;
    const fetchOpts = {
      method: req.method,
      headers: { "Content-Type": "application/json" },
    };
    if (req.method !== "GET" && req.method !== "HEAD") {
      fetchOpts.body = JSON.stringify(req.body);
    }

    const agentRes = await fetch(url, fetchOpts);
    const contentType = agentRes.headers.get("content-type") || "";

    // SSE passthrough
    if (contentType.includes("text/event-stream")) {
      res.setHeader("Content-Type", "text/event-stream");
      res.setHeader("Cache-Control", "no-cache");
      res.setHeader("Connection", "keep-alive");
      const reader = agentRes.body.getReader();
      const decoder = new TextDecoder();
      (async () => {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            res.write(decoder.decode(value, { stream: true }));
          }
        } catch { /* client disconnected */ }
        res.end();
      })();
      return;
    }

    // JSON / text passthrough
    const body = await agentRes.text();
    res.status(agentRes.status).setHeader("Content-Type", contentType).send(body);
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════
//  WEBSOCKET HUB
// ═══════════════════════════════════════════════════════════

const wss = new WebSocketServer({ noServer: true });

// Track connected clients
const clients = new Map(); // ws → { type: "public"|"internal", subscriptions: Set<runId> }

server.on("upgrade", (req, socket, head) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  if (url.pathname.startsWith("/ws/chat/")) {
    // Public WebSocket: /ws/chat/:run_id
    wss.handleUpgrade(req, socket, head, (ws) => {
      const runId = url.pathname.split("/ws/chat/")[1];
      clients.set(ws, { type: "public", subscriptions: new Set([runId]) });
      ws.send(JSON.stringify({ type: "connected", chat_id: runId, visibility: "PUBLIC" }));

      // Subscribe to SSE from agent for this run
      subscribeToRunEvents(runId);

      ws.on("close", () => clients.delete(ws));
    });
  } else if (url.pathname === "/ws") {
    // Internal WebSocket: /ws
    wss.handleUpgrade(req, socket, head, (ws) => {
      clients.set(ws, { type: "internal", subscriptions: new Set(["*"]) });
      ws.send(JSON.stringify({ type: "connected", visibility: "INTERNAL" }));

      ws.on("message", (data) => {
        try {
          const msg = JSON.parse(data);
          // Allow internal clients to subscribe/unsubscribe from specific runs
          if (msg.type === "subscribe" && msg.run_id) {
            clients.get(ws)?.subscriptions.add(msg.run_id);
            subscribeToRunEvents(msg.run_id);
          }
        } catch { /* ignore */ }
      });

      ws.on("close", () => clients.delete(ws));
    });
  } else {
    socket.destroy();
  }
});

// ── SSE → WebSocket bridge ──────────────────────────────

const activeSSE = new Set(); // run IDs we're already subscribed to

function subscribeToRunEvents(runId) {
  if (activeSSE.has(runId)) return;
  activeSSE.add(runId);

  const es = new EventSource(`${AGENT_URL}/api/runs/${runId}/events`);

  es.onmessage = (evt) => {
    try {
      const event = JSON.parse(evt.data);
      broadcastEvent(event);
    } catch { /* ignore */ }
  };

  es.onerror = () => {
    es.close();
    activeSSE.delete(runId);
  };
}

function broadcastEvent(event) {
  const runId = event.request_id;
  const visibility = event.visibility || "INTERNAL";

  for (const [ws, client] of clients.entries()) {
    if (ws.readyState !== WebSocket.OPEN) continue;

    // Check subscription
    const subscribed =
      client.subscriptions.has("*") || client.subscriptions.has(runId);
    if (!subscribed) continue;

    // Visibility filtering
    if (client.type === "public" && visibility !== "PUBLIC") continue;

    // For public clients, strip internal fields
    const payload = client.type === "public" ? sanitizeForPublic(event) : event;
    ws.send(JSON.stringify(payload));
  }
}

function sanitizeForPublic(event) {
  // Remove internal-only fields
  const { state, entry, error, pr_title, pr_summary, patch, ...safe } = event;
  // Add a user-friendly message if available
  if (event.message) safe.message = event.message;
  return safe;
}

// ── Start ───────────────────────────────────────────────

server.listen(PORT, () => {
  console.log(`🚀 Gateway listening on :${PORT}`);
  console.log(`   Agent upstream: ${AGENT_URL}`);
  console.log(`   Auth: ${API_KEY ? "API key required" : "open (no key)"}`);
});
