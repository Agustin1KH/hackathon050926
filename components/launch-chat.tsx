"use client";

import { useEffect, useRef, useState } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { ArrowUp, Bot, RefreshCw, Sparkles, Square, User } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const SUGGESTIONS = [
  "Pitch me 5 hackathon ideas built on Next.js + AI SDK",
  "Suggest an MVP cut for a 24-hour build",
  "Sketch the architecture for a multiplayer voting app",
  "Write a streaming AI summarizer route handler",
];

function MessageBubble({
  role,
  text,
  isStreaming,
}: {
  role: "user" | "assistant" | "system";
  text: string;
  isStreaming?: boolean;
}) {
  const isUser = role === "user";
  return (
    <div
      className={cn(
        "flex w-full gap-3",
        isUser ? "flex-row-reverse" : "flex-row",
      )}
    >
      <div
        className={cn(
          "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ring-1",
          isUser
            ? "bg-primary text-primary-foreground ring-primary/20"
            : "bg-muted text-foreground ring-border",
        )}
        aria-hidden
      >
        {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
      </div>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words",
          isUser
            ? "bg-primary text-primary-foreground rounded-tr-sm"
            : "bg-muted/60 text-foreground rounded-tl-sm ring-1 ring-border",
        )}
      >
        {text || (isStreaming ? <PulsingDots /> : null)}
        {isStreaming && text ? (
          <span
            aria-hidden
            className="ml-0.5 inline-block h-3 w-1.5 translate-y-0.5 animate-pulse rounded-sm bg-current/70"
          />
        ) : null}
      </div>
    </div>
  );
}

function PulsingDots() {
  return (
    <span className="inline-flex items-center gap-1 text-muted-foreground">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
    </span>
  );
}

export function LaunchChat() {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const { messages, sendMessage, status, stop, error, setMessages, regenerate } =
    useChat({
      transport: new DefaultChatTransport({ api: "/api/chat" }),
    });

  const isBusy = status === "streaming" || status === "submitted";

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, status]);

  const submit = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isBusy) return;
    void sendMessage({ text: trimmed });
    setInput("");
  };

  return (
    <Card className="flex h-[560px] flex-col overflow-hidden">
      <CardHeader className="flex-row items-center justify-between gap-3 border-b pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary ring-1 ring-primary/20">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <CardTitle>Launchpad assistant</CardTitle>
            <CardDescription>
              Live AI chat — wired to the Vercel AI Gateway.
            </CardDescription>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="font-mono text-[10px]">
            {process.env.NEXT_PUBLIC_AI_MODEL ?? "openai/gpt-5.4-mini"}
          </Badge>
          {messages.length > 0 ? (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setMessages([])}
              title="Clear conversation"
              aria-label="Clear conversation"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          ) : null}
        </div>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col gap-3 overflow-hidden p-0">
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-4 [scrollbar-width:thin]"
        >
          <div className="flex flex-col gap-4 py-4">
            {messages.length === 0 ? (
              <EmptyState onPick={submit} />
            ) : (
              messages.map((m) => {
                const text = m.parts
                  .map((p) => (p.type === "text" ? p.text : ""))
                  .join("");
                return (
                  <MessageBubble
                    key={m.id}
                    role={m.role}
                    text={text}
                    isStreaming={
                      isBusy &&
                      m.role === "assistant" &&
                      m.id === messages[messages.length - 1]?.id
                    }
                  />
                );
              })
            )}

            {error ? (
              <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                <div className="font-medium">Chat error</div>
                <div className="mt-0.5 opacity-90">{error.message}</div>
                <Button
                  variant="ghost"
                  size="xs"
                  className="mt-2 h-6 text-destructive hover:bg-destructive/15 hover:text-destructive"
                  onClick={() => regenerate()}
                >
                  Retry
                </Button>
              </div>
            ) : null}
          </div>
        </div>

        <form
          className="border-t bg-background/60 p-3"
          onSubmit={(e) => {
            e.preventDefault();
            submit(input);
          }}
        >
          <div className="relative">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit(input);
                }
              }}
              placeholder="Ask for ideas, code, or a quick gut-check…"
              rows={2}
              className="min-h-[60px] resize-none pr-12"
              disabled={isBusy && status === "submitted"}
            />
            <div className="absolute right-2 bottom-2">
              {isBusy ? (
                <Button
                  type="button"
                  size="icon-sm"
                  variant="secondary"
                  onClick={() => stop()}
                  aria-label="Stop generating"
                >
                  <Square className="h-3.5 w-3.5" />
                </Button>
              ) : (
                <Button
                  type="submit"
                  size="icon-sm"
                  disabled={!input.trim()}
                  aria-label="Send message"
                >
                  <ArrowUp className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          </div>
          <p className="mt-2 px-0.5 text-[11px] text-muted-foreground">
            Shift + Enter for newline. Edit{" "}
            <code className="rounded bg-muted px-1 py-0.5 font-mono text-[10px]">
              app/api/chat/route.ts
            </code>{" "}
            to change the system prompt or model.
          </p>
        </form>
      </CardContent>
    </Card>
  );
}

function EmptyState({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="flex flex-col items-center gap-4 py-10 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary ring-1 ring-primary/20">
        <Sparkles className="h-5 w-5" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium">Talk to your launchpad assistant.</p>
        <p className="text-xs text-muted-foreground">
          Try one of these to kick things off.
        </p>
      </div>
      <div className="grid w-full gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onPick(s)}
            className="rounded-lg border border-border bg-card px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:border-foreground/20 hover:bg-muted hover:text-foreground"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
