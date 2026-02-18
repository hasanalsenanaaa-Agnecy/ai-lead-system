// Knowledge Base Page - Manage AI knowledge bases, documents, and FAQs

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { clsx } from 'clsx';
import toast from 'react-hot-toast';
import {
  BookOpenIcon,
  PlusIcon,
  DocumentTextIcon,
  QuestionMarkCircleIcon,
  MagnifyingGlassIcon,
  TrashIcon,
  ArrowPathIcon,
  DocumentArrowUpIcon,
  XMarkIcon,
  SparklesIcon,
  FolderIcon,
} from '@heroicons/react/24/outline';
import { useClientStore } from '../store';
import { knowledgeApi } from '../api';
import type { KnowledgeBase } from '../types';

function KnowledgeSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="space-y-3">
            <div className="h-5 w-40 bg-gray-200 rounded" />
            <div className="h-4 w-24 bg-gray-200 rounded" />
            <div className="h-3 w-32 bg-gray-200 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function KnowledgePage() {
  const { currentClient } = useClientStore();
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showIngestModal, setShowIngestModal] = useState<string | null>(null);
  const [showFAQModal, setShowFAQModal] = useState<string | null>(null);
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Array<{ id: string; content: string; source: string; similarity: number; knowledge_base: string }>>([]);
  const [searching, setSearching] = useState(false);

  // Create form state
  const [createName, setCreateName] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createCategory, setCreateCategory] = useState('general');

  // Ingest form state
  const [ingestContent, setIngestContent] = useState('');
  const [ingestSource, setIngestSource] = useState('');

  // FAQ form state
  const [faqQuestion, setFaqQuestion] = useState('');
  const [faqAnswer, setFaqAnswer] = useState('');
  const [faqCategory, setFaqCategory] = useState('');

  const { data: knowledgeBases, isLoading } = useQuery({
    queryKey: ['knowledge-bases', currentClient?.id],
    queryFn: () => knowledgeApi.listBases(currentClient!.id),
    enabled: !!currentClient?.id,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.createBase(currentClient!.id, {
        name: createName,
        description: createDescription || undefined,
        category: createCategory,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      toast.success('Knowledge base created');
      setShowCreateModal(false);
      setCreateName('');
      setCreateDescription('');
      setCreateCategory('general');
    },
    onError: () => toast.error('Failed to create knowledge base'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => knowledgeApi.deleteBase(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      toast.success('Knowledge base deleted');
    },
    onError: () => toast.error('Failed to delete knowledge base'),
  });

  const ingestMutation = useMutation({
    mutationFn: ({ kbId, content, source }: { kbId: string; content: string; source: string }) =>
      knowledgeApi.ingestDocument(kbId, { content, source }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      toast.success(`Document ingested: ${data.chunks_created} chunks created`);
      setShowIngestModal(null);
      setIngestContent('');
      setIngestSource('');
    },
    onError: () => toast.error('Failed to ingest document'),
  });

  const faqMutation = useMutation({
    mutationFn: ({ kbId, question, answer, category }: { kbId: string; question: string; answer: string; category?: string }) =>
      knowledgeApi.ingestFAQ(kbId, { question, answer, category }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      toast.success(`FAQ added: ${data.chunks_created} chunks created`);
      setShowFAQModal(null);
      setFaqQuestion('');
      setFaqAnswer('');
      setFaqCategory('');
    },
    onError: () => toast.error('Failed to add FAQ'),
  });

  const clearMutation = useMutation({
    mutationFn: (id: string) => knowledgeApi.clear(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
      toast.success(`Cleared: ${data.chunks_deleted} chunks removed`);
    },
    onError: () => toast.error('Failed to clear knowledge base'),
  });

  const handleSearch = async () => {
    if (!searchQuery.trim() || !currentClient?.id) return;
    setSearching(true);
    try {
      const results = await knowledgeApi.search(currentClient.id, { query: searchQuery });
      setSearchResults(results);
    } catch {
      toast.error('Search failed');
    } finally {
      setSearching(false);
    }
  };

  if (!currentClient) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Please select a client to manage knowledge bases.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Knowledge Base</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage documents and FAQs that power your AI agent's responses
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowSearchModal(true)}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
          >
            <MagnifyingGlassIcon className="h-4 w-4 mr-2" />
            Test Search
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            New Knowledge Base
          </button>
        </div>
      </div>

      {/* Knowledge Bases Grid */}
      {isLoading ? (
        <KnowledgeSkeleton />
      ) : !knowledgeBases || knowledgeBases.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <BookOpenIcon className="mx-auto h-12 w-12 text-gray-300" />
          <p className="mt-3 text-sm font-medium text-gray-900">No knowledge bases yet</p>
          <p className="mt-1 text-sm text-gray-500">Create a knowledge base to get started with AI-powered responses.</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="mt-4 inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            Create Knowledge Base
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {knowledgeBases.map((kb: KnowledgeBase) => (
            <div key={kb.id} className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 bg-blue-50 rounded-lg">
                    <FolderIcon className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900">{kb.name}</h3>
                    <span className="text-xs text-gray-500 capitalize">{kb.category}</span>
                  </div>
                </div>
                <span className={clsx(
                  'inline-flex px-2 py-0.5 rounded-full text-xs font-medium',
                  kb.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                )}>
                  {kb.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>

              {kb.description && (
                <p className="text-sm text-gray-600 mb-3 line-clamp-2">{kb.description}</p>
              )}

              <div className="flex items-center gap-4 text-xs text-gray-500 mb-4">
                <span className="flex items-center gap-1">
                  <DocumentTextIcon className="h-3.5 w-3.5" />
                  {kb.chunk_count} chunks
                </span>
                <span className="flex items-center gap-1">
                  <DocumentArrowUpIcon className="h-3.5 w-3.5" />
                  {kb.document_count} docs
                </span>
                {kb.last_synced_at && (
                  <span>Synced {format(new Date(kb.last_synced_at), 'MMM d')}</span>
                )}
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => setShowIngestModal(kb.id)}
                  className="flex-1 inline-flex items-center justify-center px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors"
                >
                  <DocumentTextIcon className="h-3.5 w-3.5 mr-1" />
                  Add Doc
                </button>
                <button
                  onClick={() => setShowFAQModal(kb.id)}
                  className="flex-1 inline-flex items-center justify-center px-3 py-1.5 text-xs font-medium text-purple-600 border border-purple-200 rounded-lg hover:bg-purple-50 transition-colors"
                >
                  <QuestionMarkCircleIcon className="h-3.5 w-3.5 mr-1" />
                  Add FAQ
                </button>
                <button
                  onClick={() => {
                    if (confirm('Clear all chunks from this knowledge base?')) {
                      clearMutation.mutate(kb.id);
                    }
                  }}
                  className="px-2 py-1.5 text-xs text-gray-400 border border-gray-200 rounded-lg hover:text-red-600 hover:border-red-200 transition-colors"
                >
                  <ArrowPathIcon className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => {
                    if (confirm('Delete this knowledge base permanently?')) {
                      deleteMutation.mutate(kb.id);
                    }
                  }}
                  className="px-2 py-1.5 text-xs text-gray-400 border border-gray-200 rounded-lg hover:text-red-600 hover:border-red-200 transition-colors"
                >
                  <TrashIcon className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-black/50" onClick={() => setShowCreateModal(false)} />
            <div className="relative bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Create Knowledge Base</h3>
                <button onClick={() => setShowCreateModal(false)} className="text-gray-400 hover:text-gray-600">
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                  <input
                    type="text"
                    value={createName}
                    onChange={(e) => setCreateName(e.target.value)}
                    placeholder="e.g., Product Documentation"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={createDescription}
                    onChange={(e) => setCreateDescription(e.target.value)}
                    placeholder="What this knowledge base contains..."
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    value={createCategory}
                    onChange={(e) => setCreateCategory(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="general">General</option>
                    <option value="product">Product</option>
                    <option value="faq">FAQ</option>
                    <option value="policy">Policy</option>
                    <option value="pricing">Pricing</option>
                    <option value="support">Support</option>
                  </select>
                </div>
                <button
                  onClick={() => createMutation.mutate()}
                  disabled={!createName.trim() || createMutation.isPending}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {createMutation.isPending ? 'Creating...' : 'Create Knowledge Base'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Ingest Document Modal */}
      {showIngestModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-black/50" onClick={() => setShowIngestModal(null)} />
            <div className="relative bg-white rounded-2xl shadow-xl max-w-lg w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Add Document</h3>
                <button onClick={() => setShowIngestModal(null)} className="text-gray-400 hover:text-gray-600">
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Source</label>
                  <input
                    type="text"
                    value={ingestSource}
                    onChange={(e) => setIngestSource(e.target.value)}
                    placeholder="e.g., product-guide.pdf, website FAQ"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Content</label>
                  <textarea
                    value={ingestContent}
                    onChange={(e) => setIngestContent(e.target.value)}
                    placeholder="Paste the document text content here..."
                    rows={10}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono"
                  />
                  <p className="text-xs text-gray-400 mt-1">{ingestContent.split(/\s+/).filter(Boolean).length} words</p>
                </div>
                <button
                  onClick={() => ingestMutation.mutate({ kbId: showIngestModal, content: ingestContent, source: ingestSource })}
                  disabled={!ingestContent.trim() || !ingestSource.trim() || ingestMutation.isPending}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {ingestMutation.isPending ? 'Processing...' : 'Ingest Document'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add FAQ Modal */}
      {showFAQModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-black/50" onClick={() => setShowFAQModal(null)} />
            <div className="relative bg-white rounded-2xl shadow-xl max-w-lg w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Add FAQ</h3>
                <button onClick={() => setShowFAQModal(null)} className="text-gray-400 hover:text-gray-600">
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Question</label>
                  <input
                    type="text"
                    value={faqQuestion}
                    onChange={(e) => setFaqQuestion(e.target.value)}
                    placeholder="What question will leads ask?"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Answer</label>
                  <textarea
                    value={faqAnswer}
                    onChange={(e) => setFaqAnswer(e.target.value)}
                    placeholder="The answer your AI agent should give..."
                    rows={5}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category (optional)</label>
                  <input
                    type="text"
                    value={faqCategory}
                    onChange={(e) => setFaqCategory(e.target.value)}
                    placeholder="e.g., pricing, support, product"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <button
                  onClick={() => faqMutation.mutate({ kbId: showFAQModal, question: faqQuestion, answer: faqAnswer, category: faqCategory || undefined })}
                  disabled={!faqQuestion.trim() || !faqAnswer.trim() || faqMutation.isPending}
                  className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 transition-colors"
                >
                  {faqMutation.isPending ? 'Adding...' : 'Add FAQ'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Search Modal */}
      {showSearchModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-black/50" onClick={() => { setShowSearchModal(false); setSearchResults([]); }} />
            <div className="relative bg-white rounded-2xl shadow-xl max-w-2xl w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  <SparklesIcon className="h-5 w-5 inline mr-1 text-blue-600" />
                  Test Semantic Search
                </h3>
                <button onClick={() => { setShowSearchModal(false); setSearchResults([]); }} className="text-gray-400 hover:text-gray-600">
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>
              <div className="space-y-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    placeholder="Ask a question to test AI retrieval..."
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <button
                    onClick={handleSearch}
                    disabled={searching || !searchQuery.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                  >
                    {searching ? 'Searching...' : 'Search'}
                  </button>
                </div>

                {searchResults.length > 0 && (
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {searchResults.map((result, i) => (
                      <div key={result.id} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-medium text-gray-500">
                            #{i + 1} · {result.knowledge_base} · {result.source}
                          </span>
                          <span className={clsx(
                            'text-xs font-medium px-2 py-0.5 rounded-full',
                            result.similarity > 0.9 ? 'bg-green-100 text-green-700' :
                            result.similarity > 0.8 ? 'bg-blue-100 text-blue-700' : 'bg-yellow-100 text-yellow-700'
                          )}>
                            {(result.similarity * 100).toFixed(1)}% match
                          </span>
                        </div>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">{result.content}</p>
                      </div>
                    ))}
                  </div>
                )}

                {searchResults.length === 0 && searchQuery && !searching && (
                  <p className="text-sm text-gray-500 text-center py-4">No results found. Try a different query or add more documents.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
