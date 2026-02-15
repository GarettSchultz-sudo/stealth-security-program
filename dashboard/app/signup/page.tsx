'use client'

import Link from 'next/link'
import { SignUpForm } from '@/components/auth/auth-forms'

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">
            Agent<span className="text-cyan-400">CostControl</span>
          </h1>
          <p className="text-slate-400 mt-2">Create your account</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <SignUpForm />

          <div className="mt-6 pt-6 border-t border-slate-800 text-center">
            <p className="text-slate-400 text-sm">
              Already have an account?{' '}
              <Link href="/login" className="text-cyan-400 hover:text-cyan-300 font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
