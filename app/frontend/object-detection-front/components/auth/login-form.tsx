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
        <h1 className="text-2xl font-semibold tracking-tight">Iniciar sesión</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {mode === "password" ? "Accede con tu correo y contraseña." : "Accede con la API key del servicio."}
        </p>
      </div>

      {mode === "password" ? (
        <>
          <Field label="Correo" htmlFor="email">
            <Input id="email" type="email" autoComplete="username" required autoFocus value={email}
              onChange={(e) => setEmail(e.target.value)} placeholder="tu@tienda.com" />
          </Field>
          <Field label="Contraseña" htmlFor="password">
            <Input id="password" type="password" autoComplete="current-password" required value={password}
              onChange={(e) => setPassword(e.target.value)} />
          </Field>
        </>
      ) : (
        <Field label="API key" htmlFor="key" hint="Se envía en la cabecera X-API-Key y opera como super admin.">
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
        {mode === "password" ? "Usar una API key en su lugar" : "Usar correo y contraseña"}
      </button>
    </form>
  );
}
