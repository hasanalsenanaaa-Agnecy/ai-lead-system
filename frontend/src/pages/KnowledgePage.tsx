// Knowledge Base Management Page

import { useState } from 'react';
import { clsx } from 'clsx';
import {
  PlusIcon,
  DocumentTextIcon,
  QuestionMarkCircleIcon,
  TrashIcon,
  MagnifyingGlassIcon,
  ArrowUpTrayIcon,
  BookOpenIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { format, parseISO } from 'date-fns';
import { useClientStore } from '../store';
import type { KnowledgeBase } from '../types';

// Mock data
const mockKnowledgeBases: KnowledgeBase[] = [
  {
    id: '1',
    client_id: '1',
    name: 'Company FAQs',
    description: 'Frequently asked questions about our services',
    document_count: 25,
    is_active: true,
    created_at: new Date(Date.now() - 86400000 * 7).toISOString(),
  },
  {
    id: '2',
    client_id: '1',
    name: 'Property Listings',
    description: 'Current property listings and details',
    document_count: 48,
    is_active: true,
    created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
  },
  {
    id: '3',
    client_id: '1',
    name: 'Policies & Procedures',
    description: 'Company policies and standard procedures',
    document_count: 12,
    is_active: false,
    created_at: new Date(Date.now() - 86400000 * 14).toISOString(),
  },
];

interface CreateKBModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (name: string, description: string) => void;
}

