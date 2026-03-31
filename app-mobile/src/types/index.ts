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

export type CasePatternCandidate = {
  name: string;
  score: number;
  reasons: string[];
};

export type CaseProfile = {
  isCase: boolean;
  fields?: Record<string, string>;
  sex?: string;
  age?: string;
  department?: string;
  mainComplaint?: string;
  symptoms: string[];
  dangerSignsPresent: string[];
  dangerSignsAbsent: string[];
  vitals?: Record<string, string>;
  painScore?: string;
  bpLevel?: string;
  tcmFindings: string[];
  patternCandidates: CasePatternCandidate[];
  suggestedTerms: string[];
  summary?: string;
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
  caseProfile?: CaseProfile;
};

export type RetrievalHit = {
  articleId: string;
  fileLabel: string;
  title: string;
  kind?: string;
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

export type AssistantReference = {
  fileLabel: string;
  title: string;
};

export type AssistantTurn = {
  time: string;
  question: string;
  tags: string[];
  focus: string;
  hitTitles: string[];
  answerSummary: string;
  answer: string;
  analysis?: {
    intent?: string;
    focus?: string;
    matchedTags?: string[];
  };
  references?: AssistantReference[];
};

export type AssistantSessionSummary = {
  sessionId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  recentFocus: string;
  turnCount: number;
  preview: string;
};

export type AssistantSessionDetail = {
  sessionId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  recentFocus: string;
  memoryTags: string[];
  recentHits: string[];
  turnCount: number;
  latestTurn?: AssistantTurn | null;
  turns: AssistantTurn[];
};

export type MemoryOverview = {
  sessionTitle?: string;
  recentFocus: string;
  memoryTags: string[];
  recentHits: string[];
  turnCount?: number;
  recentTurns: AssistantTurn[];
};

export type AssistantResult = {
  sessionId: string;
  analysis: QueryAnalysis;
  retrieval: RetrievalResult;
  answer: string;
  memory: MemoryOverview;
  session: AssistantSessionDetail;
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
