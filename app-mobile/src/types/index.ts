export type ArticleCard = {
  articleId: string;
  fileLabel: string;
  title: string;
  shortTitle?: string;
  partTitle?: string;
  chapterTitle?: string;
  tags: string[];
  summary: string;
  updatedAt?: string;
  score?: number;
};

export type ArticleSection = {
  title: string;
  level: number;
  content: string;
};

export type ArticleDetail = {
  articleId: string;
  fileLabel: string;
  title: string;
  shortTitle?: string;
  partTitle?: string;
  chapterTitle?: string;
  tags: string[];
  summary: string;
  body: string;
  sections: ArticleSection[];
  updatedAt?: string;
  relativePath?: string;
};

export type QueryAnalysis = {
  question: string;
  normalized: string;
  intent: string;
  focus: string;
  matchedTags: string[];
  keywords: string[];
  fragments: string[];
  memoryTags: string[];
  useMemory: boolean;
};

export type RetrievalHit = {
  articleId: string;
  fileLabel: string;
  title: string;
  score: number;
  basis: string[];
  snippet: string;
};

export type RetrievalResult = {
  matched: boolean;
  hits: RetrievalHit[];
  chapterContext?: {
    title?: string;
    summary?: string;
  };
};

export type MemoryOverview = {
  recentFocus: string;
  memoryTags: string[];
  recentHits: string[];
  recentTurns: Array<{
    time: string;
    question: string;
    tags: string[];
    focus: string;
    hitTitles: string[];
    answerSummary: string;
  }>;
};

export type AssistantResult = {
  sessionId: string;
  analysis: QueryAnalysis;
  retrieval: RetrievalResult;
  answer: string;
  memory: MemoryOverview;
};

export type HomePayload = {
  appName: string;
  generatedAt: string;
  stats: {
    articleCount?: number;
    partCount?: number;
    lastExport?: string;
  };
  quickEntries: ArticleCard[];
  sampleQueries: string[];
  dailyTip: {
    title: string;
    content: string;
  };
};

export type HealthStatus = {
  status: string;
  articleCount: number;
};

export type ManagementOverview = {
  articleCount: number;
  partCount: number;
  lastExport: string;
  sessionFile: string;
  knowledgeSource: string;
};

export type TreeNode = {
  id: string;
  fileLabel: string;
  type: string;
  title: string;
  shortTitle?: string;
  articleId?: string;
  children?: TreeNode[];
};
