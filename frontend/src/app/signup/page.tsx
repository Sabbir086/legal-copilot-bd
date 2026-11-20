"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { ArrowLeft, Eye, EyeOff, Landmark, LoaderCircle, ShieldCheck } from "lucide-react";
import { getBackendUser, saveSession, signIn, signUp } from "@/lib/auth";

export default function SignUpPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (email.trim().toLowerCase() === "joysabbir086@gmail.com") {
      setError("এই email Super Admin-এর জন্য সংরক্ষিত। Sign in পেজ ব্যবহার করুন।");
      return;
    }
    if (pw.length < 8) {
      setError("Password কমপক্ষে ৮ অক্ষরের হতে হবে।");
      return;
    }
    if (pw !== confirm) {
      setError("দুইটি password মিলছে না।");
      return;
    }

    setLoading(true);
    try {
      let session = await signUp(email, pw);
      if (!session.access_token) session = await signIn(email, pw);
      saveSession(session);
      const profile = await getBackendUser(session.access_token);
      router.replace(profile.role === "admin" || profile.role === "super_admin" ? "/admin" : "/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up সম্পন্ন হয়নি।");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page auth-signup-page">
      <section className="auth-visual-panel">
        <Link href="/" className="auth-visual-brand"><Landmark size={34} /><span><b>MyLegal AI</b><small>Bangladesh Legal Assistant</small></span></Link>
        <div className="auth-visual-copy">
          <span>CREATE YOUR SECURE WORKSPACE</span>
          <h2>আপনার আইনি কাজের সহযাত্রী হিসেবে MyLegal AI।</h2>
          <p>একটি account তৈরি করে AI chat, conversation history ও document analysis ব্যবহার শুরু করুন।</p>
        </div>
        <div className="auth-visual-footer"><ShieldCheck size={16} /> Private workspace · Bangladesh 🇧🇩</div>
      </section>

      <section className="auth-form-panel">
        <Link className="auth-back" href="/"><ArrowLeft size={16} /> Back to Home</Link>
        <div className="auth-card">
          <div className="auth-logo"><Landmark size={24} /></div>
          <span className="auth-kicker">CREATE ACCOUNT</span>
          <h1>Create an Account</h1>
          <p>MyLegal AI-তে যোগ দিন এবং আপনার ব্যক্তিগত legal workspace চালু করুন।</p>

          <form onSubmit={submit}>
            <label htmlFor="signup-email">Official email address</label>
            <input id="signup-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@example.com" autoComplete="email" required />

            <label htmlFor="signup-password">Password</label>
            <div className="password-input">
              <input id="signup-password" type={show ? "text" : "password"} value={pw} onChange={(e) => setPw(e.target.value)} placeholder="কমপক্ষে ৮ অক্ষর" autoComplete="new-password" required />
              <button type="button" onClick={() => setShow(!show)} aria-label={show ? "Hide password" : "Show password"}>{show ? <EyeOff size={18} /> : <Eye size={18} />}</button>
            </div>

            <label htmlFor="signup-confirm">Confirm password</label>
            <input id="signup-confirm" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="আবার password লিখুন" autoComplete="new-password" required />

            {error && <div className="auth-error" role="alert">{error}{/email.*(confirm|verification)|confirm.*email/i.test(error) && <><br /><small>Supabase Dashboard → Authentication → Providers → Email-এ Email Confirmation setting পরীক্ষা করুন।</small></>}</div>}
            <button className="auth-submit" disabled={loading}>{loading ? <LoaderCircle className="spin" size={18} /> : "Register"}</button>
          </form>

          <div className="auth-meta"><span>আগে থেকেই account আছে? <Link href="/signin">Login</Link></span></div>
          <small className="auth-footnote">নির্ধারিত Super Admin email ছাড়া অন্য সব নতুন account default User role পাবে।</small>
        </div>
      </section>
    </main>
  );
}
