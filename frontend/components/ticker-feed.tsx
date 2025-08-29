"use client";

import { CommentData, PostSummary, socialService } from "@/services/social";
import { useEffect, useState } from "react";

export function TickerFeed({ ticker }: { ticker: string }) {
  const [posts, setPosts] = useState<PostSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedPostId, setExpandedPostId] = useState<string | null>(null);
  const [comments, setComments] = useState<Record<string, CommentData[]>>({});
  const [commentsLoading, setCommentsLoading] = useState<
    Record<string, boolean>
  >({});

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await socialService.getTickerPosts(ticker, 20);
        if (!cancelled) setPosts(data);
      } catch (e: any) {
        if (!cancelled) setError(e?.message || "Failed to load feed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  async function toggleComments(postId: string) {
    if (expandedPostId === postId) {
      setExpandedPostId(null);
      return;
    }
    setExpandedPostId(postId);
    if (!comments[postId]) {
      setCommentsLoading((s) => ({ ...s, [postId]: true }));
      try {
        const data = await socialService.getPostComments(postId, 20);
        setComments((c) => ({ ...c, [postId]: data }));
      } catch (e) {
        // swallow error per-post
      } finally {
        setCommentsLoading((s) => ({ ...s, [postId]: false }));
      }
    }
  }

  if (loading)
    return <div className="text-sm text-muted-foreground">Loading feed…</div>;
  if (error) return <div className="text-sm text-red-500">{error}</div>;

  if (!posts.length) {
    return (
      <div className="text-sm text-muted-foreground">
        No posts yet for {ticker}.
      </div>
    );
  }

  return (
    <div className="space-y-4 pr-2">
      {posts.map((p) => {
        const isOpen = expandedPostId === p.post_id;
        const postComments = comments[p.post_id] || [];
        return (
          <div key={p.post_id} className="border rounded-md p-3 bg-background">
            <div className="flex items-start justify-between gap-2">
              <div className="whitespace-pre-wrap break-words text-sm">
                {p.content}
              </div>
              <div className="text-xs text-muted-foreground flex-shrink-0">
                <span className="mr-2">👍 {p.likes}</span>
                <button
                  className="underline"
                  onClick={() => toggleComments(p.post_id)}
                >
                  💬 {p.comments}
                </button>
              </div>
            </div>
            {isOpen && (
              <div className="mt-3 border-t pt-3 space-y-2">
                {commentsLoading[p.post_id] && (
                  <div className="text-xs text-muted-foreground">
                    Loading comments…
                  </div>
                )}
                {!commentsLoading[p.post_id] && postComments.length === 0 && (
                  <div className="text-xs text-muted-foreground">
                    No comments.
                  </div>
                )}
                {postComments.map((c) => (
                  <div
                    key={c.comment_id}
                    className="text-sm whitespace-pre-wrap break-words"
                  >
                    {c.content}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
