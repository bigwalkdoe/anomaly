"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme, type Theme } from "@/components/ThemeProvider";

const THEME_ORDER: Theme[] = ["light", "dark", "system"];

const THEME_META: Record<Theme, { label: string; icon: typeof Sun }> = {
  light: { label: "Light theme", icon: Sun },
  dark: { label: "Dark theme", icon: Moon },
  system: { label: "System theme", icon: Monitor },
};

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  const cycleTheme = () => {
    const currentIndex = THEME_ORDER.indexOf(theme);
    const nextTheme = THEME_ORDER[(currentIndex + 1) % THEME_ORDER.length];
    setTheme(nextTheme);
  };

  const { label, icon: Icon } = THEME_META[theme];

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      onClick={cycleTheme}
      aria-label={`${label}. Activate to switch theme.`}
      title={`${label} (click to switch)`}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
    </Button>
  );
}
