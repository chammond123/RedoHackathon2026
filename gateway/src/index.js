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
import cors from "cors";
import { createServer } from "node:http";
import { WebSocketServer, WebSocket } from "ws";
import { v4 as uuidv4 } from "uuid";
import { EventSource } from "eventsource";
import nodemailer from "nodemailer";

// ── Config ───────────────────────────────────────────────

const PORT = parseInt(process.env.GATEWAY_PORT || "3001", 10);
const AGENT_URL = process.env.AGENT_URL || "http://agent:8000";
const API_KEY = process.env.GATEWAY_API_KEY || ""; // empty = no auth
const INTERNAL_TOKEN = process.env.INTERNAL_TOKEN || "internal-dev"; // shared secret for internal API

// Default repo path for the agent (path inside Docker container)
const DEFAULT_REPO_PATH = process.env.DEFAULT_REPO_PATH || "/app/BuggyDemo";

// ── Email Config ─────────────────────────────────────────
// Configure via environment variables:
//   SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM
// Set SMTP_HOST=ethereal for auto-generated test account
const SMTP_HOST = process.env.SMTP_HOST || "";
const SMTP_PORT = parseInt(process.env.SMTP_PORT || "587", 10);
const SMTP_USER = process.env.SMTP_USER || "";
const SMTP_PASS = process.env.SMTP_PASS || "";
const SMTP_FROM = process.env.SMTP_FROM || "bugfixer@example.com";

// Email transporter (initialized async if using ethereal)
let emailTransporter = null;
let etherealAccount = null;

async function initEmailTransporter() {
  if (SMTP_HOST === "ethereal") {
    // Create a test account on Ethereal
    etherealAccount = await nodemailer.createTestAccount();
    emailTransporter = nodemailer.createTransport({
      host: "smtp.ethereal.email",
      port: 587,
      secure: false,
      auth: {
        user: etherealAccount.user,
        pass: etherealAccount.pass,
      },
    });
    console.log(`[Email] Ethereal test account created:`);
    console.log(`        User: ${etherealAccount.user}`);
    console.log(`        Pass: ${etherealAccount.pass}`);
    console.log(`        Preview URL: https://ethereal.email/login`);
  } else if (SMTP_HOST) {
    emailTransporter = nodemailer.createTransport({
      host: SMTP_HOST,
      port: SMTP_PORT,
      secure: SMTP_PORT === 465,
      auth: SMTP_USER ? { user: SMTP_USER, pass: SMTP_PASS } : undefined,
    });
    console.log(`[Email] Configured with SMTP host: ${SMTP_HOST}`);
  } else {
    console.log(`[Email] Not configured (set SMTP_HOST=ethereal for testing)`);
  }
}

// Initialize email on startup
initEmailTransporter();

// ── In-memory bug ticket store (synced to frontend) ──────
const bugTickets = new Map(); // ticket_id → ticket data

// ── Email history store (per request) ──────────────────────
const emailHistory = new Map(); // request_id → [{ id, direction, to, from, subject, body, timestamp, messageId, previewUrl }]

// ── App ──────────────────────────────────────────────────

const app = express();

// Enable CORS for all origins (allows BuggyDemo on localhost:5000 to call gateway on localhost:3001)
app.use(cors());

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
 * Body: { bug_report, repo_path?, ticket? }
 * Returns: { chat_id, status, ticket_id? }
 * 
 * If `ticket` object is provided, it will be stored and synced to the frontend.
 * Note: repo_path from client is ignored; we use the server-configured DEFAULT_REPO_PATH
 */
