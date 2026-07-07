import { create } from "zustand";

interface UiState {
  paletteCollapsed: boolean;
  theme: "dark" | "light";
  togglePalette: () => void;
  toggleTheme: () => void;
}

export const useUiStore = create<UiState>((set) => ({
  paletteCollapsed: false,
  theme: "dark",
  togglePalette: () => set((s) => ({ paletteCollapsed: !s.paletteCollapsed })),
  toggleTheme: () => set((s) => ({ theme: s.theme === "dark" ? "light" : "dark" })),
}));
