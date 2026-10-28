"use client";

import { Loader2 } from "lucide-react";
import { useState } from "react";
import { Field } from "@/components/common/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useLogin } from "@/hooks/use-session";

type Mode = "password" | "key";

export function LoginForm({ ready }: { ready: boolean }) {
  const login = useLogin();
  const [mode, setMode] = useState<Mode>("password");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [key, setKey] = useState("");

  function submit() {
    login.mutate(mode === "password" ? { mode, email: email.trim(), password } : { mode, key: key.trim() });
  }

  return (
    <form
      className="mx-auto grid w-full max-w-sm gap-5"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {mode === "password" ? "Sign in with your email and password." : "Sign in with the service API key."}
        </p>
      </div>

      {mode === "password" ? (
        <>
          <Field label="Email" htmlFor="email">
            <Input id="email" type="email" autoComplete="username" required autoFocus value={email}
              onChange={(e) => setEmail(e.target.value)} placeholder="tu@store.com" />
          </Field>
          <Field label="Password" htmlFor="password">
            <Input id="password" type="password" autoComplete="current-password" required value={password}
              onChange={(e) => setPassword(e.target.value)} />
          </Field>
        </>
      ) : (
        <Field label="API key" htmlFor="key" hint="Sent in the X-API-Key header; grants super admin access.">
          <Input id="key" type="password" required autoFocus value={key} onChange={(e) => setKey(e.target.value)} className="font-mono" />
        </Field>
      )}

      <Button type="submit" size="lg" disabled={login.isPending || !ready} className="h-9">
        {login.isPending && <Loader2 className="animate-spin" />}
        Entrar
      </Button>

      <button
        type="button"
        className="text-left text-xs text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
        onClick={() => setMode(mode === "password" ? "key" : "password")}
      >
        {mode === "password" ? "Use an API key instead" : "Use email and password"}
      </button>
    </form>
  );
}
