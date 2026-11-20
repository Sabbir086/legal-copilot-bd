"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, FormEvent, KeyboardEvent as ReactKeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getBackendUser, getSession, getValidSession, signOut } from "@/lib/auth";
import {
  AlertCircle, ArrowUp, Bot, Check, ChevronDown, FileText, FolderOpen, Gavel,
  LoaderCircle, LogOut, MessageSquare, Paperclip, Plus, Scale, Send, ShieldCheck,
  Sparkles, Trash2, UploadCloud, X,
} from "lucide-react";

type Conversation = {
  id: string;
  title: string;
  jurisdiction: string;
  language: string;
  created_at: string;
  updated_at: string;
};
type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string;
};
type Attachment = {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  document_type: string;
  document_type_bn: string;
  page_count: number;
  extracted_characters: number;
  parse_status: "uploaded" | "ready" | "failed";
  document_id?: string;
  created_at: string;
};
type DocumentAnalysis = {
  document_id: string;
  filename: string;
  status: "queued" | "processing" | "partial" | "completed" | "failed" | "needs_ocr" | "ocr_unavailable";
  document_type?: string | null;
  classification_confidence?: number | null;
  summary?: string | null;
  page_count?: number;
  block_count?: number;
  extracted_characters?: number;
  segments?: Array<{
    segment_index: number;
    heading?: string | null;
    clause_number?: string | null;
    content?: string;
    text?: string;
    start_locator?: Record<string, string | number | null>;
    end_locator?: Record<string, string | number | null>;
    has_overlap?: boolean;
  }>;
  sections_error?: string | null;
  facts?: Array<{
    id?: string;
    field: string;
    value?: string | null;
    supporting_quote?: string | null;
    confidence: number;
    needs_review: boolean;
    uncertainty_reason?: string | null;
    evidence_locator?: Record<string, string | number | null>;
    extraction_method?: string;
  }>;
  uncertainty_notes?: string[];
  prompt_injection?: { detected?: boolean; signals?: string[] };
  last_error_message?: string | null;
  analysis_error?: string | null;
};

type ApiError = { detail?: string };
const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const MAX_FILE_BYTES = 20 * 1024 * 1024;
const MAX_FILES = 8;
const ALLOWED_FILE = /\.(pdf|docx|png|jpe?g|webp)$/i;

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
function relativeDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "এখন";
  return new Intl.DateTimeFormat("bn-BD", { day: "numeric", month: "short" }).format(date);
}
function errorMessage(payload: ApiError, fallback: string) {
  return typeof payload.detail === "string" ? payload.detail : fallback;
}

