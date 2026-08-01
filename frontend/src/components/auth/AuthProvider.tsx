"use client";

import { useEffect } from "react";
import { onAuthStateChanged } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { useAppStore } from "@/lib/store";
import { useRouter, usePathname } from "next/navigation";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { setUser, setAuthLoading } = useAppStore();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (user) {
        setUser({
          uid: user.uid,
          email: user.email,
        });
        setAuthLoading(false);
        if (pathname === '/login' || pathname === '/signup') {
          router.push('/dashboard');
        }
      } else {
        setUser(null);
        setAuthLoading(false);
        if (pathname !== '/login' && pathname !== '/signup' && pathname !== '/') {
          router.push('/login');
        }
      }
    });

    return () => unsubscribe();
  }, [setUser, setAuthLoading, router, pathname]);

  return <>{children}</>;
}
