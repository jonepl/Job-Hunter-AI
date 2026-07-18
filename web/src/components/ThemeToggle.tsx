import { useTheme } from "../lib/theme";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const next = theme === "light" ? "dark" : "light";
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${next} theme`}
      className="rounded-control border border-border-strong px-3 py-1.5 text-control text-text-2 transition-colors duration-fast hover:border-accent hover:text-accent"
    >
      {theme === "light" ? "Dark" : "Light"}
    </button>
  );
}
