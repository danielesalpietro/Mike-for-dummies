"use client";

import { useState, useEffect, useCallback } from "react";

export type ServiceStatus = "ok" | "starting" | "error" | "unknown";

export interface ServiceResult {
    name: string;
    status: ServiceStatus;
    latencyMs?: number;
    message?: string;
}

export interface SystemStatus {
    services: ServiceResult[];
    overall: ServiceStatus;
    lastChecked: Date | null;
}

const API_BASE =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:3001";

function deriveOverall(services: ServiceResult[]): ServiceStatus {
    if (services.some((s) => s.status === "error")) return "error";
    if (services.some((s) => s.status === "starting" || s.status === "unknown"))
        return "starting";
    return "ok";
}

export function useServiceStatus(intervalMs = 30_000): SystemStatus {
    const [status, setStatus] = useState<SystemStatus>({
        services: [],
        overall: "unknown",
        lastChecked: null,
    });

    const fetch_ = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/status`, {
                cache: "no-store",
                signal: AbortSignal.timeout(8000),
            });
            if (!res.ok) throw new Error("non-ok");
            const data = (await res.json()) as { services: ServiceResult[] };
            setStatus({
                services: data.services,
                overall: deriveOverall(data.services),
                lastChecked: new Date(),
            });
        } catch {
            setStatus((prev) => ({
                ...prev,
                overall: prev.lastChecked ? "error" : "unknown",
                lastChecked: prev.lastChecked ?? null,
            }));
        }
    }, []);

    useEffect(() => {
        fetch_();
        const id = setInterval(fetch_, intervalMs);
        return () => clearInterval(id);
    }, [fetch_, intervalMs]);

    return status;
}
