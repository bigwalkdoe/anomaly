"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiJson } from "@/lib/api";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch("http://localhost:8000/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, name, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        setError(err.detail || `Registration failed: ${res.status}`);
        return;
      }
      router.push("/login");
    } catch (err) {
      setError("Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-md space-y-8 p-4">
        <div className="flex flex-col items-center">
          <ShieldCheck className="h-12 w-12 text-primary" />
          <h2 className="text-2xl font-bold">Create Account</h2>
          <p className="text-muted-foreground">Register for Anomaly</p>
        </div>

        {error && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-700 border border-red-100">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Full Name</label>
            <input
              type="text"
              required
              className="w-full rounded-md border border-border bg-input px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Email</label>
            <input
              type="email"
              required
              className="w-full rounded-md border border-border bg-input px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Password</label>
            <input
              type="password"
              required
              minLength={8}
              className="w-full rounded-md border border-border bg-input px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center rounded-md bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <p className="text-sm text-center text-muted-foreground">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-primary hover:text-primary/90">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