function CreateKBModal({ isOpen, onClose, onCreate }: CreateKBModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onCreate(name.trim(), description.trim());
      setName('');
      setDescription('');
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Create Knowledge Base
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Company FAQs"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description (optional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What kind of content will this contain?"
                rows={3}
                className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div className="flex justify-end gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Create
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

interface AddContentModalProps {
  isOpen: boolean;
  kbName: string;
  onClose: () => void;
  onAddDocument: (content: string, source: string) => void;
  onAddFAQ: (question: string, answer: string) => void;
}

function AddContentModal({
  isOpen,
  kbName,
  onClose,
  onAddDocument,
  onAddFAQ,
}: AddContentModalProps) {
  const [mode, setMode] = useState<'document' | 'faq'>('faq');
  const [content, setContent] = useState('');
  const [source, setSource] = useState('');
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === 'document' && content.trim() && source.trim()) {
      onAddDocument(content.trim(), source.trim());
    } else if (mode === 'faq' && question.trim() && answer.trim()) {
      onAddFAQ(question.trim(), answer.trim());
    }
    setContent('');
    setSource('');
    setQuestion('');
    setAnswer('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
        <div className="p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Add Content to {kbName}
          </h2>

          {/* Mode Tabs */}
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => setMode('faq')}
              className={clsx(
                'flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors',
                mode === 'faq'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
            >
              <QuestionMarkCircleIcon className="h-5 w-5 inline mr-2" />
              FAQ
            </button>
            <button
              onClick={() => setMode('document')}
              className={clsx(
                'flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors',
                mode === 'document'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
            >
              <DocumentTextIcon className="h-5 w-5 inline mr-2" />
              Document
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'faq' ? (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Question
                  </label>
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="e.g., What are your business hours?"
                    className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Answer
                  </label>
                  <textarea
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder="e.g., We're open Monday-Friday, 9 AM to 6 PM"
                    rows={4}
                    className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    required
                  />
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Source Name
                  </label>
                  <input
                    type="text"
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                    placeholder="e.g., company-policies.pdf"
                    className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Content
                  </label>
                  <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="Paste the document content here..."
                    rows={8}
                    className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono text-sm"
                    required
                  />
                </div>
              </>
            )}

            <div className="flex justify-end gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Add {mode === 'faq' ? 'FAQ' : 'Document'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<
    { content: string; source: string; similarity: number }[]
  >([]);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setIsSearching(true);

    // Mock search results
    await new Promise((r) => setTimeout(r, 500));
    setResults([
      {
        content:
          'Our business hours are Monday through Friday, 9 AM to 6 PM. We are closed on weekends and public holidays.',
        source: 'Company FAQs',
        similarity: 0.94,
      },
      {
        content:
          'For urgent inquiries outside business hours, please email urgent@example.com and we will respond within 24 hours.',
        source: 'Company FAQs',
        similarity: 0.82,
      },
    ]);
    setIsSearching(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col">
        <div className="p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Test Knowledge Search
          </h2>
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Ask a question to test the knowledge base..."
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              onClick={handleSearch}
              disabled={isSearching}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {isSearching ? 'Searching...' : 'Search'}
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {results.length > 0 ? (
            <div className="space-y-4">
              {results.map((result, i) => (
                <div
                  key={i}
                  className="p-4 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-500">
                      {result.source}
                    </span>
                    <span
                      className={clsx(
                        'text-xs font-medium px-2 py-1 rounded',
                        result.similarity >= 0.9
                          ? 'bg-green-100 text-green-700'
                          : result.similarity >= 0.8
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-gray-100 text-gray-700'
                      )}
                    >
                      {Math.round(result.similarity * 100)}% match
                    </span>
                  </div>
                  <p className="text-gray-700">{result.content}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <MagnifyingGlassIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Enter a query to search the knowledge base</p>
            </div>
          )}
        </div>

        <div className="p-4 border-t">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default function KnowledgePage() {
  const { currentClient } = useClientStore();
  const [knowledgeBases, setKnowledgeBases] = useState(mockKnowledgeBases);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(null);
  const [showAddContentModal, setShowAddContentModal] = useState(false);

  const handleCreateKB = (name: string, description: string) => {
    const newKB: KnowledgeBase = {
      id: crypto.randomUUID(),
      client_id: currentClient?.id || '1',
      name,
      description,
      document_count: 0,
      is_active: true,
      created_at: new Date().toISOString(),
    };
    setKnowledgeBases([newKB, ...knowledgeBases]);
    toast.success('Knowledge base created');
  };

  const handleDeleteKB = (id: string) => {
    if (confirm('Are you sure you want to delete this knowledge base?')) {
      setKnowledgeBases(knowledgeBases.filter((kb) => kb.id !== id));
      toast.success('Knowledge base deleted');
    }
  };

  const handleAddDocument = (content: string, source: string) => {
    toast.success(`Document "${source}" added successfully`);
  };

  const handleAddFAQ = (question: string, answer: string) => {
    toast.success('FAQ added successfully');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Knowledge Base</h1>
          <p className="text-gray-500">
            Manage the AI's knowledge for answering customer questions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSearchModal(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <MagnifyingGlassIcon className="h-4 w-4" />
            Test Search
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <PlusIcon className="h-4 w-4" />
            New Knowledge Base
          </button>
        </div>
      </div>

      {/* Knowledge Bases Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {knowledgeBases.map((kb) => (
          <div
            key={kb.id}
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
                  <BookOpenIcon className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">{kb.name}</h3>
                  <span
                    className={clsx(
                      'text-xs font-medium',
                      kb.is_active ? 'text-green-600' : 'text-gray-500'
                    )}
                  >
                    {kb.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
              <button
                onClick={() => handleDeleteKB(kb.id)}
                className="text-gray-400 hover:text-red-600"
              >
                <TrashIcon className="h-5 w-5" />
              </button>
            </div>

            {kb.description && (
              <p className="text-sm text-gray-500 mb-4">{kb.description}</p>
            )}

            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">
                {kb.document_count} documents
              </span>
              <span className="text-gray-400">
                Created {format(parseISO(kb.created_at), 'MMM d, yyyy')}
              </span>
            </div>

            <div className="mt-4 pt-4 border-t flex gap-2">
              <button
                onClick={() => {
                  setSelectedKB(kb);
                  setShowAddContentModal(true);
                }}
                className="flex-1 inline-flex items-center justify-center gap-1 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg"
              >
                <ArrowUpTrayIcon className="h-4 w-4" />
                Add Content
              </button>
            </div>
          </div>
        ))}

        {knowledgeBases.length === 0 && (
          <div className="col-span-full text-center py-12 bg-white rounded-xl border border-dashed border-gray-300">
            <BookOpenIcon className="h-12 w-12 mx-auto text-gray-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No knowledge bases yet
            </h3>
            <p className="text-gray-500 mb-4">
              Create your first knowledge base to help the AI answer questions
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <PlusIcon className="h-4 w-4" />
              Create Knowledge Base
            </button>
          </div>
        )}
      </div>

      {/* Modals */}
      <CreateKBModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={handleCreateKB}
      />
      <AddContentModal
        isOpen={showAddContentModal}
        kbName={selectedKB?.name || ''}
        onClose={() => {
          setShowAddContentModal(false);
          setSelectedKB(null);
        }}
        onAddDocument={handleAddDocument}
        onAddFAQ={handleAddFAQ}
      />
      <SearchModal
        isOpen={showSearchModal}
        onClose={() => setShowSearchModal(false)}
      />
    </div>
  );
}
