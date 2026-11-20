"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { ArrowLeft, Landmark, LoaderCircle, MailCheck, ShieldCheck } from "lucide-react";
import { requestPasswordReset } from "@/lib/auth";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await requestPasswordReset(email, `${window.location.origin}/reset-password`);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset email পাঠানো যায়নি।");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page auth-recovery-page">
      <section className="auth-visual-panel">
        <Link href="/" className="auth-visual-brand"><Landmark size={34} /><span><b>MyLegal AI</b><small>Bangladesh Legal Assistant</small></span></Link>
        <div className="auth-visual-copy"><span>ACCOUNT RECOVERY</span><h2>আপনার workspace-এ আবার ফিরে আসুন।</h2><p>নিরাপদ password reset link ব্যবহার করে account access পুনরুদ্ধার করুন।</p></div>
        <div className="auth-visual-footer"><ShieldCheck size={16} /> Secure account recovery · Bangladesh 🇧🇩</div>
      </section>
      <section className="auth-form-panel">
        <Link className="auth-back" href="/signin"><ArrowLeft size={16} /> Back to sign in</Link>
        <div className="auth-card">
          <div className="auth-logo"><Landmark size={24} /></div>
          <span className="auth-kicker">ACCOUNT RECOVERY</span>
          <h1>Password reset</h1>
          <p>আপনার account-এর email address লিখুন। Reset link পাঠানো হবে।</p>
          {done ? (
            <div className="auth-success"><MailCheck size={25} /><b>Reset email অনুরোধ পাঠানো হয়েছে</b><span>Inbox ও spam folder পরীক্ষা করুন।</span></div>
          ) : (
            <form onSubmit={submit}>
              <label htmlFor="recovery-email">Email address</label>
              <input id="recovery-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required placeholder="name@example.com" autoComplete="email" />
              {error && <div className="auth-error" role="alert">{error}</div>}
              <button className="auth-submit" disabled={loading}>{loading ? <LoaderCircle className="spin" size={18} /> : "Send reset link"}</button>
            </form>
          )}
          <div className="auth-meta"><Link href="/signin">Sign in</Link></div>
        </div>
      </section>
    </main>
  );
}
