"use client";

import { useState, useRef, useEffect } from "react";
import { useServiceStatus, type ServiceStatus } from "@/app/hooks/useServiceStatus";

const DOT_COLORS: Record<ServiceStatus, string> = {
    ok: "bg-green-500",
    starting: "bg-yellow-400",
    error: "bg-red-500",
    unknown: "bg-gray-400",
};

const LABEL_COLORS: Record<ServiceStatus, string> = {
    ok: "text-green-600",
    starting: "text-yellow-600",
    error: "text-red-600",
    unknown: "text-gray-500",
};

const STATUS_LABELS: Record<ServiceStatus, string> = {
    ok: "Online",
    starting: "Starting…",
    error: "Unavailable",
    unknown: "Unknown",
};

function StatusDot({ status, size = "sm" }: { status: ServiceStatus; size?: "sm" | "lg" }) {
    const sz = size === "lg" ? "h-2.5 w-2.5" : "h-2 w-2";
    const pulse = status === "starting" ? "animate-pulse" : "";
    return (
        <span
            className={`inline-block rounded-full flex-shrink-0 ${sz} ${DOT_COLORS[status]} ${pulse}`}
        />
    );
}

export function ServiceStatusPopover() {
    const { services, overall, lastChecked } = useServiceStatus();
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        function onClickOutside(e: MouseEvent) {
            if (ref.current && !ref.current.contains(e.target as Node)) {
                setOpen(false);
            }
        }
        if (open) document.addEventListener("mousedown", onClickOutside);
        return () => document.removeEventListener("mousedown", onClickOutside);
    }, [open]);

    return (
        <div ref={ref} className="relative">
            <button
                onClick={() => setOpen((v) => !v)}
                title="System status"
                className="flex items-center justify-center h-5 w-5 rounded-full hover:opacity-80 transition-opacity"
                aria-label="System status"
            >
                <StatusDot status={overall} size="lg" />
            </button>

            {open && (
                <div className="absolute bottom-full left-0 mb-2 bg-white rounded-lg shadow-lg border border-gray-200 p-3 z-50 w-56">
                    <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                        System Status
                    </div>
                    <ul className="space-y-2">
                        {services.length === 0 ? (
                            <li className="text-xs text-gray-400">Checking…</li>
                        ) : (
                            services.map((svc) => (
                                <li key={svc.name} className="space-y-0.5">
                                    <div className="flex items-center justify-between gap-2">
                                        <div className="flex items-center gap-2 min-w-0">
                                            <StatusDot status={svc.status} />
                                            <span className="text-sm text-gray-700 truncate">{svc.name}</span>
                                        </div>
                                        <div className="flex items-center gap-1.5 flex-shrink-0">
                                            {svc.latencyMs !== undefined && svc.status === "ok" && (
                                                <span className="text-[11px] text-gray-400">{svc.latencyMs}ms</span>
                                            )}
                                            <span className={`text-[11px] font-medium ${LABEL_COLORS[svc.status]}`}>
                                                {STATUS_LABELS[svc.status]}
                                            </span>
                                        </div>
                                    </div>
                                    {svc.message && (
                                        <p className="text-[11px] text-red-500 pl-4 leading-tight">{svc.message}</p>
                                    )}
                                </li>
                            ))
                        )}
                    </ul>
                    {lastChecked && (
                        <div className="mt-2 pt-2 border-t border-gray-100 text-[11px] text-gray-400">
                            Updated {lastChecked.toLocaleTimeString()}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
