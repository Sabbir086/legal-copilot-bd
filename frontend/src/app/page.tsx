"use client";

import { useRef, useState, type DragEvent, type FormEvent, type KeyboardEvent, type ReactNode } from "react";
import {
  AlertCircle, ArrowDownToLine, ArrowUpRight, Bot, BookOpen, CheckCircle2,
  FileSearch, FileText, HelpCircle, Home as HomeIcon, Landmark, LoaderCircle, MessageCircle,
  Send, ShieldCheck, Sparkles, UploadCloud, X,
} from "lucide-react";

type Risk = {
  title: string;
  category: string;
  severity: "critical" | "high" | "medium" | "low";
  clause_excerpt: string;
  page?: number | null;
  explanation: string;
  recommendation: string;
  evidence_status: string;
};

type Analysis = {
  document_id: string;
  filename: string;
  status: string;
  analysis_method: string;
  analysis_notice?: string | null;
  document_type: string;
  document_type_bn: string;
  document_workflow: string;
  classification_notice?: string;
  extracted_characters: number;
  page_count: number;
  risks: Risk[];
  legal_citations: unknown[];
  citation_notice: string;
  pipeline: Record<string, string>;
  disclaimer: string;
};

type ChatMessage = { role: "user" | "assistant"; content: string };

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const MAX_FILE_BYTES = 20 * 1024 * 1024;

function formatBytes(bytes: number) {
  return bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(0)} KB` : `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function severityLabel(value: Risk["severity"]) {
  return ({ critical: "অতি উচ্চ", high: "উচ্চ", medium: "মাঝারি", low: "কম" })[value];
}

function severityStyle(value: Risk["severity"]) {
  return ({
    critical: "border-rose-200 bg-rose-50 text-rose-700",
    high: "border-orange-200 bg-orange-50 text-orange-700",
    medium: "border-amber-200 bg-amber-50 text-amber-700",
    low: "border-slate-200 bg-slate-50 text-slate-600",
  })[value];
}

function methodLabel(method?: string) {
  if (method === "gemini") return "Gemini AI বিশ্লেষণ";
  if (method === "document_classifier") return "নথির ধরন শনাক্ত";
  return "নিয়মভিত্তিক প্রাথমিক পরীক্ষা";
}