export default function Home() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messageInputRef = useRef<HTMLTextAreaElement>(null);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState("");
  const [userRole, setUserRole] = useState<"user" | "admin" | "super_admin">("user");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [documentAnalyses, setDocumentAnalyses] = useState<Record<string, DocumentAnalysis>>({});
  const [retryingDocumentId, setRetryingDocumentId] = useState<string | null>(null);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [draft, setDraft] = useState("");
  const [view, setView] = useState<"chat" | "documents">("chat");
  const [loading, setLoading] = useState(true);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [creating, setCreating] = useState(false);
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);

  const activeConversation = useMemo(
    () => conversations.find((item) => item.id === activeConversationId) || null,
    [conversations, activeConversationId],
  );

  const apiFetch = useCallback(async (path: string, init: RequestInit = {}) => {
    if (!workspaceId) throw new Error("Workspace প্রস্তুত হচ্ছে। আবার চেষ্টা করুন।");
    const session = await getValidSession();
    const token = session?.access_token || accessToken;
    if (!token) throw new Error("Session পাওয়া যায়নি। আবার sign in করুন।");
    if (session?.access_token && session.access_token !== accessToken) setAccessToken(session.access_token);
    const headers = new Headers(init.headers);
    headers.set("X-Workspace-ID", workspaceId);
    headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
    const payload = await response.json().catch(() => ({}));
    if (response.status === 401) {
      if (typeof window !== "undefined") window.location.href = "/signin";
    }
    if (!response.ok) throw new Error(errorMessage(payload as ApiError, `Request failed (${response.status})`));
    return payload;
  }, [workspaceId, accessToken]);

  useEffect(() => {
    if (view !== "documents" || attachments.length === 0 || !workspaceId) return;
    let cancelled = false;
    const refreshAnalyses = async () => {
      const results = await Promise.all(attachments.map(async (file) => {
        try {
          const documentId = file.document_id || file.id;
          const payload = await apiFetch(`/api/v1/documents/${documentId}/analysis`) as DocumentAnalysis;
          let segments: DocumentAnalysis["segments"] = [];
          let sectionsError: string | null = null;
          try {
            const segmentPayload = await apiFetch(`/api/v1/documents/${documentId}/segments?limit=8&offset=0`);
            segments = (segmentPayload.items || []) as DocumentAnalysis["segments"];
          } catch (error) {
            sectionsError = error instanceof Error ? error.message : "Extracted sections could not be loaded.";
          }
          return [documentId, { ...payload, segments, sections_error: sectionsError }] as const;
        } catch (error) {
          return [file.document_id || file.id, {
            document_id: file.document_id || file.id, status: "queued",
            analysis_error: error instanceof Error ? error.message : "Document analysis could not be loaded.",
          } as DocumentAnalysis] as const;
        }
      }));
      if (!cancelled) {
        setDocumentAnalyses((current) => {
          const next = { ...current };
          for (const item of results) if (item) next[item[0]] = item[1];
          return next;
        });
      }
    };
    void refreshAnalyses();
    const timer = window.setInterval(() => { void refreshAnalyses(); }, 5000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [view, attachments, workspaceId, apiFetch]);

  async function retryDocument(documentId: string) {
    setRetryingDocumentId(documentId);
    try {
      await apiFetch(`/api/v1/documents/${documentId}/retry`, { method: "POST" });
      setNotice("নথি পুনরায় বিশ্লেষণের জন্য queue করা হয়েছে। / Document retry queued.");
      setDocumentAnalyses((current) => ({
        ...current,
        [documentId]: { ...current[documentId], document_id: documentId, status: "queued" },
      }));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Retry করা যায়নি।");
    } finally {
      setRetryingDocumentId(null);
    }
  }

  const refreshConversations = useCallback(async () => {
    const payload = await apiFetch("/api/v1/conversations");
    setConversations((payload.conversations || []) as Conversation[]);
  }, [apiFetch]);

  const loadConversation = useCallback(async (conversationId: string) => {
    setLoadingConversation(true);
    setActiveConversationId(conversationId);
    setView("chat");
    setNotice("");
    setPendingFiles([]);
    try {
      const payload = await apiFetch(`/api/v1/conversations/${conversationId}`);
      setMessages((payload.messages || []) as ChatMessage[]);
      setAttachments((payload.attachments || []) as Attachment[]);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Conversation লোড করা যায়নি।");
    } finally {
      setLoadingConversation(false);
    }
  }, [apiFetch]);

  useEffect(() => {
    let cancelled = false;
    async function initialize() {
      try {
        const session = getSession();
        if (!session?.access_token) {
          router.replace("/signin");
          setLoading(false);
          return;
        }
        if (cancelled) return;
        setAccessToken(session.access_token);
        setUserEmail(session.user.email || "");
        try {
          const profile = await getBackendUser(session.access_token);
          if (!cancelled) setUserRole(profile.role);
        } catch (error) {
          if (!cancelled) setNotice(error instanceof Error ? error.message : "Account যাচাই করা যায়নি।");
        }
        let id = window.localStorage.getItem(`mylegal_workspace_id_${session.user.id}`);
        if (!id) {
          id = window.crypto.randomUUID();
          window.localStorage.setItem(`mylegal_workspace_id_${session.user.id}`, id);
        }
        if (cancelled) return;
        setWorkspaceId(id);
      } catch {
        setNotice("Browser local storage প্রয়োজন। Private browsing restriction বন্ধ করে আবার চেষ্টা করুন।");
        setLoading(false);
      }
    }
    void initialize();
    return () => { cancelled = true; };
  }, [router]);

  useEffect(() => {
    if (!workspaceId || !accessToken) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [healthResponse, listPayload] = await Promise.all([
          fetch(`${API_BASE}/health`).catch(() => null),
          apiFetch("/api/v1/conversations"),
        ]);
        if (cancelled) return;
        setApiOnline(Boolean(healthResponse?.ok));
        const items = (listPayload.conversations || []) as Conversation[];
        setConversations(items);
        if (items.length > 0) {
          const first = items[0];
          setActiveConversationId(first.id);
          const detail = await apiFetch(`/api/v1/conversations/${first.id}`);
          if (!cancelled) {
            setMessages((detail.messages || []) as ChatMessage[]);
            setAttachments((detail.attachments || []) as Attachment[]);
          }
        }
      } catch (error) {
        if (!cancelled) {
          setApiOnline(false);
          setNotice(error instanceof Error ? error.message : "Backend বা Supabase সংযোগ করা যাচ্ছে না।");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [workspaceId, accessToken, apiFetch]);

  async function createConversation() {
    if (!workspaceId || creating) return null;
    setCreating(true);
    try {
      const payload = await apiFetch("/api/v1/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "নতুন আইনি আলোচনা", language: "auto" }),
      });
      const conversation = payload as Conversation;
      setConversations((items) => [conversation, ...items]);
      setActiveConversationId(conversation.id);
      setMessages([]);
      setAttachments([]);
      setPendingFiles([]);
      setView("chat");
      setNotice("");
      return conversation.id;
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "নতুন conversation তৈরি হয়নি।");
      return null;
    } finally {
      setCreating(false);
    }
  }

  function chooseFiles(event: ChangeEvent<HTMLInputElement>) {
    const chosen = Array.from(event.target.files || []);
    event.target.value = "";
    if (!chosen.length) return;
    const invalid = chosen.find((file) => !ALLOWED_FILE.test(file.name) || file.size === 0 || file.size > MAX_FILE_BYTES || (/\.(png|jpe?g|webp)$/i.test(file.name) && file.size > 8 * 1024 * 1024));
    if (invalid) {
      setNotice(`${invalid.name}: PDF/DOCX (২০ MB) অথবা PNG/JPG/WEBP ছবি (৮ MB) যুক্ত করুন।`);
      return;
    }
    if (attachments.length + pendingFiles.length + chosen.length > MAX_FILES) {
      setNotice(`একটি conversation-এ সর্বোচ্চ ${MAX_FILES}টি ফাইল যুক্ত করা যাবে।`);
      return;
    }
    const currentImageBytes = attachments.filter((file) => file.mime_type.startsWith("image/")).reduce((sum, file) => sum + file.size_bytes, 0);
    const pendingImageBytes = pendingFiles.filter((file) => /\.(png|jpe?g|webp)$/i.test(file.name)).reduce((sum, file) => sum + file.size, 0);
    const chosenImageBytes = chosen.filter((file) => /\.(png|jpe?g|webp)$/i.test(file.name)).reduce((sum, file) => sum + file.size, 0);
    if (currentImageBytes + pendingImageBytes + chosenImageBytes > 12 * 1024 * 1024) {
      setNotice("একটি conversation-এ সব image মিলিয়ে সর্বোচ্চ ১২ MB যুক্ত করা যাবে।");
      return;
    }
    setPendingFiles((files) => [...files, ...chosen]);
    setNotice(`${chosen.length}টি ফাইল যুক্ত করার জন্য প্রস্তুত।`);
  }

  async function uploadPendingFiles(conversationId: string) {
    if (!pendingFiles.length) return;
    setUploading(true);
    const body = new FormData();
    pendingFiles.forEach((file) => body.append("files", file));
    try {
      const payload = await apiFetch(`/api/v1/conversations/${conversationId}/attachments`, {
        method: "POST",
        body,
      });
      const added = (payload.attachments || []) as Attachment[];
      setAttachments((items) => [...items, ...added]);
      setPendingFiles([]);
      setNotice(`${added.length}টি ফাইল সংযুক্ত হয়েছে। এখন AI Chat বা Document Analysis থেকে ব্যবহার করতে পারবেন।`);
    } finally {
      setUploading(false);
    }
  }

  async function sendMessage(event?: FormEvent<HTMLFormElement>, suggested?: string) {
    event?.preventDefault();
    if (sending || uploading) return;
    const message = (suggested ?? draft).trim();
    if (!message && pendingFiles.length === 0 && attachments.length === 0) return;
    setSending(true);
    setNotice("");
    let targetConversationId = activeConversationId;
    try {
      if (!targetConversationId) targetConversationId = await createConversation();
      if (!targetConversationId) throw new Error("Conversation তৈরি করা যায়নি।");
      if (pendingFiles.length) await uploadPendingFiles(targetConversationId);
      const finalMessage = message || "সংযুক্ত নথিগুলোর মূল বিষয় সহজ ভাষায় সংক্ষেপে ব্যাখ্যা করুন। নথি থেকে কোন তথ্য নিশ্চিত এবং কোনটি অনিশ্চিত তা আলাদা করে বলুন।";
      const optimistic: ChatMessage = { id: `pending-${Date.now()}`, role: "user", content: finalMessage };
      setMessages((items) => [...items, optimistic]);
      setDraft("");
      const payload = await apiFetch(`/api/v1/conversations/${targetConversationId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: finalMessage }),
      });
      const assistant = payload.message as ChatMessage;
      setMessages((items) => [...items.filter((item) => !item.id.startsWith("pending-")), { id: `user-${Date.now()}`, role: "user", content: finalMessage }, assistant]);
      await refreshConversations();
      setActiveConversationId(targetConversationId);
      setView("chat");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "বার্তা পাঠানো যায়নি।");
      if (targetConversationId) {
        try {
          const detail = await apiFetch(`/api/v1/conversations/${targetConversationId}`);
          setMessages((detail.messages || []) as ChatMessage[]);
        } catch { /* keep the visible error */ }
      }
    } finally {
      setSending(false);
      messageInputRef.current?.focus();
    }
  }

  async function deleteConversation(item: Conversation) {
    if (!window.confirm(`“${item.title}” conversation মুছে ফেলবেন?`)) return;
    setDeletingId(item.id);
    try {
      await apiFetch(`/api/v1/conversations/${item.id}`, { method: "DELETE" });
      const remaining = conversations.filter((conversation) => conversation.id !== item.id);
      setConversations(remaining);
      if (activeConversationId === item.id) {
        setActiveConversationId(null);
        setMessages([]);
        setAttachments([]);
      }
      setNotice("Conversation মুছে ফেলা হয়েছে।");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Conversation মুছতে সমস্যা হয়েছে।");
    } finally {
      setDeletingId(null);
    }
  }

  function handleMessageKeyDown(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage();
    }
  }

  const suggestions = [
    "আমি একটি আইনি সমস্যায় পড়েছি। কীভাবে এগোব?",
    "একটি চুক্তি সই করার আগে কী কী যাচাই করা উচিত?",
    "আমার বিরুদ্ধে মামলা হয়েছে—প্রথমে কী করব?",
    "বাংলাদেশে GD ও মামলা করার মধ্যে পার্থক্য কী?",
  ];

  return (
    <main className="workspace-shell">
      <aside className="workspace-sidebar">
        <div className="brand-lockup">
          <span className="brand-mark"><Scale size={22} /></span>
          <span><strong>MyLegal AI</strong><small>বাংলাদেশের AI Legal Assistant</small></span>
        </div>
        <button className="new-chat-button" type="button" onClick={() => void createConversation()} disabled={creating || !workspaceId}>
          {creating ? <LoaderCircle className="spin" size={17} /> : <Plus size={18} />} নতুন আলোচনা
        </button>
        <div className="history-heading"><span>সাম্প্রতিক আলোচনা</span><span>{conversations.length}</span></div>
        <div className="conversation-list">
          {conversations.map((item) => (
            <div key={item.id} className={`conversation-item ${activeConversationId === item.id ? "active" : ""}`}>
              <button type="button" className="conversation-main" onClick={() => void loadConversation(item.id)}>
                <MessageSquare size={16} />
                <span className="conversation-title">{item.title || "নতুন আইনি আলোচনা"}<small>{relativeDate(item.updated_at)}</small></span>
              </button>
              <button type="button" aria-label="Conversation মুছুন" className="delete-chat" onClick={() => void deleteConversation(item)} disabled={deletingId === item.id}>
                {deletingId === item.id ? <LoaderCircle className="spin" size={15} /> : <Trash2 size={14} />}
              </button>
            </div>
          ))}
          {!loading && conversations.length === 0 && <p className="history-empty">এখনো কোনো আলোচনা নেই। নতুন আলোচনা শুরু করুন।</p>}
        </div>
        <div className="sidebar-bottom">
          <div className="jurisdiction-card"><div className="flex items-center gap-2"><Gavel size={17} /><strong>আইনগত এখতিয়ার</strong></div><p>বাংলাদেশ 🇧🇩</p><small>প্রাথমিক আইনি তথ্য সহায়তা; আইনজীবীর বিকল্প নয়।</small></div>
          <div className="workspace-status"><span className={`status-dot ${apiOnline ? "online" : "offline"}`} />{apiOnline ? "Backend সংযুক্ত" : "Backend / Supabase যাচাই করুন"}</div>
        </div>
      </aside>

      <section className="workspace-main">
        <header className="workspace-header">
          <div><div className="eyebrow"><Sparkles size={14} /> বাংলাদেশ-কেন্দ্রিক আইনি সহায়তা</div><h1>{activeConversation?.title || "আপনার ব্যক্তিগত AI Legal Assistant"}</h1></div>
          <div className="header-pills"><span><ShieldCheck size={15} /> {userEmail || "Signed in"}</span>{(userRole === "admin" || userRole === "super_admin") && <Link href="/admin" className="admin-shortcut">Admin panel</Link>}<span className="jurisdiction-pill">বাংলাদেশ 🇧🇩 <ChevronDown size={14} /></span><button type="button" className="logout-shortcut" onClick={() => { void signOut().finally(() => router.replace("/signin")); }}><LogOut size={14}/> Sign out</button></div>
        </header>

        <div className="view-tabs" role="tablist" aria-label="Workspace view">
          <button type="button" role="tab" aria-selected={view === "chat"} className={view === "chat" ? "selected" : ""} onClick={() => setView("chat")}><MessageSquare size={16} /> AI Chat</button>
          <button type="button" role="tab" aria-selected={view === "documents"} className={view === "documents" ? "selected" : ""} onClick={() => setView("documents")}><FolderOpen size={16} /> Document Analysis <span className="tab-count">{attachments.length}</span></button>
        </div>

        {notice && <div className="notice-banner" role="status"><AlertCircle size={17} /><span>{notice}</span><button type="button" aria-label="বার্তা বন্ধ করুন" onClick={() => setNotice("")}><X size={15} /></button></div>}

        {view === "documents" ? (
          <div className="documents-view">
            <div className="documents-intro"><span className="documents-icon"><FileText size={23} /></span><div><h2>Document Analysis Workspace</h2><p>Processing, OCR, detected type, evidence-linked facts ও uncertainty দেখুন। / Review extracted evidence and processing status.</p></div></div>
            {attachments.length === 0 ? (
              <div className="empty-documents"><UploadCloud size={34} /><strong>এখনো কোনো নথি যুক্ত হয়নি</strong><p>AI Chat-এ ফিরে paperclip বাটন দিয়ে PDF বা DOCX যুক্ত করুন।</p><button type="button" onClick={() => setView("chat")}>AI Chat-এ ফিরে যান</button></div>
            ) : (
              <div className="attachment-cards">
                {attachments.map((file) => {
                  const analysis = documentAnalyses[file.document_id || file.id];
                  const status = analysis?.status || "queued";
                  const statusLabel: Record<string, string> = {
                    queued: "Queue-তে আছে / Queued", processing: "বিশ্লেষণ চলছে / Processing",
                    partial: "আংশিক সম্পন্ন / Partial", completed: "সম্পন্ন / Completed",
                    failed: "ব্যর্থ / Failed", needs_ocr: "OCR প্রয়োজন / Needs OCR",
                    ocr_unavailable: "OCR পাওয়া যায়নি / OCR unavailable",
                  };
                  const canRetry = ["partial", "failed", "needs_ocr", "ocr_unavailable"].includes(status);
                  return <article className="attachment-card" key={file.id}>
                    <div className="file-icon"><FileText size={22} /></div>
                    <div className="attachment-info">
                      <strong>{file.filename}</strong>
                      <p>{analysis?.document_type || file.document_type_bn} · {formatBytes(file.size_bytes)}</p>
                      <small>{analysis ? `${(analysis.page_count || 0).toLocaleString("bn-BD")} page · ${(analysis.block_count || 0).toLocaleString("bn-BD")} source block · ${(analysis.extracted_characters || 0).toLocaleString("bn-BD")} characters` : "Analysis state loading… / বিশ্লেষণের অবস্থা লোড হচ্ছে"}</small>
                      {analysis?.classification_confidence != null && <small>Classification confidence: {Math.round(analysis.classification_confidence * 100)}%</small>}
                      {analysis?.summary && <><small>Source-text extractive preview / উৎস-পাঠ থেকে সংক্ষিপ্ত preview (AI legal summary নয়)</small><p className="analysis-summary">{analysis.summary}</p></>}
                      {analysis?.analysis_error && <small className="document-warning">Analysis could not be loaded / বিশ্লেষণ লোড করা যায়নি: {analysis.analysis_error}</small>}
                      {analysis?.segments && analysis.segments.length > 0 && <div className="document-sections">
                        <strong>Extracted sections / নথির অংশ</strong>
                        {analysis.segments.map((segment) => {
                          const locator = segment.start_locator || {};
                          const anchor = locator.page_number != null ? `Page ${locator.page_number}` : [locator.kind, locator.paragraph_index != null ? `Paragraph ${locator.paragraph_index}` : null, locator.table_index != null ? `Table ${locator.table_index}` : null].filter(Boolean).join(" · ");
                          return <div className="document-section" key={segment.segment_index}>
                            <b>{segment.heading || (segment.clause_number ? `Clause ${segment.clause_number}` : `Section ${segment.segment_index}`)}</b>
                            <small>{anchor || "Source block"}{segment.has_overlap ? " · Context overlap" : ""}</small>
                            <p>{(segment.text || segment.content || "").slice(0, 360)}{(segment.text || segment.content || "").length > 360 ? "…" : ""}</p>
                          </div>;
                        })}
                        {analysis.sections_error && <small className="document-warning">Section list could not be loaded: {analysis.sections_error}</small>}
                      </div>}
                      {analysis?.facts && analysis.facts.length > 0 && <div className="document-facts">
                        <strong>Evidence-linked findings / উৎস-সংযুক্ত তথ্য</strong>
                        {analysis.facts.slice(0, 12).map((fact, index) => {
                          const locator = fact.evidence_locator || {};
                          const anchor = locator.page_number != null ? `Page ${locator.page_number}` : [locator.kind, locator.paragraph_index != null ? `Paragraph ${locator.paragraph_index}` : null, locator.table_index != null ? `Table ${locator.table_index}, row ${locator.row_index}` : null].filter(Boolean).join(" · ");
                          return <div className="document-fact" key={`${fact.field}-${index}`}>
                            <span><b>{fact.field.replace(/_/g, " ")}</b>{fact.value ? `: ${fact.value}` : ": Unknown"} · {Math.round(fact.confidence * 100)}%</span>
                            {fact.supporting_quote && <q>{fact.supporting_quote}</q>}
                            <small>{anchor || "Source locator pending"} · {fact.extraction_method === "ocr_rule_based" ? "OCR text" : "Selectable/source text"}{fact.needs_review ? " · Review required" : ""}</small>
                          </div>;
                        })}
                      </div>}
                      {analysis && ["completed", "partial", "needs_ocr", "ocr_unavailable"].includes(analysis.status) && (!analysis.facts || analysis.facts.length === 0) && <small>No supported candidate facts were found yet / প্রমাণ-সমর্থিত candidate তথ্য পাওয়া যায়নি।</small>}
                      {analysis?.uncertainty_notes?.map((note, index) => <small className="document-warning" key={index}>{note}</small>)}
                      {analysis?.prompt_injection?.detected && <small className="document-warning">Prompt-like instructions were detected and treated as untrusted document content.</small>}
                      {analysis?.last_error_message && <small className="document-warning">{analysis.last_error_message}</small>}
                      {canRetry && <button className="document-retry" type="button" onClick={() => void retryDocument(file.document_id || file.id)} disabled={retryingDocumentId === (file.document_id || file.id)}>{retryingDocumentId === (file.document_id || file.id) ? "Retrying…" : "Retry processing / আবার চেষ্টা"}</button>}
                    </div>
                    <span className={`parse-pill ${status === "completed" ? "ready" : ["failed", "partial", "needs_ocr", "ocr_unavailable"].includes(status) ? "pending" : "pending"}`}>{statusLabel[status] || status}</span>
                  </article>;
                })}
              </div>
            )}
            <div className="analysis-next-step"><AlertCircle size={17} /><p><strong>Evidence note:</strong> Extracted facts are candidates linked to source quotes and locators, not verified facts or legal conclusions. OCR text is stored separately from selectable source text; model/visual descriptions are not treated as OCR evidence.</p></div>
          </div>
        ) : (
          <>
            <div className="chat-scroll-area">
              {loading || loadingConversation ? <div className="loading-state"><LoaderCircle className="spin" size={24} /> Conversation প্রস্তুত হচ্ছে…</div> : messages.length === 0 ? (
                <div className="welcome-panel">
                  <div className="welcome-mark"><Scale size={31} /></div>
                  <div className="welcome-eyebrow">WELCOME TO MYLEGAL AI</div>
                  <h2>আইনি বিষয় বুঝুন, পরবর্তী পদক্ষেপ জানুন।</h2>
                  <p>আপনার ঘটনা নিজের ভাষায় লিখুন। চাইলে PDF বা DOCX নথিও যুক্ত করতে পারেন। আমি নথি ও কথোপকথনের প্রাসঙ্গিক তথ্য ধরে উত্তর দেব।</p>
                  <div className="suggestion-grid">
                    {suggestions.map((prompt) => <button type="button" key={prompt} onClick={() => { setDraft(prompt); messageInputRef.current?.focus(); }}>{prompt}<ArrowUp size={15} /></button>)}
                  </div>
                  <div className="welcome-footnote"><ShieldCheck size={15} /> কোনো নথি না থাকলেও সাধারণ আইনি তথ্য জানতে পারবেন।</div>
                </div>
              ) : (
                <div className="message-list">
                  {messages.map((message) => <article className={`message-row ${message.role === "user" ? "from-user" : "from-assistant"}`} key={message.id}>
                    <span className={`message-avatar ${message.role === "user" ? "user-avatar" : "assistant-avatar"}`}>{message.role === "user" ? "আপনি" : <Bot size={18} />}</span>
                    <div className="message-content"><div className="message-author">{message.role === "user" ? "আপনি" : "MyLegal AI"}</div><p>{message.content}</p></div>
                  </article>)}
                  {sending && <article className="message-row from-assistant"><span className="message-avatar assistant-avatar"><Bot size={18} /></span><div className="message-content"><div className="message-author">MyLegal AI</div><p className="typing-indicator"><LoaderCircle className="spin" size={16} /> উত্তর তৈরি হচ্ছে…</p></div></article>}
                </div>
              )}
            </div>
            <div className="composer-wrap">
              {attachments.length > 0 && <div className="attached-context"><Paperclip size={14} /><span>{attachments.length}টি নথি conversation context-এ আছে</span><button type="button" onClick={() => setView("documents")}>দেখুন</button></div>}
              {pendingFiles.length > 0 && <div className="pending-file-list">{pendingFiles.map((file, index) => <span className="pending-file" key={`${file.name}-${index}`}><FileText size={14} />{file.name}<small>{formatBytes(file.size)}</small><button type="button" aria-label="ফাইল সরান" onClick={() => setPendingFiles((items) => items.filter((_, i) => i !== index))}><X size={13} /></button></span>)}</div>}
              <form className="message-composer" onSubmit={(event) => void sendMessage(event)}>
                <input ref={fileInputRef} type="file" accept=".pdf,.docx,.png,.jpg,.jpeg,.webp,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/png,image/jpeg,image/webp" multiple hidden onChange={chooseFiles} />
                <button className="attach-button" type="button" aria-label="নথি যুক্ত করুন" onClick={() => fileInputRef.current?.click()} disabled={sending || uploading}><Paperclip size={19} /></button>
                <textarea ref={messageInputRef} rows={1} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={handleMessageKeyDown} placeholder="আপনার আইনি প্রশ্ন বা ঘটনার বিবরণ লিখুন…" disabled={sending || uploading} />
                <button type="submit" aria-label="বার্তা পাঠান" className="send-button" disabled={sending || uploading || (!draft.trim() && pendingFiles.length === 0 && attachments.length === 0)}>{sending || uploading ? <LoaderCircle className="spin" size={18} /> : <Send size={18} />}</button>
              </form>
              <p className="composer-hint">PDF / DOCX (২০ MB) · PNG / JPG / WEBP (৮ MB) · সর্বোচ্চ ৮টি ফাইল · সব image মিলিয়ে ১২ MB · Enter দিয়ে পাঠান</p>
              <p className="legal-disclaimer">MyLegal AI প্রাথমিক আইনি তথ্য ও document assistance দেয়; এটি আইনজীবীর পরামর্শ বা সরকারি যাচাইয়ের বিকল্প নয়।</p>

            </div>
          </>
        )}
      </section>
    </main>
  );
}