app.post("/api/chat/start", requirePublicAuth, async (req, res) => {
  try {
    const { bug_report, ticket, email } = req.body;
    if (!bug_report) return res.status(400).json({ error: "bug_report is required" });

    // Always use the server-configured repo path, not the client-provided one
    const repo_path = DEFAULT_REPO_PATH;

    // Get email from request body or from ticket
    const reporterEmail = email || (ticket && ticket.email) || "";

    // Store the bug ticket if provided (for frontend dashboard sync)
    let ticketId = null;
    if (ticket) {
      ticketId = uuidv4();
      const storedTicket = {
        id: ticketId,
        ...ticket,
        email: reporterEmail,
        submitted_at: ticket.submitted_at || now(),
        status: "processing",
        run_id: null, // will be updated after agent starts
      };
      bugTickets.set(ticketId, storedTicket);

      // Broadcast new ticket to internal (frontend) clients
      broadcastEvent({
        type: "ticket_created",
        visibility: "INTERNAL",
        ticket: storedTicket,
        timestamp: now(),
      });
    }

    const result = await agentFetch("/api/runs", {
      method: "POST",
      body: JSON.stringify({ bug_report, repo_path, email: reporterEmail }),
    });

    // Link ticket to the run
    if (ticketId && bugTickets.has(ticketId)) {
      const t = bugTickets.get(ticketId);
      t.run_id = result.id;
      t.status = "running";
      bugTickets.set(ticketId, t);

      // Notify frontend of the link
      broadcastEvent({
        type: "ticket_updated",
        visibility: "INTERNAL",
        ticket: t,
        timestamp: now(),
      });
    }

    res.status(201).json({
      chat_id: result.id,
      status: result.status,
      ticket_id: ticketId,
    });
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
//  BUG TICKETS API (syncs BuggyDemo reports to frontend)
// ═══════════════════════════════════════════════════════════

/**
 * GET /api/tickets
 * Returns all bug tickets (for frontend dashboard)
 */
app.get("/api/tickets", requireInternalAuth, (_req, res) => {
  const tickets = Array.from(bugTickets.values())
    .sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));
  res.json(tickets);
});

/**
 * GET /api/tickets/:id
 * Returns a specific bug ticket
 */
app.get("/api/tickets/:id", requireInternalAuth, (req, res) => {
  const ticket = bugTickets.get(req.params.id);
  if (!ticket) return res.status(404).json({ error: "Ticket not found" });
  res.json(ticket);
});

/**
 * POST /api/tickets
 * Create a bug ticket WITHOUT starting an agent run
 * Body: { title, description, module, severity, reporter, steps }
 */
app.post("/api/tickets", requireInternalAuth, (req, res) => {
  const ticketId = uuidv4();
  const ticket = {
    id: ticketId,
    title: req.body.title || "Untitled",
    description: req.body.description || "",
    module: req.body.module || "",
    severity: req.body.severity || "medium",
    reporter: req.body.reporter || "Unknown",
    email: req.body.email || "",
    steps: req.body.steps || "",
    submitted_at: now(),
    status: "pending",
    run_id: null,
  };
  bugTickets.set(ticketId, ticket);

  broadcastEvent({
    type: "ticket_created",
    visibility: "INTERNAL",
    ticket,
    timestamp: now(),
  });

  res.status(201).json(ticket);
});

/**
 * POST /api/tickets/:id/start
 * Start an agent run for an existing ticket
 */
app.post("/api/tickets/:id/start", requireInternalAuth, async (req, res) => {
  const ticket = bugTickets.get(req.params.id);
  if (!ticket) return res.status(404).json({ error: "Ticket not found" });
  if (ticket.run_id) return res.status(400).json({ error: "Ticket already has a run" });

  try {
    const bug_report = `${ticket.title}\n\n${ticket.description}\n\nSteps: ${ticket.steps}\nModule: ${ticket.module}\nSeverity: ${ticket.severity}`;
    const result = await agentFetch("/api/runs", {
      method: "POST",
      body: JSON.stringify({
        bug_report,
        repo_path: req.body.repo_path || "/app/BuggyDemo"
      }),
    });

    ticket.run_id = result.id;
    ticket.status = "running";
    bugTickets.set(req.params.id, ticket);

    broadcastEvent({
      type: "ticket_updated",
      visibility: "INTERNAL",
      ticket,
      timestamp: now(),
    });

    res.json({ ticket, run: result });
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════
//  EMAIL API
// ═══════════════════════════════════════════════════════════

/**
 * GET /api/email/status
 * Check if email is configured
 */
app.get("/api/email/status", requireInternalAuth, (_req, res) => {
  res.json({
    configured: !!emailTransporter,
    from: etherealAccount ? etherealAccount.user : SMTP_FROM,
    ethereal: etherealAccount ? {
      user: etherealAccount.user,
      pass: etherealAccount.pass,
      webUrl: "https://ethereal.email/login",
    } : null,
  });
});

/**
 * POST /api/email/send
 * Send an email to a bug reporter
 * Body: { to, subject, body, request_id? }
 */
app.post("/api/email/send", requireInternalAuth, async (req, res) => {
  if (!emailTransporter) {
    return res.status(503).json({
      error: "Email not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS environment variables.",
    });
  }

  const { to, subject, body, request_id } = req.body;

  if (!to || !subject || !body) {
    return res.status(400).json({ error: "Missing required fields: to, subject, body" });
  }

  try {
    const info = await emailTransporter.sendMail({
      from: etherealAccount ? etherealAccount.user : SMTP_FROM,
      to,
      subject,
      text: body,
      html: body.replace(/\n/g, "<br>"),
    });

    console.log(`[Email] Sent to ${to}: ${info.messageId}`);

    // Get preview URL for Ethereal
    const previewUrl = etherealAccount ? nodemailer.getTestMessageUrl(info) : null;
    if (previewUrl) {
      console.log(`[Email] Preview URL: ${previewUrl}`);
    }

    // Store in history if request_id provided
    const emailRecord = {
      id: uuidv4(),
      direction: "outbound",
      from: etherealAccount ? etherealAccount.user : SMTP_FROM,
      to,
      subject,
      body,
      timestamp: now(),
      messageId: info.messageId,
      previewUrl,
    };

    if (request_id) {
      if (!emailHistory.has(request_id)) {
        emailHistory.set(request_id, []);
      }
      emailHistory.get(request_id).push(emailRecord);

      // Broadcast to connected clients
      broadcastEvent({
        type: "email_sent",
        visibility: "INTERNAL",
        request_id,
        email: emailRecord,
        timestamp: now(),
      });
    }

    res.json({
      success: true,
      messageId: info.messageId,
      to,
      subject,
      previewUrl,
      email: emailRecord,
    });
  } catch (err) {
    console.error(`[Email] Failed to send to ${to}:`, err.message);
    res.status(500).json({ error: `Failed to send email: ${err.message}` });
  }
});

/**
 * GET /api/requests/:request_id/emails
 * Get email history for a request
 */
app.get("/api/requests/:request_id/emails", requireInternalAuth, (req, res) => {
  const { request_id } = req.params;
  const history = emailHistory.get(request_id) || [];
  res.json(history);
});

/**
 * POST /api/requests/:request_id/email
 * Send an email to the reporter and store in history
 * Body: { subject, body }
 */
app.post("/api/requests/:request_id/email", requireInternalAuth, async (req, res) => {
  if (!emailTransporter) {
    return res.status(503).json({
      error: "Email not configured. Set SMTP_HOST environment variable.",
    });
  }

  const { request_id } = req.params;
  const { subject, body } = req.body;

  if (!subject || !body) {
    return res.status(400).json({ error: "Missing required fields: subject, body" });
  }

  // Get the request to find the email
  try {
    const request = await agentFetch(`/api/runs/${request_id}`);

    if (!request.email) {
      return res.status(400).json({ error: "No email address associated with this request" });
    }

    const info = await emailTransporter.sendMail({
      from: etherealAccount ? etherealAccount.user : SMTP_FROM,
      to: request.email,
      subject,
      text: body,
      html: body.replace(/\n/g, "<br>"),
    });

    console.log(`[Email] Sent to ${request.email}: ${info.messageId}`);

    const previewUrl = etherealAccount ? nodemailer.getTestMessageUrl(info) : null;
    if (previewUrl) {
      console.log(`[Email] Preview URL: ${previewUrl}`);
    }

    // Store in history
    const emailRecord = {
      id: uuidv4(),
      direction: "outbound",
      from: etherealAccount ? etherealAccount.user : SMTP_FROM,
      to: request.email,
      subject,
      body,
      timestamp: now(),
      messageId: info.messageId,
      previewUrl,
    };

    if (!emailHistory.has(request_id)) {
      emailHistory.set(request_id, []);
    }
    emailHistory.get(request_id).push(emailRecord);

    // Broadcast to connected clients
    broadcastEvent({
      type: "email_sent",
      visibility: "INTERNAL",
      request_id,
      email: emailRecord,
      timestamp: now(),
    });

    res.json({
      success: true,
      email: emailRecord,
    });
  } catch (err) {
    console.error(`[Email] Failed to send:`, err.message);
    res.status(500).json({ error: err.message });
  }
});

/**
 * POST /api/email/notify-reporter/:request_id
 * Send a notification to the bug reporter for a specific request
 * Body: { subject?, message }
 */
app.post("/api/email/notify-reporter/:request_id", requireInternalAuth, async (req, res) => {
  if (!emailTransporter) {
    return res.status(503).json({
      error: "Email not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS environment variables.",
    });
  }

  const { request_id } = req.params;
  const { subject, message } = req.body;

  if (!message) {
    return res.status(400).json({ error: "Missing required field: message" });
  }

  // Get the request from the agent to find the email
  try {
    const request = await agentFetch(`/api/runs/${request_id}`);

    if (!request.email) {
      return res.status(400).json({ error: "No email address associated with this request" });
    }

    const emailSubject = subject || `Update on your bug report: ${request.bug_report.substring(0, 50)}...`;
    const emailBody = `Hi,

${message}

---
Bug Report: ${request.bug_report}
Status: ${request.status}
Request ID: ${request_id}

- BugFixer Team`;

    const info = await emailTransporter.sendMail({
      from: etherealAccount ? etherealAccount.user : SMTP_FROM,
      to: request.email,
      subject: emailSubject,
      text: emailBody,
      html: emailBody.replace(/\n/g, "<br>"),
    });

    console.log(`[Email] Notified reporter ${request.email}: ${info.messageId}`);

    // Get preview URL for Ethereal
    const previewUrl = etherealAccount ? nodemailer.getTestMessageUrl(info) : null;
    if (previewUrl) {
      console.log(`[Email] Preview URL: ${previewUrl}`);
    }

    res.json({
      success: true,
      messageId: info.messageId,
      to: request.email,
      subject: emailSubject,
      previewUrl,
    });
  } catch (err) {
    console.error(`[Email] Failed to notify reporter:`, err.message);
    res.status(500).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════
//  DYNAMIC CHAT FEATURES
// ═══════════════════════════════════════════════════════════

/**
 * POST /api/chat/:id/typing
 * Emit a "typing" indicator to connected clients (makes chat feel more alive)
 */
app.post("/api/chat/:id/typing", requirePublicAuth, (req, res) => {
  const { id } = req.params;
  const { is_typing = true, message } = req.body;

  broadcastEvent({
    type: "typing",
    visibility: "PUBLIC",
    request_id: id,
    is_typing,
    message: message || (is_typing ? "Agent is thinking..." : null),
    timestamp: now(),
  });

  res.json({ ok: true });
});

/**
 * POST /api/chat/:id/feedback
 * Send intermediate feedback/hints to the user during processing
 */
app.post("/api/chat/:id/feedback", requirePublicAuth, (req, res) => {
  const { id } = req.params;
  const { message, type = "info" } = req.body;

  broadcastEvent({
    type: "chat_feedback",
    visibility: "PUBLIC",
    request_id: id,
    feedback_type: type, // "info", "warning", "success", "question"
    message,
    timestamp: now(),
  });

  res.json({ ok: true });
});

// ═══════════════════════════════════════════════════════════
//  INTERNAL GUI API  (all visibility levels)
//  Proxied straight through to the Python agent
// ═══════════════════════════════════════════════════════════

// Handle POST /api/requests specially to auto-subscribe to new runs
app.post("/api/requests", requireInternalAuth, async (req, res) => {
  try {
    const result = await agentFetch("/api/requests", {
      method: "POST",
      body: JSON.stringify(req.body),
    });
    // Auto-subscribe to events for the new run
    if (result.id) {
      console.log(`[Gateway] New run created: ${result.id}, subscribing to events...`);
      subscribeToRunEvents(result.id);
    }
    res.status(201).json(result);
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

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

      // Subscribe to all active runs when internal client connects
      subscribeToActiveRuns();

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

async function subscribeToActiveRuns() {
  // Fetch all runs and subscribe to active ones
  try {
    const runs = await agentFetch("/api/runs");
    for (const run of runs) {
      if (!["complete", "failed"].includes(run.status)) {
        subscribeToRunEvents(run.id);
      }
    }
  } catch (err) {
    console.error("Failed to subscribe to active runs:", err.message);
  }
}

function subscribeToRunEvents(runId) {
  if (activeSSE.has(runId)) return;
  activeSSE.add(runId);
  console.log(`[SSE] Subscribing to run ${runId}`);

  const es = new EventSource(`${AGENT_URL}/api/runs/${runId}/events`);

  es.onmessage = (evt) => {
    try {
      const event = JSON.parse(evt.data);
      console.log(`[SSE] Event from ${runId}: ${event.type}`);
      broadcastEvent(event);
    } catch { /* ignore */ }
  };

  es.onerror = () => {
    console.log(`[SSE] Connection closed for ${runId}`);
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
