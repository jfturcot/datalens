import { useCallback, useState } from "react";

interface PasswordGateProps {
  onAuthenticated: () => void;
}

export function PasswordGate({ onAuthenticated }: PasswordGateProps) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!password.trim() || submitting) return;
      setSubmitting(true);
      setError(false);

      try {
        const { createSession } = await import("../lib/api");
        await createSession(password);
        onAuthenticated();
      } catch {
        setError(true);
        setSubmitting(false);
      }
    },
    [password, submitting, onAuthenticated],
  );

  return (
    <div className="flex h-screen items-center justify-center bg-white dark:bg-gray-900">
      <form onSubmit={handleSubmit} className="w-full max-w-xs space-y-4">
        <h1 className="text-center text-xl font-semibold text-gray-900 dark:text-gray-100">
          DataLens
        </h1>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          autoFocus
          className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500"
        />
        {error && (
          <p className="text-center text-sm text-red-500">
            Incorrect password
          </p>
        )}
        <button
          type="submit"
          disabled={submitting || !password.trim()}
          className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 dark:bg-blue-500 dark:hover:bg-blue-600"
        >
          {submitting ? "..." : "Enter"}
        </button>
      </form>
    </div>
  );
}
