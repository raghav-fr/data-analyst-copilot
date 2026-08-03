/**
 * Global store using Zustand for dataset and conversation state
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface ActiveDataset {
  id: string;
  filename: string;
  rows: number;
  columns: number;
  column_names: string[];
}

export interface ConversationItem {
  id: string;
  title: string;
  dataset_id: string;
  created_at: string;
}

interface AppState {
  // Auth
  user: any | null;
  setUser: (user: any | null) => void;
  authLoading: boolean;
  setAuthLoading: (loading: boolean) => void;

  // Dataset
  activeDataset: ActiveDataset | null;
  setActiveDataset: (dataset: ActiveDataset | null) => void;

  // Conversation
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
  conversations: ConversationItem[];
  addConversation: (conv: ConversationItem) => void;

  // UI
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;

  // Settings
  settingsOpen: boolean;
  setSettingsOpen: (open: boolean) => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      user: null,
      setUser: (user) => set({ user }),
      authLoading: true,
      setAuthLoading: (loading) => set({ authLoading: loading }),

      activeDataset: null,
      setActiveDataset: (dataset) => set({ activeDataset: dataset }),

      activeConversationId: null,
      setActiveConversationId: (id) => set({ activeConversationId: id }),
      conversations: [],
      addConversation: (conv) =>
        set((state) => ({
          conversations: [conv, ...state.conversations.filter(c => c.id !== conv.id)].slice(0, 20),
        })),

      sidebarOpen: true,
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      activeTab: 'chat',
      setActiveTab: (tab) => set({ activeTab: tab }),

      settingsOpen: false,
      setSettingsOpen: (open) => set({ settingsOpen: open }),
      selectedModel: "nemotron",
      setSelectedModel: (model) => set({ selectedModel: model }),
    }),
    {
      name: 'data-copilot-store',
      partialize: (state) => ({
        sidebarOpen: state.sidebarOpen,
        activeDataset: state.activeDataset,
        activeConversationId: state.activeConversationId,
        activeTab: state.activeTab,
        selectedModel: state.selectedModel,
      }),
    }
  )
);
