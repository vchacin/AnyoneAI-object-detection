"use client";

import { BrandName } from "@/components/app/brand";
import { LoginForm } from "@/components/auth/login-form";
import { ShelfArt } from "@/components/auth/shelf-art";
import { useRedirectIfAuthed } from "@/hooks/use-session";

export default function LoginPage() {
  const ready = useRedirectIfAuthed();
  return (
    <main className="flex min-h-svh">
      <ShelfArt />
      <div className="flex w-full flex-col justify-between px-6 py-8 sm:px-12 lg:w-[480px] lg:shrink-0">
        <BrandName className="text-lg" />
        <LoginForm ready={ready} />
        <p className="text-xs text-muted-foreground">AnyoneAI · Out-of-stock product detection</p>
      </div>
    </main>
  );
}
