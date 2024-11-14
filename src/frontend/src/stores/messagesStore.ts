import { applyPatch } from "fast-json-patch";
import { create } from "zustand";
import { MessagesStoreType } from "../types/zustand/messages";

export const useMessagesStore = create<MessagesStoreType>((set, get) => ({
  messages: [],
  setMessages: (messages) => {
    set(() => ({ messages: messages }));
  },
  addMessage: (message) => {
    const existingMessage = get().messages.find((msg) => msg.id === message.id);
    if (existingMessage) {
      get().updateMessagePartial(message);
      return;
    }
    set(() => ({ messages: [...get().messages, message] }));
  },
  removeMessage: (message) => {
    set(() => ({
      messages: get().messages.filter((msg) => msg.id !== message.id),
    }));
  },
  updateMessage: (message) => {
    set(() => ({
      messages: get().messages.map((msg) =>
        msg.id === message.id ? message : msg,
      ),
    }));
  },
  updateMessagePartial: (message) => {
    set((state) => {
      const updatedMessages = [...state.messages];
      for (let i = state.messages.length - 1; i >= 0; i--) {
        if (state.messages[i].id === message.id) {
          updatedMessages[i] = { ...updatedMessages[i], ...message };
          break;
        }
      }
      return { messages: updatedMessages };
    });
  },
  updateMessageText: (id, chunk) => {
    set((state) => {
      const updatedMessages = [...state.messages];
      for (let i = state.messages.length - 1; i >= 0; i--) {
        if (state.messages[i].id === id) {
          updatedMessages[i] = {
            ...updatedMessages[i],
            text: updatedMessages[i].text + chunk,
          };
          break;
        }
      }
      return { messages: updatedMessages };
    });
  },
  applyMessagePatch: (messageId, patch) => {
    set((state) => {
      const updatedMessages = [...state.messages];
      const messageIndex = updatedMessages.findIndex(
        (msg) => msg.id === messageId,
      );

      if (messageIndex !== -1) {
        try {
          const patchResult = applyPatch(
            updatedMessages[messageIndex],
            patch,
            true,
            false,
          );

          updatedMessages[messageIndex] = patchResult.newDocument;
          return { messages: updatedMessages };
        } catch (error) {
          console.error("Error applying patch:", error);
          return state;
        }
      }
      return state;
    });
  },
  clearMessages: () => {
    set(() => ({ messages: [] }));
  },
  removeMessages: (ids) => {
    return new Promise((resolve, reject) => {
      try {
        set((state) => {
          const updatedMessages = state.messages.filter(
            (msg) => !ids.includes(msg.id),
          );
          get().setMessages(updatedMessages);
          resolve(updatedMessages);
          return { messages: updatedMessages };
        });
      } catch (error) {
        reject(error);
      }
    });
  },
  deleteSession: (id) => {
    set((state) => {
      const updatedMessages = state.messages.filter(
        (msg) => msg.session_id !== id,
      );
      return { messages: updatedMessages };
    });
  },
}));
