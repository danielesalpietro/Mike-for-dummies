import { Router } from "express";
import { createServerSupabase } from "../lib/supabase";
import Anthropic from "@anthropic-ai/sdk";

export const statusRouter = Router();

type ServiceStatus = "ok" | "starting" | "error";

interface ServiceResult {
    name: string;
    status: ServiceStatus;
    latencyMs?: number;
    message?: string;
}

async function checkDatabase(): Promise<ServiceResult> {
    const t0 = Date.now();
    try {
        const db = createServerSupabase();
        const { error } = await db.from("user_profiles").select("id").limit(1);
        if (error) throw error;
        return { name: "Database", status: "ok", latencyMs: Date.now() - t0 };
    } catch {
        return { name: "Database", status: "error" };
    }
}

async function checkMinio(): Promise<ServiceResult> {
    const t0 = Date.now();
    const endpoint = process.env.R2_ENDPOINT_URL;
    const bucket = process.env.R2_BUCKET_NAME ?? "mike";
    if (!endpoint) return { name: "Storage", status: "error" };
    try {
        const res = await fetch(`${endpoint}/${bucket}`, {
            method: "HEAD",
            signal: AbortSignal.timeout(4000),
        });
        const ok = res.status < 500;
        return {
            name: "Storage",
            status: ok ? "ok" : "error",
            latencyMs: Date.now() - t0,
        };
    } catch (err: unknown) {
        const isConnRefused =
            err instanceof Error && err.message.includes("ECONNREFUSED");
        return {
            name: "Storage",
            status: isConnRefused ? "error" : "starting",
        };
    }
}

async function checkMem0(): Promise<ServiceResult> {
    const t0 = Date.now();
    const url = process.env.MEM0_SERVICE_URL;
    if (!url) return { name: "Memory (Mem0)", status: "error" };
    try {
        const res = await fetch(`${url}/health`, {
            signal: AbortSignal.timeout(4000),
        });
        return {
            name: "Memory (Mem0)",
            status: res.ok ? "ok" : "error",
            latencyMs: Date.now() - t0,
        };
    } catch (err: unknown) {
        const isConnRefused =
            err instanceof Error && err.message.includes("ECONNREFUSED");
        return {
            name: "Memory (Mem0)",
            status: isConnRefused ? "error" : "starting",
        };
    }
}

// Cache Anthropic check — a real API call, so we limit to once every 5 minutes
let _anthropicCache: { result: ServiceResult; expiresAt: number } | null = null;

async function checkAnthropicLLM(): Promise<ServiceResult> {
    const now = Date.now();
    if (_anthropicCache && now < _anthropicCache.expiresAt) {
        return _anthropicCache.result;
    }

    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
        return { name: "LLM (Anthropic)", status: "error", message: "API key mancante" };
    }

    const t0 = Date.now();
    try {
        const client = new Anthropic({ apiKey });
        await client.messages.create({
            model: "claude-haiku-4-5-20251001",
            max_tokens: 1,
            messages: [{ role: "user", content: "hi" }],
        });
        const result: ServiceResult = {
            name: "LLM (Anthropic)",
            status: "ok",
            latencyMs: Date.now() - t0,
        };
        _anthropicCache = { result, expiresAt: now + 5 * 60 * 1000 };
        return result;
    } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        const isBilling = msg.includes("credit balance") || msg.includes("billing");
        const result: ServiceResult = {
            name: "LLM (Anthropic)",
            status: "error",
            message: isBilling ? "Credito esaurito — aggiungi crediti su console.anthropic.com" : undefined,
        };
        // Cache errors for 2 minutes (don't hammer the API on repeated failures)
        _anthropicCache = { result, expiresAt: now + 2 * 60 * 1000 };
        return result;
    }
}

statusRouter.get("/", async (_req, res) => {
    const [database, storage, memory, llm] = await Promise.all([
        checkDatabase(),
        checkMinio(),
        checkMem0(),
        checkAnthropicLLM(),
    ]);
    res.json({ services: [database, storage, memory, llm] });
});
