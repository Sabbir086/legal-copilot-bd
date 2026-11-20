import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Check,
  FileSearch,
  Landmark,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

const benefits = [
  "আইন ও নীতিমালা থেকে উৎসভিত্তিক উত্তর",
  "রুটিন আইনি কাজ ও নথি বিশ্লেষণে সহায়তা",
  "Conversation history ও ব্যক্তিগত workspace",
];

export default function LandingPage() {
  return (
    <main className="landing-page">
      <header className="landing-nav">
        <Link href="/" className="landing-brand" aria-label="MyLegal AI home">
          <span className="landing-brand-icon"><Landmark size={25} strokeWidth={2.1} /></span>
          <span>
            <b>MyLegal AI</b>
            <small>Bangladesh Legal Assistant</small>
          </span>
        </Link>

        <nav className="landing-links" aria-label="Main navigation">
          <Link href="/">Home</Link>
          <a href="#features">Features</a>
          <a href="#how-it-works">How It Works</a>
          <a href="#about">About</a>
        </nav>

        <Link className="landing-nav-cta" href="/signin">Login <ArrowRight size={16} /></Link>
      </header>

      <section className="landing-hero">
        <div className="landing-copy">
          <span className="landing-kicker"><Sparkles size={15} /> AI Assistant for Bangladesh Legal Services</span>
          <h1>বাংলাদেশের আইন বুঝুন। <span>পরবর্তী পদক্ষেপ জানুন।</span></h1>
          <p>
            আইনি প্রশ্ন, ঘটনা বা নথি নিজের ভাষায় তুলে ধরুন। MyLegal AI আপনাকে
            প্রাসঙ্গিক আইন খুঁজতে, নথির তথ্য বুঝতে এবং সম্ভাব্য পরবর্তী পদক্ষেপ
            সাজাতে সহায়তা করবে।
          </p>

          <ul className="landing-benefits">
            {benefits.map((benefit) => (
              <li key={benefit}><Check size={19} />{benefit}</li>
            ))}
          </ul>

          <div className="landing-actions">
            <Link href="/signup" className="landing-primary">Get Started <ArrowRight size={18} /></Link>
            <a href="#features" className="landing-secondary">Learn More</a>
          </div>
          <div className="landing-trust"><ShieldCheck size={16} /> ব্যক্তিগত workspace · নিরাপদ sign-in · উৎসভিত্তিক সহায়তা</div>
        </div>

        <div className="landing-hero-art" aria-label="Bangladesh public institution illustration">
          <div className="landing-preview-card">
            <div className="landing-preview-heading"><span><MessageSquareText size={16} /></span><b>MyLegal AI Assistant</b><i>Online</i></div>
            <div className="landing-preview-user">একটি আইনি বিষয়ে জানতে চাই। কীভাবে শুরু করব?</div>
            <div className="landing-preview-ai"><span><Sparkles size={14} /> AI Assistant</span><p>ঘটনার বিবরণ লিখুন। প্রাসঙ্গিক আইন ও প্রয়োজনীয় তথ্য ধাপে ধাপে যাচাই করতে সাহায্য করব।</p></div>
          </div>
        </div>
      </section>

      <section className="landing-features" id="features">
        <article>
          <span><BookOpen size={21} /></span>
          <h3>আইনভিত্তিক অনুসন্ধান</h3>
          <p>প্রাসঙ্গিক আইন, ধারা ও নীতিমালার তথ্য খুঁজে বুঝতে সহায়তা।</p>
        </article>
        <article>
          <span><FileSearch size={21} /></span>
          <h3>নথি বিশ্লেষণ</h3>
          <p>PDF ও DOCX নথির তথ্য, গুরুত্বপূর্ণ অংশ এবং সম্ভাব্য ঝুঁকি পর্যালোচনা।</p>
        </article>
        <article>
          <span><ShieldCheck size={21} /></span>
          <h3>ব্যক্তিগত workspace</h3>
          <p>নিজস্ব conversation history ও সংযুক্ত নথি এক জায়গায় সংরক্ষণ।</p>
        </article>
      </section>

      <section className="landing-how" id="how-it-works">
        <div className="landing-section-heading">
          <span>HOW IT WORKS</span>
          <h2>সহজ তিনটি ধাপে শুরু করুন</h2>
        </div>
        <div className="landing-steps">
          <article><b>01</b><h3>অ্যাকাউন্টে প্রবেশ করুন</h3><p>আপনার account তৈরি করুন অথবা আগে থেকে থাকা account দিয়ে sign in করুন।</p></article>
          <article><b>02</b><h3>প্রশ্ন বা নথি যুক্ত করুন</h3><p>নিজের ভাষায় প্রশ্ন লিখুন, প্রয়োজন হলে PDF বা DOCX যুক্ত করুন।</p></article>
          <article><b>03</b><h3>উত্তর ও বিশ্লেষণ দেখুন</h3><p>AI-এর প্রাথমিক তথ্য, বিশ্লেষণ এবং উৎস যাচাইয়ের প্রয়োজনীয়তা বুঝে নিন।</p></article>
        </div>
      </section>

      <section className="landing-about" id="about">
        <div><span>ABOUT MYLEGAL AI</span><h2>আইনি তথ্য বুঝতে সহায়ক একটি ডিজিটাল workspace</h2></div>
        <p>MyLegal AI প্রাথমিক আইনি তথ্য ও document assistance দেয়। এর উত্তর আইনজীবীর পরামর্শ, সরকারি রেকর্ড বা সর্বশেষ আইন যাচাইয়ের বিকল্প নয়। গুরুত্বপূর্ণ সিদ্ধান্তের আগে মূল আইন ও যোগ্য আইনজীবীর পরামর্শ যাচাই করুন।</p>
      </section>
      <footer className="landing-footer">© {new Date().getFullYear()} MyLegal AI · Bangladesh Legal Assistant</footer>
    </main>
  );
}
