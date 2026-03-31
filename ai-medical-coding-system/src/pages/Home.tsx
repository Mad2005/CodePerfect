import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import { 
  Activity, 
  FileText, 
  ShieldCheck, 
  Zap, 
  Clock, 
  ChevronRight, 
  Stethoscope, 
  Database, 
  Lock,
  ArrowUpRight,
  Sparkles
} from 'lucide-react';

export default function Home() {
  return (
    <div className="min-h-[calc(100vh-64px)] flex flex-col">
      {/* Hero Section */}
      <section className="bg-white border-b border-slate-100 py-24 px-4 relative overflow-hidden">
        {/* Background Decorative Elements */}
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none opacity-20">
          <div className="absolute -top-24 -left-24 w-96 h-96 bg-hospital-blue-100 rounded-full blur-3xl" />
          <div className="absolute top-1/2 -right-24 w-64 h-64 bg-hospital-blue-50 rounded-full blur-3xl" />
        </div>

        <div className="max-w-5xl mx-auto text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold bg-hospital-blue-50 text-hospital-blue-700 mb-8 border border-hospital-blue-100">
              <Sparkles className="w-3.5 h-3.5" />
              AI-POWERED CLINICAL INTELLIGENCE
            </div>
            <h1 className="text-6xl md:text-7xl font-black text-slate-900 tracking-tight mb-8 leading-[1.1]">
              Next-Gen Medical <br />
              <span className="text-hospital-blue-600">Coding Intelligence</span>
            </h1>
            <p className="text-xl text-slate-500 max-w-2xl mx-auto mb-12 leading-relaxed font-medium">
              Transform clinical documentation into accurate medical codes with our advanced 
              language understanding system. Reduce denials and optimize revenue cycles.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="flex flex-col sm:flex-row gap-6 justify-center items-center"
          >
            <Link
              to="/auto-coding"
              className="group relative inline-flex items-center justify-center px-10 py-5 rounded-2xl bg-hospital-blue-600 text-white font-bold text-lg hover:bg-hospital-blue-700 transition-all shadow-2xl shadow-hospital-blue-200 active:scale-95"
            >
              <Activity className="w-5 h-5 mr-3 group-hover:animate-pulse" />
              Auto Coding Mode
              <ArrowUpRight className="w-5 h-5 ml-2 opacity-0 group-hover:opacity-100 -translate-y-1 translate-x-1 transition-all" />
            </Link>
            <Link
              to="/assisted-coding"
              className="inline-flex items-center justify-center px-10 py-5 rounded-2xl bg-white border-2 border-slate-200 text-slate-700 font-bold text-lg hover:border-hospital-blue-500 hover:text-hospital-blue-600 transition-all active:scale-95"
            >
              <FileText className="w-5 h-5 mr-3" />
              Assisted Coding
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Stats / Trust Section */}
      <section className="py-12 bg-white border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex flex-wrap justify-center gap-12 md:gap-24 opacity-40 grayscale hover:grayscale-0 transition-all duration-500">
            <div className="flex items-center gap-2 font-bold text-slate-900">
              <ShieldCheck className="w-6 h-6" /> HIPAA COMPLIANT
            </div>
            <div className="flex items-center gap-2 font-bold text-slate-900">
              <Lock className="w-6 h-6" /> SOC2 TYPE II
            </div>
            <div className="flex items-center gap-2 font-bold text-slate-900">
              <Database className="w-6 h-6" /> 99.9% UPTIME
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 px-4 bg-slate-50 flex-grow">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">Enterprise-Grade Features</h2>
            <div className="w-20 h-1.5 bg-hospital-blue-600 mx-auto rounded-full" />
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard
              icon={Zap}
              title="Instant Extraction"
              description="Our engine identifies clinical entities, diagnoses, and procedures directly from unstructured text in milliseconds."
            />
            <FeatureCard
              icon={Stethoscope}
              title="Clinical Context"
              description="Deep understanding of medical terminology and clinical relationships ensures accurate code assignment."
            />
            <FeatureCard
              icon={ShieldCheck}
              title="Compliance Guard"
              description="Built-in validation against NCCI, MUE, and local coverage determinations to prevent billing errors."
            />
            <FeatureCard
              icon={Clock}
              title="Audit Trail"
              description="Every report is versioned and stored with a full audit trail for internal review and external audits."
            />
            <FeatureCard
              icon={Database}
              title="Knowledge Base"
              description="Continuously updated with the latest coding guidelines and regulatory changes automatically."
            />
            <FeatureCard
              icon={Lock}
              title="Secure Handling"
              description="Enterprise-grade security ensures patient data is handled with the highest level of privacy and encryption."
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <Activity className="text-hospital-blue-600 w-6 h-6" />
            <span className="font-bold text-slate-900">AI Medical Coding</span>
          </div>
          <div className="text-slate-400 text-sm">
            &copy; {new Date().getFullYear()} AI Medical Coding System. Professional Edition.
          </div>
          <div className="flex gap-6 text-sm font-medium text-slate-500">
            <a href="#" className="hover:text-hospital-blue-600 transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-hospital-blue-600 transition-colors">Terms of Service</a>
            <a href="#" className="hover:text-hospital-blue-600 transition-colors">Support</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon: Icon, title, description }: { icon: any, title: string, description: string }) {
  return (
    <motion.div 
      whileHover={{ y: -5 }}
      className="bg-white p-10 rounded-3xl border border-slate-100 shadow-sm hover:shadow-xl hover:border-hospital-blue-100 transition-all group"
    >
      <div className="w-14 h-14 bg-hospital-blue-50 rounded-2xl flex items-center justify-center mb-8 group-hover:bg-hospital-blue-600 transition-colors">
        <Icon className="text-hospital-blue-600 w-7 h-7 group-hover:text-white transition-colors" />
      </div>
      <h3 className="text-2xl font-bold text-slate-900 mb-4">{title}</h3>
      <p className="text-slate-500 leading-relaxed font-medium">{description}</p>
    </motion.div>
  );
}