export default function Home() {
  const inputRef = useRef<HTMLInputElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sending, setSending] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [notice, setNotice] = useState("একটি PDF বা DOCX নথি আপলোড করে শুরু করুন।");
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");

  function acceptFile(candidate?: File) {
    if (!candidate) return;
    if (!/\.(pdf|docx)$/i.test(candidate.name)) {
      setFile(null);
      setAnalysis(null);
      setMessages([]);
      setNotice("শুধু PDF অথবা DOCX ফাইল নির্বাচন করুন।");
      return;
    }
    if (candidate.size === 0 || candidate.size > MAX_FILE_BYTES) {
      setFile(null);
      setNotice(candidate.size === 0 ? "ফাইলটি খালি। অন্য ফাইল নির্বাচন করুন।" : "ফাইলের আকার ২০ MB-এর বেশি হতে পারবে না।");
      return;
    }
    setFile(candidate);
    setAnalysis(null);
    setMessages([]);
    setNotice("ফাইল নির্বাচন সম্পন্ন। এখন নথি বিশ্লেষণ করুন।");
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    event.stopPropagation();
    setDragging(false);
    acceptFile(event.dataTransfer.files?.[0]);
  }

  function onDropKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      inputRef.current?.click();
    }
  }

  async function analyzeDocument() {
    if (!file || busy) {
      if (!file) setNotice("প্রথমে একটি PDF বা DOCX ফাইল নির্বাচন করুন।");
      return;
    }
    setBusy(true);
    setAnalysis(null);
    setMessages([]);
    setNotice("নথি আপলোড ও পাঠ্য বিশ্লেষণ করা হচ্ছে…");

    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch(`${API_BASE}/api/v1/documents/analyze`, { method: "POST", body });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "নথি বিশ্লেষণ সম্পন্ন হয়নি।");
      setAnalysis(payload as Analysis);
      setNotice(`${payload.document_type_bn || "নথি"} শনাক্ত হয়েছে। এখন নথি-সহকারীকে প্রশ্ন করতে পারেন।`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Backend API-এর সঙ্গে সংযোগ করা যায়নি।");
    } finally {
      setBusy(false);
    }
  }

  async function sendMessage(event?: FormEvent<HTMLFormElement>, suggested?: string) {
    event?.preventDefault();
    const text = (suggested ?? draft).trim();
    if (!text || !analysis?.document_id || sending) return;

    const previous = messages;
    const nextMessages: ChatMessage[] = [...previous, { role: "user", content: text }];
    setMessages(nextMessages);
    setDraft("");
    setSending(true);

    try {
      const response = await fetch(`${API_BASE}/api/v1/chat/document`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          document_id: analysis.document_id,
          message: text,
          history: previous.slice(-10),
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "উত্তর তৈরি করা যায়নি।");
      setMessages([...nextMessages, { role: "assistant", content: payload.reply }]);
    } catch (error) {
      setMessages([...nextMessages, {
        role: "assistant",
        content: error instanceof Error ? `দুঃখিত, উত্তর তৈরি করা যায়নি: ${error.message}` : "দুঃখিত, এই মুহূর্তে উত্তর দেওয়া যাচ্ছে না।",
      }]);
    } finally {
      setSending(false);
      chatInputRef.current?.focus();
    }
  }

  async function downloadReport() {
    if (!analysis || exporting) return;
    setExporting(true);
    setNotice("প্রাথমিক প্রতিবেদন তৈরি করা হচ্ছে…");
    try {
      const response = await fetch(`${API_BASE}/api/v1/memoranda/${analysis.document_id}/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_name: /^[\x20-\x7E]*$/.test(analysis.filename) ? analysis.filename : "Uploaded document (Bangla filename retained in workspace)", risks: analysis.risks }),
      });
      if (!response.ok) throw new Error("প্রতিবেদন তৈরি করা যায়নি।");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${analysis.document_id}-preliminary-report.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setNotice("প্রাথমিক প্রতিবেদন ডাউনলোড হয়েছে। আইনগত citation এখনো যাচাইকৃত নয়।");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "PDF export ব্যর্থ হয়েছে।");
    } finally {
      setExporting(false);
    }
  }

  const contractDocument = analysis?.document_type === "contract";
  const chatPrompts = analysis?.document_type === "land_record"
    ? ["এই খতিয়ানের নম্বর কত?", "মৌজা ও উপজেলা কী?", "মোট জমির পরিমাণ কত?", "নথিতে কোন কোন দাগ নম্বর আছে?"]
    : ["এই নথির মূল বিষয় কী?", "সবচেয়ে গুরুত্বপূর্ণ শর্তগুলো কী?", "কোন তথ্যগুলো আরও যাচাই করা দরকার?"];

  return (
    <main className="min-h-screen bg-[#f5f7fb] text-slate-800">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-[250px] border-r border-slate-200 bg-white px-5 py-6 lg:flex lg:flex-col">
        <a href="#overview" className="flex items-center gap-3 px-2">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-700"><ScaleIcon /></span>
          <span><strong className="block text-[15px] font-bold tracking-tight text-slate-900">LEGAL COPILOT BD</strong><small className="text-xs text-slate-500">বাংলাদেশি আইন সহকারী</small></span>
        </a>
        <div className="mt-10 px-3 text-[11px] font-semibold tracking-[.13em] text-slate-400">ওয়ার্কস্পেস</div>
        <nav className="mt-3 space-y-1 text-sm">
          <a className="nav-active" href="#overview"><HomeIcon size={17} /> সারসংক্ষেপ</a>
          <a className="nav-link" href="#upload"><FileSearch size={17} /> নথি বিশ্লেষণ</a>
          <a className="nav-link" href="#assistant"><MessageCircle size={17} /> নথি-সহকারী</a>
          <a className="nav-link" href="#findings"><AlertCircle size={17} /> ঝুঁকি ও পর্যবেক্ষণ</a>
          <a className="nav-link" href="#verification"><ShieldCheck size={17} /> আইন ও citation যাচাই</a>
          <a className="nav-link" href="#reports"><FileText size={17} /> প্রতিবেদন</a>
        </nav>
        <div className="mt-auto rounded-2xl border border-blue-100 bg-blue-50/80 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-800"><Landmark size={16} className="text-blue-700" /> এখতিয়ার</div>
          <div className="mt-2 text-sm text-slate-700">বাংলাদেশ 🇧🇩</div>
          <p className="mt-2 text-xs leading-5 text-slate-500">প্রাথমিক AI সহায়তা। সরকারি যাচাইয়ের বিকল্প নয়।</p>
        </div>
      </aside>

      <section className="mx-auto max-w-[1500px] px-4 py-5 sm:px-6 lg:ml-[250px] lg:px-8 lg:py-8">
        <header id="overview" className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-blue-700"><Sparkles size={15} /> বাংলাদেশ-কেন্দ্রিক আইনি তথ্য সহায়তা</div>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">আপনার নথি বুঝতে পাশে আছে Legal Copilot</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">PDF বা DOCX দিন, নথির ধরন শনাক্ত করুন এবং নথির তথ্য নিয়ে বাংলায় প্রশ্ন করুন।</p>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-xs font-medium text-emerald-700"><span className="h-2 w-2 rounded-full bg-emerald-500" /> স্থানীয় সার্ভার প্রস্তুত</div>
        </header>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard icon={<FileText size={19} />} label="পর্যালোচিত নথি" value={analysis ? "১" : "—"} note={analysis ? "সর্বশেষ নথি প্রক্রিয়াকৃত" : "নথি আপলোডের অপেক্ষায়"} />
          <StatCard icon={<AlertCircle size={19} />} label="ঝুঁকি / পর্যবেক্ষণ" value={analysis ? String(analysis.risks.length) : "—"} note={contractDocument ? "নথির প্রমাণসহ সংকেত" : "প্রযোজ্য হলে দেখানো হবে"} />
          <StatCard icon={<ShieldCheck size={19} />} label="যাচাইকৃত আইন" value="০" note="সরকারি citation যাচাই এখনো চালু নয়" />
          <StatCard icon={<MessageCircle size={19} />} label="নথি-সহকারী" value={analysis ? "সক্রিয়" : "প্রস্তুত"} note="আপলোড করা নথি নিয়ে প্রশ্ন করুন" />
        </div>

        <div className="mt-6 grid items-start gap-6 2xl:grid-cols-[minmax(0,1.2fr)_minmax(390px,.8fr)]">
          <div className="space-y-6">
            <section id="upload" className="panel p-5 sm:p-6">
              <div className="flex items-start justify-between gap-3">
                <div><div className="section-kicker">ধাপ ১</div><h2 className="mt-1 text-lg font-bold text-slate-900">নথি আপলোড করুন</h2><p className="mt-1 text-sm text-slate-500">চুক্তিপত্র, খতিয়ান, দলিল বা অন্যান্য PDF/DOCX নথি নির্বাচন করুন।</p></div>
                <span className="rounded-xl bg-blue-50 p-3 text-blue-700"><UploadCloud size={22} /></span>
              </div>
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                className="hidden"
                onChange={(event) => acceptFile(event.target.files?.[0])}
              />
              <div
                role="button"
                tabIndex={0}
                aria-label="PDF অথবা DOCX ফাইল নির্বাচন করুন অথবা এখানে ছেড়ে দিন"
                onClick={() => inputRef.current?.click()}
                onKeyDown={onDropKeyDown}
                onDragOver={(event) => { event.preventDefault(); event.stopPropagation(); setDragging(true); }}
                onDragLeave={(event) => { event.preventDefault(); event.stopPropagation(); setDragging(false); }}
                onDrop={onDrop}
                className={`mt-5 flex min-h-48 cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed px-4 py-6 text-center transition ${dragging ? "border-blue-500 bg-blue-50" : "border-blue-200 bg-slate-50 hover:border-blue-400 hover:bg-blue-50/60"}`}
              >
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-blue-700 shadow-sm"><UploadCloud size={25} /></span>
                <span className="mt-3 font-semibold text-slate-800">{dragging ? "এখানে ফাইল ছেড়ে দিন" : "ফাইল টেনে এনে ছাড়ুন অথবা ব্রাউজ করুন"}</span>
                <span className="mt-2 text-xs text-slate-500">PDF / DOCX · সর্বোচ্চ ২০ MB</span>
                {file && <span className="mt-4 flex max-w-full items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800"><CheckCircle2 size={16} /><span className="max-w-[260px] truncate">{file.name}</span><span className="text-xs">{formatBytes(file.size)}</span><button type="button" aria-label="ফাইল সরান" onClick={(event) => { event.stopPropagation(); setFile(null); setAnalysis(null); setMessages([]); if (inputRef.current) inputRef.current.value = ""; }} className="ml-1 rounded p-1 hover:bg-emerald-100"><X size={14} /></button></span>}
              </div>
              <button type="button" onClick={analyzeDocument} disabled={!file || busy} className="primary-button mt-4 w-full">
                {busy ? <><LoaderCircle className="animate-spin" size={17} /> বিশ্লেষণ চলছে…</> : <>নথি বিশ্লেষণ করুন <ArrowUpRight size={17} /></>}
              </button>
              <p className="mt-3 rounded-xl bg-slate-50 px-3 py-3 text-xs leading-5 text-slate-600" aria-live="polite">{notice}</p>
            </section>

            {analysis && (
              <section id="findings" className="panel p-5 sm:p-6">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div><div className="section-kicker">ধাপ ২</div><h2 className="mt-1 text-lg font-bold text-slate-900">নথি পর্যালোচনার ফলাফল</h2><p className="mt-1 text-sm text-slate-500">{analysis.filename}</p></div>
                  <span className={`rounded-full px-3 py-1.5 text-xs font-semibold ${analysis.analysis_method === "gemini" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"}`}>{methodLabel(analysis.analysis_method)}</span>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  <InfoTile label="নথির ধরন" value={analysis.document_type_bn || "শনাক্ত হয়নি"} />
                  <InfoTile label="পৃষ্ঠা" value={String(analysis.page_count)} />
                  <InfoTile label="উদ্ধার করা অক্ষর" value={analysis.extracted_characters.toLocaleString("bn-BD")} />
                </div>
                {analysis.analysis_notice && <div className="mt-4 flex gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-900"><AlertCircle className="mt-1 shrink-0" size={17} /><p>{analysis.analysis_notice}</p></div>}
                {analysis.document_type === "land_record" && <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50/70 p-4 text-sm leading-6 text-blue-900"><strong>এটি ভূমি-রেকর্ডধর্মী নথি।</strong> চুক্তিপত্রের ঝুঁকি পরীক্ষা এখানে প্রযোজ্য নয়। খতিয়ান, মৌজা, দাগ ও জমির পরিমাণ সম্পর্কে নথিভিত্তিক প্রশ্ন করতে পাশের সহকারী ব্যবহার করুন।</div>}
                {analysis.risks.length > 0 ? <div className="mt-5 space-y-3">{analysis.risks.map((risk, index) => <div key={`${risk.category}-${index}`} className="rounded-xl border border-slate-200 p-4"><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold text-slate-900">{risk.title}</h3><span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${severityStyle(risk.severity)}`}>{severityLabel(risk.severity)}</span></div><p className="mt-2 text-sm leading-6 text-slate-600">{risk.explanation}</p><blockquote className="mt-3 rounded-lg border-l-2 border-blue-400 bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-700">“{risk.clause_excerpt}” <span className="block pt-1 text-xs text-slate-400">পৃষ্ঠা: {risk.page ?? "উল্লেখ নেই"} · নথির উদ্ধৃতি মিলেছে; আইনগত citation যাচাই নয়</span></blockquote><p className="mt-3 text-sm leading-6 text-slate-600"><strong className="text-slate-800">পরবর্তী করণীয়:</strong> {risk.recommendation}</p></div>)}</div> : <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600">{analysis.document_type === "contract" ? "বর্তমান পরীক্ষায় নথি থেকে প্রমাণসমর্থিত ঝুঁকির সংকেত পাওয়া যায়নি। এর অর্থ এই নয় যে নথিতে কোনো ঝুঁকি নেই।" : "এই নথির জন্য contract-risk ফলাফল দেখানো হচ্ছে না। নথির বিষয়বস্তু জানতে নথি-সহকারীকে প্রশ্ন করুন।"}</div>}
                <div id="verification" className="mt-5 rounded-xl border border-slate-200 bg-white p-4"><div className="flex items-center gap-2 font-semibold text-slate-800"><ShieldCheck size={17} className="text-amber-600" /> আইন ও citation যাচাই</div><p className="mt-2 text-sm leading-6 text-slate-500">{analysis.citation_notice || "সরকারি আইন-উৎস, সংশোধনী, কার্যকারিতা ও প্রযোজ্যতা যাচাই এখনো সম্পন্ন হয়নি।"} নথির উদ্ধৃতি মেলা মানেই আইনগত citation যাচাই হওয়া নয়।</p></div>
                <div id="reports" className="mt-4 flex flex-wrap items-center justify-between gap-3"><p className="text-xs leading-5 text-slate-500">প্রতিবেদনটি প্রাথমিক; এটি আইনগত মতামত নয়।</p>{contractDocument ? <button type="button" onClick={downloadReport} disabled={exporting} className="secondary-button">{exporting ? <LoaderCircle size={16} className="animate-spin" /> : <ArrowDownToLine size={16} />} প্রাথমিক ঝুঁকি প্রতিবেদন PDF</button> : <span className="text-xs text-slate-500">এই নথির বিশেষায়িত প্রতিবেদন পরবর্তী ধাপে যুক্ত হবে।</span>}</div>
              </section>
            )}
          </div>

          <section id="assistant" className="panel overflow-hidden 2xl:sticky 2xl:top-6">
            <div className="border-b border-slate-100 bg-gradient-to-r from-blue-50 to-white p-5">
              <div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-100 text-blue-700"><Bot size={21} /></span><div><h2 className="font-bold text-slate-900">আপনার নথি-সহকারী</h2><p className="mt-0.5 text-xs text-slate-500">Gemini AI · বাংলা ও English</p></div><span className="ml-auto h-2.5 w-2.5 rounded-full bg-emerald-500" title="চ্যাট প্রস্তুত" /></div>
              <p className="mt-3 text-sm leading-6 text-slate-600">আপলোড করা নথি থেকে তথ্য খুঁজুন, সহজ ভাষায় ব্যাখ্যা নিন এবং প্রয়োজনীয় প্রশ্ন করুন।</p>
            </div>
            <div className="flex min-h-[360px] max-h-[520px] flex-col p-4">
              <div className="flex-1 space-y-3 overflow-y-auto pr-1">
                <div className="chat-bubble assistant-bubble"><p>আসসালামু আলাইকুম! আমি Legal Copilot-এর নথি-সহকারী। প্রথমে একটি নথি আপলোড ও বিশ্লেষণ করুন। এরপর নথির তথ্য নিয়ে আমাকে প্রশ্ন করতে পারবেন।</p></div>
                {!analysis && <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-center text-xs leading-5 text-slate-500"><HelpCircle className="mx-auto mb-2 text-slate-400" size={20} />নথি বিশ্লেষণের পর এই চ্যাটে প্রশ্ন-উত্তর চালু হবে।</div>}
                {messages.map((item, index) => <div key={index} className={`chat-bubble ${item.role === "user" ? "user-bubble" : "assistant-bubble"}`}><div className="mb-1 text-[10px] font-semibold opacity-70">{item.role === "user" ? "আপনি" : "Legal Copilot"}</div><p className="whitespace-pre-wrap">{item.content}</p></div>)}
                {sending && <div className="chat-bubble assistant-bubble flex items-center gap-2 text-sm text-slate-500"><LoaderCircle size={15} className="animate-spin" /> উত্তর তৈরি হচ্ছে…</div>}
              </div>
              {analysis && <div className="mt-3"><p className="mb-2 text-[11px] font-semibold text-slate-400">প্রশ্নের উদাহরণ</p><div className="flex flex-wrap gap-2">{chatPrompts.slice(0, 3).map((prompt) => <button key={prompt} type="button" disabled={sending} onClick={() => { setDraft(prompt); chatInputRef.current?.focus(); }} className="prompt-chip">{prompt}</button>)}</div></div>}
              <form onSubmit={(event) => sendMessage(event)} className="mt-4 flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-2 shadow-sm focus-within:border-blue-300 focus-within:ring-2 focus-within:ring-blue-50">
                <input ref={chatInputRef} value={draft} onChange={(event) => setDraft(event.target.value)} disabled={!analysis || sending} placeholder={analysis ? "নথি সম্পর্কে প্রশ্ন লিখুন…" : "আগে একটি নথি আপলোড করুন"} className="min-w-0 flex-1 border-0 bg-transparent px-2 py-2 text-sm text-slate-800 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed" />
                <button type="submit" disabled={!analysis || !draft.trim() || sending} aria-label="বার্তা পাঠান" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-700 text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"><Send size={17} /></button>
              </form>
              <p className="mt-2 text-[10px] leading-4 text-slate-400">AI-এর উত্তর নথিভিত্তিক প্রাথমিক সহায়তা। মালিকানা, সত্যতা বা আইনগত বৈধতার সরকারি যাচাই নয়।</p>
            </div>
          </section>
        </div>

        <footer className="mt-8 flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 pt-5 text-xs text-slate-400"><span>© ২০২৬ Legal Copilot BD</span><span>তথ্যভিত্তিক, স্বচ্ছ ও দায়িত্বশীল AI সহায়তা</span></footer>
      </section>
    </main>
  );
}

function ScaleIcon() {
  return <Landmark size={23} />;
}

function StatCard({ icon, label, value, note }: { icon: ReactNode; label: string; value: string; note: string }) {
  return <div className="panel p-4"><div className="flex items-center justify-between text-slate-500"><span className="text-sm">{label}</span><span className="text-blue-700">{icon}</span></div><div className="mt-4 text-2xl font-bold text-slate-900">{value}</div><p className="mt-1 text-xs leading-5 text-slate-500">{note}</p></div>;
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3"><div className="text-xs text-slate-500">{label}</div><div className="mt-1 font-semibold text-slate-800">{value}</div></div>;
}
