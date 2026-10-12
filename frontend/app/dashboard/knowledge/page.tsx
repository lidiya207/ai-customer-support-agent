"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { FileText, MoreHorizontal, Upload, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { StatCard } from "@/components/ui/stat-card";
import {
  listKnowledgeDocuments,
  uploadKnowledgeDocument,
} from "@/lib/api";
import type { KnowledgeDocument } from "@/lib/types";

export default function KnowledgePage() {
  const [uploadOpen, setUploadOpen] = useState(false);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    const data = await listKnowledgeDocuments();
    setDocuments(data);
  }

  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        await load();
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load");
        }
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = useMemo(
    () => ({
      documents: documents.length,
      chunks: documents.reduce((sum, d) => sum + d.chunks, 0),
      indexed: documents.filter((d) => d.status === "indexed").length,
      processing: documents.filter((d) => d.status === "processing").length,
    }),
    [documents]
  );

  async function handleUpload(file: File | null) {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await uploadKnowledgeDocument(file);
      await load();
      setUploadOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">
            Knowledge Base
          </h1>
          <p className="mt-1 max-w-xl text-sm text-muted">
            Manage the information your AI agent uses to answer customer
            questions.
          </p>
          {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
        </div>
        <Button onClick={() => setUploadOpen(true)}>
          <Upload className="h-4 w-4" />
          Upload Document
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Documents" value={stats.documents} />
        <StatCard title="Knowledge Chunks" value={stats.chunks.toLocaleString()} />
        <StatCard title="Indexed" value={stats.indexed} />
        <StatCard title="Processing" value={stats.processing} />
      </div>

      <div className="overflow-x-auto rounded-2xl border border-line/80 bg-surface/90">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead>
            <tr className="border-b border-line bg-canvas/80">
              <th className="px-4 py-3 font-medium text-muted">Name</th>
              <th className="px-4 py-3 font-medium text-muted">Type</th>
              <th className="px-4 py-3 font-medium text-muted">Chunks</th>
              <th className="px-4 py-3 font-medium text-muted">Status</th>
              <th className="px-4 py-3 font-medium text-muted">Uploaded</th>
              <th className="px-4 py-3 font-medium text-muted">Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr
                key={doc.id}
                className="border-b border-line/60 last:border-0 hover:bg-canvas/80"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2 font-medium text-ink">
                    <FileText className="h-4 w-4 text-muted/70" />
                    {doc.name}
                  </div>
                </td>
                <td className="px-4 py-3 text-muted">{doc.type}</td>
                <td className="px-4 py-3 text-muted">{doc.chunks}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={doc.status} />
                </td>
                <td className="px-4 py-3 text-muted">{doc.uploadedAt}</td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    className="rounded-lg p-1.5 text-muted/70 hover:bg-canvas hover:text-ink/80"
                    aria-label="Document actions"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {uploadOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <button
            type="button"
            className="absolute inset-0 bg-black/40"
            aria-label="Close modal"
            onClick={() => setUploadOpen(false)}
          />
          <div className="relative w-full max-w-md rounded-2xl border border-line/80 bg-surface/90 p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-ink">
                Upload Document
              </h2>
              <button
                type="button"
                onClick={() => setUploadOpen(false)}
                className="rounded-lg p-1 text-muted/70 hover:bg-canvas hover:text-ink/80"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="mb-4 text-sm text-muted">
              Upload a .txt, .md, .pdf, or .docx file. The agent will extract
              text, chunk, and index it for RAG.
            </p>
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.md,.pdf,.docx,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="hidden"
              onChange={(e) => void handleUpload(e.target.files?.[0] ?? null)}
            />
            <button
              type="button"
              disabled={uploading}
              onClick={() => fileRef.current?.click()}
              className="flex w-full cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-line bg-canvas px-6 py-10 text-center transition hover:border-line hover:bg-canvas/80"
            >
              <Upload className="mb-3 h-8 w-8 text-muted/70" />
              <p className="text-sm font-medium text-ink">
                {uploading ? "Uploading..." : "Click to browse"}
              </p>
              <p className="mt-1 text-xs text-muted">TXT, MD, PDF, or DOCX</p>
            </button>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setUploadOpen(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
