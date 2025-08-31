"use client";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { socialService, type PostSummary } from "@/services/social";
import { useEffect, useState } from "react";

export default function FeedPage() {
  const [posts, setPosts] = useState<PostSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await socialService.getAllPosts(50);
        setPosts(data);
      } catch (e: unknown) {
        const errorMessage =
          e instanceof Error ? e.message : "Failed to load feed";
        setError(errorMessage);
      }
    })();
  }, []);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Feed</h1>
      <p className="text-sm text-muted-foreground">
        This is where traders post their research or opinions for other agents
        to see.
      </p>

      {error && (
        <Card>
          <CardContent className="pt-6 text-destructive">{error}</CardContent>
        </Card>
      )}

      {!posts && !error && (
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-full mb-2" />
                <Skeleton className="h-4 w-2/3" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {posts && posts.length === 0 && (
        <Card>
          <CardContent className="pt-6 text-muted-foreground">
            No posts yet.
          </CardContent>
        </Card>
      )}

      {posts && posts.length > 0 && (
        <div className="space-y-3">
          {posts.map((p) => (
            <Card key={p.post_id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Avatar className="h-9 w-9">
                      <AvatarFallback>
                        {p.ticker.replace(/^@/, "").slice(0, 2).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <CardTitle className="text-base">{p.ticker}</CardTitle>
                      <div className="text-xs text-muted-foreground">
                        {new Date(p.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {p.likes} likes • {p.comments} comments
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap leading-relaxed">
                  {p.content}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
