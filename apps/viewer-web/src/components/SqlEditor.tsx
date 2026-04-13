import { useCallback, useEffect, useRef, useState } from "react";
import { EditorView, keymap, placeholder } from "@codemirror/view";
import { EditorState } from "@codemirror/state";
import { sql, SQLite } from "@codemirror/lang-sql";
import { defaultKeymap } from "@codemirror/commands";
import { searchKeymap } from "@codemirror/search";
import {
  autocompletion,
  acceptCompletion,
  startCompletion,
} from "@codemirror/autocomplete";
import { useQuery } from "@tanstack/react-query";
import { getSearchColumns, getSearchExamples } from "@/lib/api";

const darkTheme = EditorView.theme(
  {
    "&": {
      backgroundColor: "rgb(24 24 27)",
      color: "rgb(228 228 231)",
      fontSize: "13px",
      borderRadius: "0.5rem",
      border: "1px solid rgb(63 63 70)",
    },
    ".cm-content": { padding: "8px 12px", fontFamily: "monospace" },
    ".cm-gutters": { display: "none" },
    "&.cm-focused": { outline: "1px solid rgb(99 102 241)" },
    ".cm-selectionBackground": { backgroundColor: "rgba(99, 102, 241, 0.3) !important" },
    ".cm-cursor": { borderLeftColor: "rgb(228 228 231)" },
  },
  { dark: true },
);

interface SqlEditorProps {
  onSubmit: (sql: string) => void;
  error?: string | null;
}

export function SqlEditor({ onSubmit, error }: SqlEditorProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [showExamples, setShowExamples] = useState(false);

  const { data: examples } = useQuery({
    queryKey: ["search-examples"],
    queryFn: getSearchExamples,
    staleTime: Infinity,
  });

  const { data: columns } = useQuery({
    queryKey: ["search-columns"],
    queryFn: getSearchColumns,
    staleTime: Infinity,
  });

  const handleSubmit = useCallback(() => {
    const val = viewRef.current?.state.doc.toString().trim();
    if (val) onSubmit(val);
  }, [onSubmit]);

  useEffect(() => {
    if (!expanded || !editorRef.current) return;
    // Already mounted — don't recreate
    if (viewRef.current) return;

    const allCompletions = [
      { label: "v_trajectories", type: "keyword" as const, detail: "view", boost: 2 },
      { label: "SELECT", type: "keyword" as const },
      { label: "FROM", type: "keyword" as const },
      { label: "WHERE", type: "keyword" as const },
      { label: "ORDER BY", type: "keyword" as const },
      { label: "GROUP BY", type: "keyword" as const },
      { label: "HAVING", type: "keyword" as const },
      { label: "LIMIT", type: "keyword" as const },
      { label: "COUNT", type: "function" as const },
      { label: "SUM", type: "function" as const },
      { label: "AVG", type: "function" as const },
      { label: "DISTINCT", type: "keyword" as const },
      { label: "ASC", type: "keyword" as const },
      { label: "DESC", type: "keyword" as const },
      { label: "LIKE", type: "keyword" as const },
      { label: "AND", type: "keyword" as const },
      { label: "OR", type: "keyword" as const },
      { label: "IN", type: "keyword" as const },
      { label: "IS NULL", type: "keyword" as const },
      { label: "IS NOT NULL", type: "keyword" as const },
      ...(columns?.map((c) => ({
        label: c.name,
        type: "property" as const,
        detail: c.type,
        info: c.description,
        boost: 1,
      })) ?? []),
    ];

    const state = EditorState.create({
      doc: "",
      extensions: [
        keymap.of([
          {
            key: "Mod-Enter",
            run: () => {
              handleSubmit();
              return true;
            },
          },
          { key: "Tab", run: acceptCompletion },
          ...defaultKeymap,
          ...searchKeymap,
        ]),
        sql({ dialect: SQLite }),
        autocompletion({
          activateOnTyping: true,
          override: [
            (ctx) => {
              const word = ctx.matchBefore(/\w*/);
              return {
                from: word ? word.from : ctx.pos,
                options: allCompletions,
              };
            },
          ],
        }),
        EditorView.updateListener.of((update) => {
          if (update.focusChanged && update.view.hasFocus) {
            startCompletion(update.view);
          }
        }),
        darkTheme,
        placeholder("SELECT * FROM v_trajectories WHERE ..."),
        EditorView.lineWrapping,
      ],
    });

    viewRef.current = new EditorView({ state, parent: editorRef.current });

    return () => {
      viewRef.current?.destroy();
      viewRef.current = null;
    };
  }, [expanded, columns, handleSubmit]);

  const loadExample = (sqlStr: string) => {
    if (viewRef.current) {
      viewRef.current.dispatch({
        changes: {
          from: 0,
          to: viewRef.current.state.doc.length,
          insert: sqlStr,
        },
      });
    }
    setShowExamples(false);
    setExpanded(true);
  };

  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="w-full text-left px-4 py-2.5 rounded-lg border border-zinc-700 bg-zinc-900 text-zinc-400 hover:border-zinc-600 hover:text-zinc-300 transition-colors text-sm"
      >
        Search with SQL...
      </button>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs text-zinc-500 font-mono">
          SELECT ... FROM v_trajectories
        </span>
        <div className="flex-1" />
        <div className="relative">
          <button
            onClick={() => setShowExamples(!showExamples)}
            className="text-xs text-indigo-400 hover:text-indigo-300"
          >
            Examples
          </button>
          {showExamples && examples && (
            <div className="absolute right-0 top-6 z-50 w-80 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl p-2 space-y-1">
              {examples.map((ex) => (
                <button
                  key={ex.title}
                  onClick={() => loadExample(ex.sql)}
                  className="w-full text-left px-3 py-2 text-xs rounded hover:bg-zinc-700 text-zinc-300"
                >
                  {ex.title}
                </button>
              ))}
            </div>
          )}
        </div>
        <button
          onClick={handleSubmit}
          className="px-3 py-1 text-xs bg-indigo-600 hover:bg-indigo-500 rounded font-medium"
        >
          Run (Cmd+Enter)
        </button>
        <button
          onClick={() => setExpanded(false)}
          className="px-2 py-1 text-xs text-zinc-500 hover:text-zinc-300"
        >
          Close
        </button>
      </div>
      <div ref={editorRef} className="min-h-[60px]" />
      {error && (
        <div className="text-xs text-red-400 bg-red-950/50 rounded px-3 py-2 font-mono">
          {error}
        </div>
      )}
    </div>
  );
}
