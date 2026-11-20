import Link from "next/link";
import { ArrowRight, BookOpen, FileSearch, Gavel, ShieldCheck, Sparkles } from "lucide-react";

export default function LandingPage() {
  return (
    <main className="landing-page">
      <nav className="landing-nav">
        <Link href="/" className="landing-brand"><span className="landing-brand-icon"><Gavel size={22} /></span><span><b>Legal Copilot BD</b><small>Bangladesh Legal Assistant</small></span></Link>
        <div className="landing-links"><Link href="/signin">Sign in</Link><Link className="landing-nav-cta" href="/dashboard">Dashboard <ArrowRight size={15} /></Link></div>
      </nav>
      <section className="landing-hero">
        <div className="landing-copy">
          <span className="landing-kicker"><Sparkles size={14} /> AI-powered legal research workspace</span>
          <h1>বাংলাদেশের আইন বুঝুন। <span>ঘটনা থেকে সম্ভাব্য ধারা খুঁজুন।</span></h1>
          <p>নিজের ভাষায় ঘটনা বা মামলার বয়ান লিখুন। Penal Code-এর সংরক্ষিত ধারার পাঠ্য থেকে সম্ভাব্য প্রাসঙ্গিক ধারা, আইনগত উপাদান এবং PDF-এ থাকা শাস্তির তথ্য খুঁজে পেতে সহায়তা নিন।</p>
          <div className="landing-actions"><Link href="/signin" className="landing-primary">চ্যাট শুরু করুন <ArrowRight size={17} /></Link><Link href="/signup" className="landing-secondary">নতুন অ্যাকাউন্ট তৈরি</Link></div>
          <div className="landing-trust"><ShieldCheck size={16} /> ব্যক্তিগত অ্যাকাউন্ট · নিরাপদ সেশন · conversation history</div>
        </div>
        <div className="landing-visual">
          <div className="landing-orbit orbit-one" /><div className="landing-orbit orbit-two" />
          <div className="landing-visual-card">
            <div className="visual-card-top"><span className="visual-mark"><Gavel size={19} /></span><span>Legal Copilot BD</span><span className="visual-status">Ready</span></div>
            <div className="visual-user-msg">একজন ব্যক্তি মিথ্যা পরিচয়ে টাকা নিয়েছে। সম্ভাব্য কোন ধারা হতে পারে?</div>
            <div className="visual-ai-msg"><div className="visual-ai-head"><Sparkles size={15} /> সম্ভাব্য আইনি বিশ্লেষণ</div><b>প্রাথমিক যাচাই দরকার</b><p>ঘটনার উপাদান ও প্রমাণ মিলিয়ে প্রাসঙ্গিক ধারা খুঁজে দেখা হবে।</p><div className="visual-tags"><span>ধারা অনুসন্ধান</span><span>উৎস-পাঠ্য</span><span>শাস্তির তথ্য</span></div></div>
          </div>
        </div>
      </section>
      <section className="landing-features">
        <article><span><BookOpen size={20} /></span><h3>আইনের ধারাভিত্তিক অনুসন্ধান</h3><p>Penal Code-এর ধারা ও মূল পাঠ্য থেকে প্রাসঙ্গিক তথ্য উদ্ধার।</p></article>
        <article><span><FileSearch size={20} /></span><h3>ঘটনা ও মামলার বয়ান বিশ্লেষণ</h3><p>ঘটনার facts, সম্ভাব্য উপাদান এবং অনুপস্থিত তথ্য আলাদা করে দেখা।</p></article>
        <article><span><ShieldCheck size={20} /></span><h3>ব্যক্তিগত workspace</h3><p>প্রতিটি account-এর নিজস্ব conversation এবং document workspace।</p></article>
      </section>
      <footer className="landing-footer">প্রাথমিক আইনি তথ্য সহায়তা মাত্র; আইনজীবীর পরামর্শ বা সর্বশেষ সরকারি আইন যাচাইয়ের বিকল্প নয়।</footer>
    </main>
  );
}
