import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { addTag, removeTag } from "@/lib/api";

interface TagChipsProps {
  trajectoryId: string;
  tags: string[];
}

export function TagChips({ trajectoryId, tags }: TagChipsProps) {
  const [input, setInput] = useState("");
  const [adding, setAdding] = useState(false);
  const qc = useQueryClient();

  const addMut = useMutation({
    mutationFn: (tag: string) => addTag(trajectoryId, tag),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["trajectory", trajectoryId] });
      setInput("");
      setAdding(false);
    },
  });

  const removeMut = useMutation({
    mutationFn: (tag: string) => removeTag(trajectoryId, tag),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["trajectory", trajectoryId] }),
  });

  return (
    <div className="flex flex-wrap gap-1.5 items-center">
      {tags.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-zinc-800 text-xs text-zinc-300 border border-zinc-700"
        >
          {tag}
          <button
            onClick={() => removeMut.mutate(tag)}
            className="text-zinc-500 hover:text-red-400 ml-0.5"
          >
            &times;
          </button>
        </span>
      ))}
      {adding ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (input.trim()) addMut.mutate(input.trim());
          }}
          className="inline-flex"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            autoFocus
            placeholder="tag name"
            className="w-24 px-2 py-0.5 text-xs bg-zinc-800 border border-zinc-600 rounded focus:outline-none focus:border-indigo-500 text-zinc-200"
            onBlur={() => {
              if (!input.trim()) setAdding(false);
            }}
          />
        </form>
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="text-xs text-indigo-400 hover:text-indigo-300"
        >
          + tag
        </button>
      )}
    </div>
  );
}
