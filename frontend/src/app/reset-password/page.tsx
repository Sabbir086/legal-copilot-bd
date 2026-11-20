"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Landmark, LoaderCircle, ShieldCheck } from "lucide-react";
import { updatePassword } from "@/lib/auth";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    setToken(params.get("access_token") || "");
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!token) {
      setError("Reset link invalid বা expired। নতুন reset link নিন।");
      return;
    }
    if (pw.length < 8 || pw !== confirm) {
      setError(pw.length < 8 ? "Password কমপক্ষে ৮ অক্ষরের হতে হবে।" : "দুইটি password মিলছে না।");
      return;
    }
    setLoading(true);
    try {
      await updatePassword(token, pw);
      router.replace("/signin");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Password update হয়নি।");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page auth-recovery-page">
      <section className="auth-visual-panel">
        <Link href="/" className="auth-visual-brand"><Landmark size={34} /><span><b>MyLegal AI</b><small>Bangladesh Legal Assistant</small></span></Link>
        <div className="auth-visual-copy"><span>SECURE YOUR ACCOUNT</span><h2>শক্তিশালী password দিয়ে account সুরক্ষিত রাখুন।</h2><p>নতুন password সেট করার পর আপনার account-এ sign in করতে পারবেন।</p></div>
        <div className="auth-visual-footer"><ShieldCheck size={16} /> Secure account access · Bangladesh 🇧🇩</div>
      </section>
      <section className="auth-form-panel">
        <Link className="auth-back" href="/signin"><ArrowLeft size={16} /> Back to sign in</Link>
        <div className="auth-card">
          <div className="auth-logo"><Landmark size={24} /></div>
          <span className="auth-kicker">NEW PASSWORD</span>
          <h1>নতুন password সেট করুন</h1>
          <p>কমপক্ষে ৮ অক্ষরের password দিন।</p>
          <form onSubmit={submit}>
            <label htmlFor="new-password">New password</label>
            <input id="new-password" type="password" value={pw} onChange={(event) => setPw(event.target.value)} required autoComplete="new-password" />
            <label htmlFor="confirm-new-password">Confirm password</label>
            <input id="confirm-new-password" type="password" value={confirm} onChange={(event) => setConfirm(event.target.value)} required autoComplete="new-password" />
            {error && <div className="auth-error" role="alert">{error}</div>}
            <button className="auth-submit" disabled={loading}>{loading ? <LoaderCircle className="spin" size={18} /> : "Update password"}</button>
          </form>
        </div>
      </section>
    </main>
  );
}
