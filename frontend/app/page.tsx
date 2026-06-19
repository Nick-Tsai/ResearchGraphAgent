"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { createProject, listProjects } from "@/lib/api";
import type { Project } from "@/lib/types";

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export default function HomePage() {
  const router = useRouter();
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<Project[]>([]);

  useEffect(() => {
    listProjects()
      .then(setRecent)
      .catch(() => {});
  }, []);

  async function handleCreate() {
    const trimmed = topic.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    try {
      const project = await createProject(trimmed);
      router.push(`/projects/${project.id}`);
    } catch (error: unknown) {
      setError(getErrorMessage(error, "Failed to create project"));
      setLoading(false);
    }
  }

  const statusColors: Record<string, string> = {
    draft: "bg-gray-100 text-gray-600",
    running: "bg-blue-100 text-blue-700",
    complete: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };

  return (
    <main className="max-w-xl mx-auto flex flex-col min-h-screen p-8">
      <h1 className="text-xl font-semibold tracking-tight mb-8 text-center">
        Research Graph Agent
      </h1>

      <div className="flex gap-3 mb-6">
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          placeholder="Enter a research topic..."
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          disabled={loading}
        />
        <button
          onClick={handleCreate}
          disabled={loading || !topic.trim()}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
        >
          {loading ? "Creating..." : "Create"}
        </button>
      </div>

      {error && (
        <p className="mb-4 text-sm text-red-600 bg-red-50 px-4 py-2 rounded-lg border border-red-200">
          {error}
        </p>
      )}

      {recent.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Recent Projects
          </h2>
          <ul className="divide-y divide-gray-100 border border-gray-200 rounded-lg overflow-hidden">
            {recent.map((p) => (
              <li key={p.id}>
                <button
                  onClick={() => router.push(`/projects/${p.id}`)}
                  className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors flex items-center justify-between gap-3"
                >
                  <span className="text-sm text-gray-800 truncate">{p.topic}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${
                      statusColors[p.status] || statusColors.draft
                    }`}
                  >
                    {p.status}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p className="mt-auto pt-8 text-xs text-gray-400 text-center">
        Enter a research topic to decompose it into structured dimensions and subquestions.
      </p>
    </main>
  );
}
