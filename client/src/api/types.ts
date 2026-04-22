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

export interface UserInfo {
  id: number;
  username: string;
  nickname: string | null;
  avatar: string | null;
  gender: string | null;
  bio: string | null;
  phone: string | null;
}

export interface AuthSession {
  token: string;
  userInfo: UserInfo;
}

export interface UpdateUserPayload {
  nickname?: string;
  avatar?: string;
  gender?: string;
  bio?: string;
  phone?: string;
}

export interface ChangePasswordPayload {
  oldPassword: string;
  newPassword: string;
}

export interface FavoriteStatus {
  isFavorite: boolean;
}

export interface FavoriteItem extends NewsListItem {
  favoriteId: number;
  favoriteTime: string | null;
}

export interface FavoriteListResult {
  list: FavoriteItem[];
  total: number;
  hasMore: boolean;
}

export interface HistoryItem extends NewsListItem {
  historyId: number;
  viewTime: string | null;
}

export interface HistoryListResult {
  list: HistoryItem[];
  total: number;
  hasMore: boolean;
}
