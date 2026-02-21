import { useMemo } from "react";

const ALL_SUGGESTIONS = [
  "What's the average ARR for fintech companies?",
  "Which company has the highest growth rate?",
  "Show me companies founded after 2020 with less than 5% churn.",
  "How many companies have more than 100 employees?",
];

interface SuggestionChipsProps {
  onSelect: (text: string) => void;
}

function pickRandom<T>(arr: T[], count: number): T[] {
  const shuffled = [...arr].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, count);
}

export function SuggestionChips({ onSelect }: SuggestionChipsProps) {
  const suggestions = useMemo(() => pickRandom(ALL_SUGGESTIONS, 3), []);

  return (
    <div className="flex flex-wrap justify-center gap-2 px-4 pb-2">
      {suggestions.map((text) => (
        <button
          key={text}
          onClick={() => onSelect(text)}
          className="rounded-full border border-gray-300 bg-white px-3 py-1.5 text-xs text-gray-700 transition-colors hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-blue-500 dark:hover:bg-blue-900/30 dark:hover:text-blue-300"
        >
          {text}
        </button>
      ))}
    </div>
  );
}
