export interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T;
}

export interface NewsCategory {
  id: number;
  name: string;
}

export interface NewsListItem {
  id: number;
  title: string;
  description: string | null;
  image: string | null;
  author: string | null;
  categoryId: number;
  views: number;
  publishTime: string | null;
}

export interface NewsListResult {
  list: NewsListItem[];
  total: number;
  hasMore: boolean;
}

export interface NewsDetail extends NewsListItem {
  content: string;
  relatedNews: NewsListItem[];
}

export interface ChatResult {
  answer: string;
  newsList: NewsListItem[];
  loopCount: number;
}
