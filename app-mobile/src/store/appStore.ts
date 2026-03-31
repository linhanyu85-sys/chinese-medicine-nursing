import { create } from "zustand";

import { runtimeConfig } from "../generated/runtimeConfig";
import type { HealthStatus } from "../types";

type AppState = {
  backendUrl: string;
  currentSessionId: string;
  pendingQuestion: string;
  health: HealthStatus | null;
  setBackendUrl: (value: string) => void;
  setCurrentSessionId: (value: string) => void;
  setPendingQuestion: (value: string) => void;
  setHealth: (value: HealthStatus | null) => void;
};

export const useAppStore = create<AppState>((set) => ({
  backendUrl: runtimeConfig.backendUrl,
  currentSessionId: "",
  pendingQuestion: "",
  health: null,
  setBackendUrl: (backendUrl) => set({ backendUrl: backendUrl.trim(), currentSessionId: "" }),
  setCurrentSessionId: (currentSessionId) => set({ currentSessionId }),
  setPendingQuestion: (pendingQuestion) => set({ pendingQuestion }),
  setHealth: (health) => set({ health }),
}));
