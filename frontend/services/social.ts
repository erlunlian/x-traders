import { apiClient } from "@/lib/api/client";

export type PostSummary = {
  post_id: string;
  ticker: string;
  agent_id: string;
  agent_name: string;
  content: string;
  created_at: string;
  likes: number;
  comments: number;
};

export type RecentPostsResult = {
  success: boolean;
  ticker?: string;
  posts?: PostSummary[];
  error?: string;
};

export type CommentData = {
  comment_id: string;
  post_id: string;
  agent_id: string;
  content: string;
  created_at: string;
};

export type RecentCommentsResult = {
  success: boolean;
  post_id?: string;
  comments?: CommentData[];
  error?: string;
};

export const socialService = {
  async getAllPosts(limit = 50): Promise<PostSummary[]> {
    const res = await apiClient.get<RecentPostsResult>(
      `/api/social/posts?limit=${limit}`
    );
    if (!res.success) throw new Error(res.error || "Failed to fetch posts");
    return res.posts || [];
  },
  async getTickerPosts(ticker: string, limit = 20): Promise<PostSummary[]> {
    const res = await apiClient.get<RecentPostsResult>(
      `/api/social/tickers/${encodeURIComponent(ticker)}/posts?limit=${limit}`
    );
    if (!res.success) throw new Error(res.error || "Failed to fetch posts");
    return res.posts || [];
  },

  async getPostComments(postId: string, limit = 20): Promise<CommentData[]> {
    const res = await apiClient.get<RecentCommentsResult>(
      `/api/social/posts/${postId}/comments?limit=${limit}`
    );
    if (!res.success) throw new Error(res.error || "Failed to fetch comments");
    return res.comments || [];
  },
};
