"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { ArrowLeft, Eye, EyeOff, Gavel, LoaderCircle } from "lucide-react";
import { bootstrapSuperAdmin, getBackendUser, saveSession, signIn } from "@/lib/auth";

export default function SignInPage() {
  const router = useRouter();
  const [email,setEmail]=useState(""); const [password,setPassword]=useState("");
  const [show,setShow]=useState(false); const [loading,setLoading]=useState(false); const [error,setError]=useState("");
  async function submit(event: FormEvent) {
    event.preventDefault(); setLoading(true); setError("");
    try {
      // Only the configured Super Admin credentials can trigger first-time provisioning.
      // The backend compares them against server-side secrets and never returns the password.
      if (email.trim().toLowerCase() === "joysabbir086@gmail.com") {
        try { await bootstrapSuperAdmin(email, password); } catch { /* Existing provisioned accounts continue to sign in; invalid credentials fail at Auth. */ }
      }
      const session = await signIn(email,password); saveSession(session);
      const profile = await getBackendUser(session.access_token);
      router.replace(profile.role === "admin" || profile.role === "super_admin" ? "/admin" : "/dashboard");
    } catch (e) { setError(e instanceof Error ? e.message : "Sign in করা যায়নি।"); }
    finally { setLoading(false); }
  }
  return <main className="auth-page"><Link className="auth-back" href="/"><ArrowLeft size={15}/> Home</Link><section className="auth-card"><div className="auth-logo"><Gavel size={22}/></div><span className="auth-kicker">WELCOME BACK</span><h1>আপনার অ্যাকাউন্টে প্রবেশ করুন</h1><p>Sign in করলে আপনার Legal Copilot workspace খুলবে।</p>
    <form onSubmit={submit}><label>Email address</label><input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="name@example.com" autoComplete="email" required/><label>Password</label><div className="password-input"><input type={show?"text":"password"} value={password} onChange={e=>setPassword(e.target.value)} placeholder="আপনার password" autoComplete="current-password" required/><button type="button" onClick={()=>setShow(!show)} aria-label="Toggle password">{show?<EyeOff size={17}/>:<Eye size={17}/>}</button></div>
    {error&&<div className="auth-error">{error}</div>}<button className="auth-submit" disabled={loading}>{loading?<LoaderCircle className="spin" size={17}/>:"Sign in"}</button></form>
    <div className="auth-meta"><Link href="/forgot-password">Forgot password?</Link><span>নতুন এখানে? <Link href="/signup">Sign up</Link></span></div>
    <small className="auth-footnote">আপনার account/password Supabase Auth-এ নিরাপদভাবে পরিচালিত হয়।</small>
  </section></main>;
}
