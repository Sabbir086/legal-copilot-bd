"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { ArrowLeft, Eye, EyeOff, Gavel, LoaderCircle } from "lucide-react";
import { getBackendUser, saveSession, signIn, signUp } from "@/lib/auth";

export default function SignUpPage(){
 const router=useRouter();const[email,setEmail]=useState("");const[pw,setPw]=useState("");const[confirm,setConfirm]=useState("");const[show,setShow]=useState(false);const[loading,setLoading]=useState(false);const[error,setError]=useState("");
 async function submit(e:FormEvent){e.preventDefault();setError("");if(email.trim().toLowerCase()==="joysabbir086@gmail.com"){setError("এই email Super Admin-এর জন্য সংরক্ষিত। Sign in পেজ ব্যবহার করুন।");return;}if(pw.length<8){setError("Password কমপক্ষে ৮ অক্ষরের হতে হবে।");return;}if(pw!==confirm){setError("দুইটি password মিলছে না।");return;}setLoading(true);
  try{let session=await signUp(email,pw);if(!session.access_token){session=await signIn(email,pw);}saveSession(session);const profile=await getBackendUser(session.access_token);router.replace(profile.role==="admin"||profile.role==="super_admin"?"/admin":"/dashboard");}
  catch(err){setError(err instanceof Error?err.message:"Sign up সম্পন্ন হয়নি। Supabase Auth email confirmation setting পরীক্ষা করুন।");}finally{setLoading(false);}}
 return <main className="auth-page"><Link className="auth-back" href="/"><ArrowLeft size={15}/> Home</Link><section className="auth-card"><div className="auth-logo"><Gavel size={22}/></div><span className="auth-kicker">CREATE ACCOUNT</span><h1>নতুন অ্যাকাউন্ট তৈরি করুন</h1><p>Email ও password দিয়ে শুরু করুন। Sign up-এর পর default role হবে User।</p>
 <form onSubmit={submit}><label>Email address</label><input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="name@example.com" autoComplete="email" required/><label>Password</label><div className="password-input"><input type={show?"text":"password"} value={pw} onChange={e=>setPw(e.target.value)} placeholder="কমপক্ষে ৮ অক্ষর" autoComplete="new-password" required/><button type="button" onClick={()=>setShow(!show)}>{show?<EyeOff size={17}/>:<Eye size={17}/>}</button></div><label>Confirm password</label><input type="password" value={confirm} onChange={e=>setConfirm(e.target.value)} placeholder="আবার password লিখুন" autoComplete="new-password" required/>
 {error&&<div className="auth-error">{error}<br/><small>Instant sign up-এর জন্য Supabase Dashboard → Authentication → Providers / Email-এ Confirm email বন্ধ রাখুন।</small></div>}<button className="auth-submit" disabled={loading}>{loading?<LoaderCircle className="spin" size={17}/>:"Create account"}</button></form>
 <div className="auth-meta"><span>আগে থেকেই account আছে? <Link href="/signin">Sign in</Link></span></div><small className="auth-footnote">নির্ধারিত Super Admin email ছাড়া অন্য সব নতুন account User role পাবে।</small></section></main>;
}
