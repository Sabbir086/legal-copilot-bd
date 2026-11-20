"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { ArrowLeft, Eye, EyeOff, Landmark, LoaderCircle, ShieldCheck } from "lucide-react";
import { bootstrapSuperAdmin, getBackendUser, saveSession, signIn } from "@/lib/auth";

export default function SignInPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      // Only the configured Super Admin credentials can trigger first-time provisioning.
      // The backend compares them against server-side secrets and never returns the password.
      if (email.trim().toLowerCase() === "joysabbir086@gmail.com") {
        try { await bootstrapSuperAdmin(email, password); } catch { /* Existing provisioned accounts continue to sign in. */ }
      }
      const session = await signIn(email, password);
      saveSession(session);
      const profile = await getBackendUser(session.access_token);
      router.replace(profile.role === "admin" || profile.role === "super_admin" ? "/admin" : "/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign in করা যায়নি।");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page auth-signin-page">
      <section className="auth-visual-panel">
        <Link href="/" className="auth-visual-brand"><Landmark size={34} /><span><b>MyLegal AI</b><small>Bangladesh Legal Assistant</small></span></Link>
        <div className="auth-visual-copy">
          <span>YOUR DIGITAL LEGAL WORKSPACE</span>
          <h2>আইনি তথ্য ও বিশ্লেষণ, এখন আরও সহজে।</h2>
          <p>প্রশ্ন করুন, নথি বুঝুন এবং প্রয়োজনীয় তথ্য এক জায়গায় গুছিয়ে রাখুন।</p>
        </div>
        <div className="auth-visual-footer"><ShieldCheck size={16} /> Private workspace · Bangladesh 🇧🇩</div>
      </section>

      <section className="auth-form-panel">
        <Link className="auth-back" href="/"><ArrowLeft size={16} /> Back to Home</Link>
        <div className="auth-card">
          <div className="auth-logo"><Landmark size={24} /></div>
          <span className="auth-kicker">WELCOME BACK</span>
          <h1>Welcome Back</h1>
          <p>আপনার MyLegal AI account-এ প্রবেশ করুন এবং workspace চালু করুন।</p>

          <form onSubmit={submit}>
            <label htmlFor="signin-email">Email address</label>
            <input id="signin-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@example.com" autoComplete="email" required />

            <label htmlFor="signin-password">Password</label>
            <div className="password-input">
              <input id="signin-password" type={show ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="আপনার password" autoComplete="current-password" required />
              <button type="button" onClick={() => setShow(!show)} aria-label={show ? "Hide password" : "Show password"}>{show ? <EyeOff size={18} /> : <Eye size={18} />}</button>
            </div>

            {error && <div className="auth-error" role="alert">{error}</div>}
            <button className="auth-submit" disabled={loading}>{loading ? <LoaderCircle className="spin" size={18} /> : "Sign in"}</button>
          </form>

          <div className="auth-meta"><Link href="/forgot-password">Forgot password?</Link><span>নতুন এখানে? <Link href="/signup">Register</Link></span></div>
          <small className="auth-footnote">আপনার account ও password Supabase Auth-এ নিরাপদভাবে পরিচালিত হয়।</small>
        </div>
      </section>
    </main>
  );
}
