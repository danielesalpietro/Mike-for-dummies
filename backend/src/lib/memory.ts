const MEM0_URL = process.env.MEM0_SERVICE_URL;

export async function searchMemories(
    query: string,
    userId: string,
    limit = 5,
): Promise<string[]> {
    if (!MEM0_URL) return [];
    try {
        const res = await fetch(`${MEM0_URL}/memories/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query, user_id: userId, limit }),
        });
        if (!res.ok) return [];
        const data = (await res.json()) as { memories: string[] };
        return data.memories ?? [];
    } catch {
        return [];
    }
}

export async function addMemories(
    messages: { role: string; content: string }[],
    userId: string,
): Promise<void> {
    if (!MEM0_URL) return;
    try {
        await fetch(`${MEM0_URL}/memories/add`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ messages, user_id: userId }),
        });
    } catch {
        // memory failures are non-fatal
    }
}
